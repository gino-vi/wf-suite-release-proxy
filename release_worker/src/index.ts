export interface Env {
  GITHUB_TOKEN: string
  REPO_OWNER?: string
  REPO_NAME?: string
}

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8' }

function json(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), { ...init, headers: { ...JSON_HEADERS, ...(init.headers || {}) } })
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url)
    const owner = env.REPO_OWNER || 'gino-vi'
    const repo = env.REPO_NAME || 'Wangfang-Suite'
    const ghHeaders: Record<string, string> = {
      'Authorization': `token ${env.GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'WF-Suite-Release-Proxy/worker'
    }

    if (url.pathname === '/') {
      return json({
        service: 'WF Suite Release Proxy (CF Worker)',
        repository: `${owner}/${repo}`,
        endpoints: {
          '/releases': 'Get available releases',
          '/releases/download/<tag>/<asset>': 'Download release asset',
          '/health': 'Health check'
        }
      })
    }

    if (url.pathname === '/health') {
      try {
        const gh = await fetch(`https://api.github.com/repos/${owner}/${repo}`, { headers: ghHeaders })
        return json({
          status: 'healthy',
          github_api: gh.ok ? 'connected' : `error:${gh.status}`,
          cache: 'edge'
        })
      } catch (e: any) {
        return json({ status: 'unhealthy', error: String(e) }, { status: 500 })
      }
    }

    if (url.pathname === '/releases') {
      const cache = caches.default
      const cacheKey = new Request(new URL(url.toString()), request)
      const cached = await cache.match(cacheKey)
      if (cached) return cached

      try {
        const gh = await fetch(`https://api.github.com/repos/${owner}/${repo}/releases`, { headers: ghHeaders })
        if (!gh.ok) return json({ error: 'Failed to fetch releases from GitHub' }, { status: 502 })

        const releases = await gh.json() as any[]
        const publicReleases = releases
          .filter(r => !r.draft)
          .map(r => {
            const assets = (r.assets || [])
              .filter((a: any) => a.name?.endsWith('.exe'))
              .map((a: any) => ({
                name: a.name,
                browser_download_url: a.browser_download_url,
                size: a.size ?? 0,
                created_at: a.created_at
              }))
            return assets.length ? {
              tag_name: r.tag_name,
              name: r.name || r.tag_name,
              prerelease: !!r.prerelease,
              body: r.body || '',
              html_url: r.html_url,
              published_at: r.published_at,
              assets
            } : null
          })
          .filter(Boolean)

        const resp = new Response(JSON.stringify(publicReleases), {
          headers: { ...JSON_HEADERS, 'Cache-Control': 'max-age=120' }
        })
        ctx.waitUntil(cache.put(cacheKey, resp.clone()))
        return resp
      } catch {
        return json({ error: 'Internal error' }, { status: 500 })
      }
    }

    const m = url.pathname.match(/^\/releases\/download\/([^\/]+)\/(.+)$/)
    if (m) {
      const tag = decodeURIComponent(m[1])
      const asset = decodeURIComponent(m[2])
      if (!asset.endsWith('.exe')) return json({ error: 'Only .exe files are allowed' }, { status: 400 })

      const rel = await fetch(`https://api.github.com/repos/${owner}/${repo}/releases/tags/${encodeURIComponent(tag)}`, {
        headers: ghHeaders
      })
      if (!rel.ok) return json({ error: 'Release not found' }, { status: 404 })
      const relJson = await rel.json() as any
      const found = (relJson.assets || []).find((a: any) => a.name === asset)
      if (!found) return json({ error: 'Asset not found' }, { status: 404 })

      const assetUrl = `https://api.github.com/repos/${owner}/${repo}/releases/assets/${found.id}`
      const dl = await fetch(assetUrl, {
        headers: { ...ghHeaders, 'Accept': 'application/octet-stream' }
      })
      if (!dl.ok || !dl.body) return json({ error: 'Failed to download from GitHub' }, { status: 502 })

      const headers = new Headers(dl.headers)
      headers.set('Content-Disposition', `attachment; filename="${asset}"`)
      headers.set('Content-Type', 'application/octet-stream')
      return new Response(dl.body, { headers })
    }

    return json({ error: 'Not found' }, { status: 404 })
  }
}
