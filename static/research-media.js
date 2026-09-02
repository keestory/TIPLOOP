export function createMediaController(config) {
  const input = document.getElementById('media-input')
  const pick = document.getElementById('media-pick')
  const zone = document.getElementById('upload-zone')
  const list = document.getElementById('media-list')
  const status = document.getElementById('media-status')
  const hidden = document.getElementById('attachments-hidden')
  let existing = config.attachments
  let removed = []
  let pending = []
  let uploading = false

  function formatBytes(bytes) {
    if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)}MB`
    return `${Math.max(1, Math.round(bytes / 1024))}KB`
  }

  function updatePayload() {
    hidden.value = JSON.stringify(existing)
  }

  function fileCopy(fileName, kind, size, state) {
    const copy = document.createElement('span')
    copy.className = 'media-item-copy'
    const name = document.createElement('strong')
    name.textContent = fileName
    const meta = document.createElement('small')
    meta.textContent = `${kind === 'image' ? '이미지' : '영상'} · ${formatBytes(size)} · ${state}`
    copy.append(name, meta)
    return copy
  }

  function removeButton(label, action) {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'media-remove'
    button.textContent = label
    button.disabled = uploading
    button.addEventListener('click', action)
    return button
  }

  function render() {
    list.replaceChildren()
    existing.forEach((attachment, index) => {
      const item = document.createElement('li')
      item.className = 'media-item'
      const remove = removeButton('노트에서 제외', () => {
        removed.push(attachment)
        existing.splice(index, 1)
        updatePayload()
        render()
        config.changed()
      })
      remove.setAttribute('aria-label', `${attachment.file_name} 노트에서 제외`)
      item.append(fileCopy(
        attachment.file_name, attachment.kind, attachment.size_bytes, '저장됨'
      ), remove)
      list.append(item)
    })
    pending.forEach((entry, index) => {
      const item = document.createElement('li')
      item.className = 'media-item'
      const preview = entry.kind === 'image'
        ? document.createElement('img')
        : document.createElement('video')
      preview.className = 'media-thumb'
      preview.src = entry.previewUrl
      preview.setAttribute('aria-hidden', 'true')
      if (entry.kind === 'video') preview.muted = true
      const remove = removeButton('제거', () => {
        URL.revokeObjectURL(entry.previewUrl)
        pending.splice(index, 1)
        render()
        config.changed()
      })
      remove.setAttribute('aria-label', `${entry.file.name} 제거`)
      item.append(
        preview,
        fileCopy(entry.file.name, entry.kind, entry.file.size, entry.state),
        remove
      )
      list.append(item)
    })
    const count = existing.length + pending.length
    status.textContent = count ? `${count}/${config.maxFiles}개 첨부` : ''
  }

  function addFiles(fileList) {
    config.clearErrors()
    const files = Array.from(fileList || [])
    const available = config.maxFiles - existing.length - pending.length
    if (files.length > available) {
      status.textContent = `최대 ${config.maxFiles}개까지 첨부할 수 있어요. 기존 선택은 그대로 두었습니다.`
      return
    }
    let videos = existing.filter((item) => item.kind === 'video').length +
      pending.filter((item) => item.kind === 'video').length
    let total = existing.reduce((sum, item) => sum + item.size_bytes, 0) +
      pending.reduce((sum, item) => sum + item.file.size, 0)
    files.forEach((file) => {
      const type = config.typeConfig[file.type]
      if (!type) {
        status.textContent = `${file.name}: 지원하지 않는 파일 형식이에요.`
        return
      }
      const [kind, extension] = type
      const limit = kind === 'image' ? config.imageMaxBytes : config.videoMaxBytes
      if (!file.size || file.size > limit) {
        status.textContent = `${file.name}: ${kind === 'image' ? '이미지 10MB' : '영상 50MB'} 이하만 가능해요.`
        return
      }
      if (kind === 'video' && videos >= config.maxVideos) {
        status.textContent = `${file.name}: 영상은 노트당 1개까지 첨부할 수 있어요.`
        return
      }
      if (total + file.size > config.maxTotalBytes) {
        status.textContent = `${file.name}: 첨부 파일 전체 크기는 100MB까지 가능해요.`
        return
      }
      pending.push({
        file, kind, extension, state: '업로드 대기',
        previewUrl: URL.createObjectURL(file)
      })
      total += file.size
      if (kind === 'video') videos += 1
    })
    input.value = ''
    config.changed()
    render()
  }

  async function uploadPendingFiles() {
    if (!pending.length) return true
    if (!config.supabase) {
      config.setError('첨부 저장 설정을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.', pick)
      return false
    }
    const { data: { session } } = await config.supabase.auth.getSession()
    if (!session || session.user.id !== config.currentAuthId) {
      config.setError('로그인 계정이 달라 첨부를 저장할 수 없습니다. 다시 로그인해 주세요.', pick)
      return false
    }
    const draftId = crypto.randomUUID()
    let failed = 0
    for (const entry of [...pending]) {
      entry.state = '업로드 중…'
      render()
      const path = `${config.currentAuthId}/drafts/${draftId}/${crypto.randomUUID()}.${entry.extension}`
      const bucket = config.buckets[entry.kind]
      const { error } = await config.supabase.storage.from(bucket).upload(path, entry.file, {
        contentType: entry.file.type, cacheControl: '3600', upsert: false
      })
      if (error) {
        entry.state = '업로드 실패 · 다시 저장해 주세요'
        failed += 1
        continue
      }
      existing.push({
        bucket, path, kind: entry.kind, mime_type: entry.file.type,
        file_name: entry.file.name, size_bytes: entry.file.size
      })
      URL.revokeObjectURL(entry.previewUrl)
      pending = pending.filter((candidate) => candidate !== entry)
      updatePayload()
    }
    render()
    if (failed) {
      config.setError(`${failed}개 파일을 올리지 못했어요. 텍스트와 성공한 파일은 그대로 유지됩니다.`, pick)
      return false
    }
    return true
  }

  pick.addEventListener('click', () => input.click())
  input.addEventListener('change', () => addFiles(input.files))
  zone.addEventListener('dragover', (event) => {
    event.preventDefault()
    zone.classList.add('is-dragover')
  })
  zone.addEventListener('dragleave', () => zone.classList.remove('is-dragover'))
  zone.addEventListener('drop', (event) => {
    event.preventDefault()
    zone.classList.remove('is-dragover')
    addFiles(event.dataTransfer.files)
  })
  updatePayload()
  render()

  return {
    pendingNames: () => pending.map((entry) => entry.file.name),
    hasPending: () => pending.length > 0,
    uploadPendingFiles,
    setUploading(value) { uploading = value; render() },
    queueCleanup(key) {
      try {
        if (removed.length) sessionStorage.setItem(key, JSON.stringify(removed))
        else sessionStorage.removeItem(key)
      } catch (error) {}
    },
    updatePayload
  }
}
