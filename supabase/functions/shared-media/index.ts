const TOKEN_RE = /^[A-Za-z0-9_-]{43}$/
const ALLOWED_MEDIA: Record<string, { kind: string; types: Record<string, string[]> }> = {
  'tiploop-research-images': {
    kind: 'image',
    types: {
      'image/jpeg': ['jpg', 'jpeg'],
      'image/png': ['png'],
      'image/webp': ['webp'],
      'image/gif': ['gif'],
    },
  },
  'tiploop-research-videos': {
    kind: 'video',
    types: {
      'video/mp4': ['mp4'],
      'video/webm': ['webm'],
      'video/quicktime': ['mov'],
    },
  },
}

function plain(status: number, message: string): Response {
  return new Response(message, {
    status,
    headers: {
      'Cache-Control': 'private, no-store, max-age=0',
      'Content-Type': 'text/plain; charset=utf-8',
      'Referrer-Policy': 'no-referrer',
      'X-Content-Type-Options': 'nosniff',
    },
  })
}

function secretKey(): string {
  const modern = Deno.env.get('SUPABASE_SECRET_KEYS')
  if (modern) {
    try {
      const keys = JSON.parse(modern)
      if (typeof keys.default === 'string' && keys.default) return keys.default
    } catch (_error) {
      // 잘못된 secret JSON은 아래 legacy fallback 또는 명시적 500으로 처리한다.
    }
  }
  return Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || ''
}

function adminHeaders(key: string): HeadersInit {
  const headers: Record<string, string> = {
    apikey: key,
    Accept: 'application/json',
  }
  if (!key.startsWith('sb_secret_')) headers.Authorization = `Bearer ${key}`
  return headers
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(value),
  )
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

async function rows(
  baseUrl: string,
  key: string,
  path: string,
): Promise<Record<string, unknown>[] | null> {
  const response = await fetch(`${baseUrl}/rest/v1/${path}`, {
    headers: adminHeaders(key),
  })
  if (!response.ok) return null
  const payload = await response.json()
  return Array.isArray(payload) ? payload : null
}

function validAttachment(value: unknown, ownerAuthId: string): value is {
  bucket: string
  path: string
  kind: string
  mime_type: string
} {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  if (
    typeof item.bucket !== 'string' ||
    typeof item.path !== 'string' ||
    typeof item.kind !== 'string' ||
    typeof item.mime_type !== 'string'
  ) return false
  const rule = ALLOWED_MEDIA[item.bucket]
  const parts = item.path.split('/')
  const filename = parts[3] || ''
  const extension = filename.includes('.') ? filename.split('.').pop()?.toLowerCase() || '' : ''
  return Boolean(
    rule &&
    item.kind === rule.kind &&
    Array.isArray(rule.types[item.mime_type]) &&
    rule.types[item.mime_type].includes(extension) &&
    parts.length === 4 &&
    parts[0] === ownerAuthId &&
    parts[1] === 'drafts' &&
    /^[A-Za-z0-9_-]{1,128}$/.test(parts[0]) &&
    /^[A-Za-z0-9_-]{1,128}$/.test(parts[2]) &&
    /^[A-Za-z0-9_-]{1,160}\.[A-Za-z0-9]{2,5}$/.test(filename) &&
    !item.path.includes('..') &&
    !item.path.includes('\\') &&
    !item.path.includes('%'),
  )
}

Deno.serve(async (request: Request) => {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return plain(405, 'Method not allowed')
  }

  const url = new URL(request.url)
  const grant = url.searchParams.get('grant') || ''
  if (!TOKEN_RE.test(grant)) {
    return plain(404, 'Not found')
  }
  const range = request.headers.get('range')
  if (range && (!/^bytes=(?:\d+-\d*|\d*-\d+)$/.test(range) || range.includes(','))) {
    return plain(416, 'Range not satisfiable')
  }

  const baseUrl = Deno.env.get('SUPABASE_URL') || ''
  const key = secretKey()
  if (!baseUrl || !key) return plain(500, 'Media service unavailable')

  const tokenHash = await sha256(grant)
  const grants = await rows(
    baseUrl,
    key,
    `post_share_media_grants?select=share_id,attachment_index&token_hash=eq.${tokenHash}&limit=1`,
  )
  const mediaGrant = grants?.[0]
  const shareId = Number(mediaGrant?.share_id)
  const index = Number(mediaGrant?.attachment_index)
  if (
    !Number.isSafeInteger(shareId) || shareId <= 0 ||
    !Number.isInteger(index) || index < 0 || index > 5
  ) return plain(404, 'Not found')

  const shares = await rows(
    baseUrl,
    key,
    `post_shares?select=include_media,snapshot,expires_at,revoked_at&id=eq.${shareId}&limit=1`,
  )
  const share = shares?.[0]
  const expiresMs = typeof share?.expires_at === 'string'
    ? Date.parse(share.expires_at)
    : Number.NaN
  if (
    !share ||
    share.include_media !== true ||
    share.revoked_at !== null ||
    !Number.isFinite(expiresMs) ||
    expiresMs <= Date.now()
  ) return plain(404, 'Not found')

  const snapshot = share.snapshot && typeof share.snapshot === 'object'
    ? share.snapshot as Record<string, unknown>
    : null
  const ownerAuthId = typeof snapshot?.owner_auth_id === 'string'
    ? snapshot.owner_auth_id
    : ''
  const attachments = Array.isArray(snapshot?.attachments) ? snapshot.attachments : []
  const attachment = attachments[index]
  if (!ownerAuthId || !validAttachment(attachment, ownerAuthId)) {
    return plain(404, 'Not found')
  }

  const objectPath = attachment.path.split('/').map(encodeURIComponent).join('/')
  const objectUrl = `${baseUrl}/storage/v1/object/authenticated/${encodeURIComponent(attachment.bucket)}/${objectPath}`
  const originHeaders = new Headers(adminHeaders(key))
  if (range) originHeaders.set('Range', range)
  const origin = await fetch(objectUrl, {
    method: request.method,
    headers: originHeaders,
  })
  if (!origin.ok && origin.status !== 206 && origin.status !== 416) {
    return plain(404, 'Not found')
  }

  const headers = new Headers({
    'Cache-Control': 'private, no-store, max-age=0',
    'Content-Type': attachment.mime_type,
    'Content-Disposition': 'inline',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
    'Vary': 'Range',
  })
  for (const name of ['accept-ranges', 'content-length', 'content-range', 'etag', 'last-modified']) {
    const value = origin.headers.get(name)
    if (value) headers.set(name, value)
  }
  return new Response(request.method === 'HEAD' ? null : origin.body, {
    status: origin.status,
    headers,
  })
})
