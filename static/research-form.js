import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { createMediaController } from '/static/research-media.js'

const config = JSON.parse(document.getElementById('research-form-config').textContent)
const form = document.getElementById('post-form')
const title = document.getElementById('service-title')
const link = document.getElementById('service-link')
const hiddenBody = document.getElementById('body-hidden')
const status = document.getElementById('form-status')
const draftStatus = document.getElementById('draft-status')
const legacy = document.getElementById('legacy-body')
const submit = document.getElementById('submit-btn')
const picker = document.getElementById('question-picker')
const pickerTrigger = document.getElementById('question-picker-trigger')
const pickerClose = document.getElementById('question-picker-close')
const pickerDone = document.getElementById('question-picker-done')
const selectedCounts = form.querySelectorAll('[data-selected-count]')
const supabase = config.supabaseUrl
  ? createClient(config.supabaseUrl, config.supabaseKey)
  : null
let draftTimer = null
let dirty = false
let uploading = false

function setError(message, field) {
  status.textContent = message
  status.hidden = false
  if (field) {
    field.setAttribute('aria-invalid', 'true')
    field.focus()
  }
}

function clearErrors() {
  status.hidden = true
  status.textContent = ''
  form.querySelectorAll('[aria-invalid="true"]').forEach((field) => {
    field.removeAttribute('aria-invalid')
  })
}

function selectedIds() {
  return Array.from(form.querySelectorAll('[data-question-id][type="checkbox"]'))
    .filter((input) => input.checked)
    .map((input) => input.value)
}

function syncSelectedCount(ids = selectedIds()) {
  selectedCounts.forEach((count) => { count.textContent = `${ids.length}개 선택` })
}

function syncQuestions(announce = true) {
  const ids = selectedIds()
  const order = new Map(ids.map((id, index) => [id, index + 1]))
  form.querySelectorAll('.question-answer').forEach((card) => {
    const isSelected = order.has(card.dataset.questionId)
    card.hidden = !isSelected
    const position = card.querySelector('.answer-position')
    position.textContent = isSelected ? `${order.get(card.dataset.questionId)}/${ids.length}` : ''
  })
  syncSelectedCount(ids)
  if (announce) dirty = true
}

function openQuestionPicker() {
  if (!picker.open) {
    if (typeof picker.showModal === 'function') picker.showModal()
    else picker.setAttribute('open', '')
  }
  pickerTrigger.setAttribute('aria-expanded', 'true')
}

function closeQuestionPicker() {
  if (picker.open) {
    // 체크할 때마다 본문 높이를 바꾸지 않고 시트를 닫을 때 한 번만 반영한다.
    syncQuestions(false)
    if (typeof picker.close === 'function') picker.close()
    else picker.removeAttribute('open')
  }
  pickerTrigger.setAttribute('aria-expanded', 'false')
}

function setSelected(ids, announce = true) {
  const wanted = new Set(ids.concat(config.requiredQuestionId))
  form.querySelectorAll('[data-question-id][type="checkbox"]').forEach((input) => {
    input.checked = wanted.has(input.value)
  })
  syncQuestions(announce)
}

function currentMode() {
  return form.querySelector('[name="analysis_mode"]:checked')?.value || 'focus'
}

function setMode(mode) {
  if (mode === 'quick') {
    closeQuestionPicker()
    setSelected(config.quickQuestionIds)
  }
  if (mode === 'full') {
    closeQuestionPicker()
    setSelected(config.questionIds)
  }
  if (mode === 'focus') {
    setSelected(selectedIds())
    openQuestionPicker()
  }
  scheduleDraft()
}

function buildBody() {
  const parts = []
  if (legacy && legacy.value.trim()) parts.push(legacy.value.trim())
  form.querySelectorAll('.tpl-field').forEach((field) => {
    const value = field.value.trim()
    if (value) parts.push(`${field.dataset.label}\n${value}`)
  })
  hiddenBody.value = parts.join('\n\n')
  return parts.length
}

function autoGrow(field) {
  if (!field || field.tagName !== 'TEXTAREA') return
  field.style.height = 'auto'
  field.style.height = `${Math.max(104, field.scrollHeight)}px`
}

const KEYBOARD_INPUT_TYPES = new Set([
  'email', 'number', 'password', 'search', 'tel', 'text', 'url'
])

function isKeyboardInput(element) {
  if (element instanceof HTMLTextAreaElement) return true
  if (element instanceof HTMLInputElement) return KEYBOARD_INPUT_TYPES.has(element.type)
  return element instanceof HTMLElement && element.isContentEditable
}

function dismissKeyboard() {
  const active = document.activeElement
  if (isKeyboardInput(active)) active.blur()
}

// iPhone Safari에서는 키보드가 열린 동안 하단 탭바가 화면 위로 밀려난다.
// 입력 영역 밖을 누르거나 손가락을 아래로 쓸면 기본 탭/스크롤을 막지 않고 키보드만 닫는다.
document.addEventListener('pointerdown', (event) => {
  if (!isKeyboardInput(event.target)) dismissKeyboard()
}, { passive: true })

let touchStart = null
document.addEventListener('touchstart', (event) => {
  const touch = event.touches.length === 1 ? event.touches[0] : null
  touchStart = touch ? { x: touch.clientX, y: touch.clientY } : null
}, { passive: true })
document.addEventListener('touchend', (event) => {
  const touch = touchStart && event.changedTouches[0]
  if (touch) {
    const deltaX = touch.clientX - touchStart.x
    const deltaY = touch.clientY - touchStart.y
    if (deltaY >= 48 && deltaY > Math.abs(deltaX)) dismissKeyboard()
  }
  touchStart = null
}, { passive: true })
document.addEventListener('touchcancel', () => {
  touchStart = null
}, { passive: true })

function collectDraft() {
  const valuesById = {}
  const values = {}
  form.querySelectorAll('.tpl-field').forEach((field) => {
    valuesById[field.dataset.questionId] = field.value
    values[field.dataset.label] = field.value
  })
  return {
    schemaVersion: 2,
    title: title.value,
    link: link.value,
    legacy: legacy ? legacy.value : '',
    mode: currentMode(),
    selectedIds: selectedIds(),
    valuesById,
    values,
    pendingFileNames: media.pendingNames(),
    updatedAt: new Date().toISOString()
  }
}

function saveDraft() {
  try {
    localStorage.setItem(config.draftKey, JSON.stringify(collectDraft()))
    const now = new Date()
    draftStatus.textContent = `이 기기에 임시 저장됨 ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  } catch (error) {
    draftStatus.textContent = '이 브라우저에서는 임시 저장을 사용할 수 없어요.'
  }
}

function scheduleDraft() {
  window.clearTimeout(draftTimer)
  draftTimer = window.setTimeout(saveDraft, 400)
}

const media = createMediaController({
  supabase,
  attachments: config.attachments,
  currentAuthId: config.currentAuthId,
  buckets: config.mediaBuckets,
  typeConfig: config.mediaTypes,
  maxFiles: config.maxFiles,
  maxVideos: config.maxVideos,
  maxTotalBytes: config.maxTotalBytes,
  imageMaxBytes: config.imageMaxBytes,
  videoMaxBytes: config.videoMaxBytes,
  setError,
  clearErrors,
  changed() {
    dirty = true
    scheduleDraft()
  }
})

function restoreDraft() {
  try {
    const raw = localStorage.getItem(config.draftKey)
    if (!raw) return
    const draft = JSON.parse(raw)
    const hasContent = draft.title || draft.link || draft.legacy ||
      Object.values(draft.valuesById || draft.values || {}).some(Boolean)
    if (!hasContent) return
    title.value = draft.title || ''
    link.value = draft.link || ''
    if (legacy && typeof draft.legacy === 'string') legacy.value = draft.legacy
    form.querySelectorAll('.tpl-field').forEach((field) => {
      if (Object.prototype.hasOwnProperty.call(draft.valuesById || {}, field.dataset.questionId)) {
        field.value = draft.valuesById[field.dataset.questionId]
      } else if (Object.prototype.hasOwnProperty.call(draft.values || {}, field.dataset.label)) {
        field.value = draft.values[field.dataset.label]
      } else if (
        field.dataset.questionId === 'ref.next_action' &&
        Object.prototype.hasOwnProperty.call(draft.values || {}, '실제로 적용할 것')
      ) {
        field.value = draft.values['실제로 적용할 것']
      }
    })
    if (Array.isArray(draft.selectedIds) && draft.selectedIds.length) {
      const safe = draft.selectedIds.filter((id) => config.questionIds.includes(id))
      const mode = ['quick', 'focus', 'full'].includes(draft.mode) ? draft.mode : 'focus'
      form.querySelector(`[name="analysis_mode"][value="${mode}"]`).checked = true
      setSelected(safe, false)
    }
    draftStatus.textContent = draft.pendingFileNames?.length
      ? '초안을 복원했어요. 첨부 파일은 다시 선택해 주세요.'
      : '이 기기에 저장한 초안을 복원했어요.'
    dirty = true
  } catch (error) {
    // 손상되거나 접근할 수 없는 초안은 서버 폼 값을 그대로 사용한다.
  }
}

function validateForm() {
  clearErrors()
  if (!title.value.trim()) {
    setError('서비스명을 입력해 주세요.', title)
    return false
  }
  if (link.value.trim()) {
    try {
      const parsed = new URL(link.value.trim())
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') throw new Error()
    } catch (error) {
      setError('http:// 또는 https://로 시작하는 링크를 입력해 주세요.', link)
      return false
    }
  }
  if (!selectedIds().length) {
    openQuestionPicker()
    setError('답하고 싶은 질문을 한 개 이상 선택해 주세요.', picker.querySelector('input[type="checkbox"]'))
    return false
  }
  if (!buildBody()) {
    setError('선택한 질문 중 한 칸 이상 답해 주세요.', form.querySelector('.question-answer:not([hidden]) .tpl-field'))
    return false
  }
  return true
}

restoreDraft()
syncQuestions(false)
form.querySelectorAll('textarea').forEach(autoGrow)
form.querySelectorAll('[name="analysis_mode"]').forEach((radio) => {
  radio.addEventListener('change', () => setMode(radio.value))
})
pickerTrigger.addEventListener('click', openQuestionPicker)
pickerClose.addEventListener('click', closeQuestionPicker)
pickerDone.addEventListener('click', closeQuestionPicker)
picker.addEventListener('close', () => {
  syncQuestions(false)
  pickerTrigger.setAttribute('aria-expanded', 'false')
})
picker.addEventListener('click', (event) => {
  if (event.target === picker) closeQuestionPicker()
})
form.querySelectorAll('[data-question-id][type="checkbox"]').forEach((input) => {
  input.addEventListener('change', () => {
    form.querySelector('[name="analysis_mode"][value="focus"]').checked = true
    syncSelectedCount()
    dirty = true
    scheduleDraft()
  })
})
form.addEventListener('input', (event) => {
  dirty = true
  clearErrors()
  autoGrow(event.target)
  scheduleDraft()
})
form.addEventListener('submit', async (event) => {
  event.preventDefault()
  if (uploading || !validateForm()) return
  window.clearTimeout(draftTimer)
  saveDraft()
  uploading = true
  submit.disabled = true
  submit.setAttribute('aria-busy', 'true')
  submit.querySelector('span').textContent = media.hasPending() ? '첨부 올리는 중…' : '저장 중…'
  media.setUploading(true)
  let uploaded = false
  try {
    uploaded = await media.uploadPendingFiles()
  } catch (error) {
    setError('네트워크 문제로 첨부를 올리지 못했어요. 다시 시도해 주세요.', document.getElementById('media-pick'))
  }
  if (!uploaded) {
    uploading = false
    submit.disabled = false
    submit.removeAttribute('aria-busy')
    submit.querySelector('span').textContent = config.submitLabel
    media.setUploading(false)
    return
  }
  buildBody()
  media.updatePayload()
  media.queueCleanup(config.cleanupKey)
  dirty = false
  HTMLFormElement.prototype.submit.call(form)
})
window.addEventListener('beforeunload', (event) => {
  if (!dirty) return
  event.preventDefault()
  event.returnValue = ''
})
