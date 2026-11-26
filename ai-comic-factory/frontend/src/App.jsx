import React, { useEffect, useState } from 'react'
import {
  BookOpen,
  Image as ImageIcon,
  LayoutDashboard,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Send,
  Settings as SettingsIcon,
  Sparkles,
  Download,
} from 'lucide-react'

const API = '/api'

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(txt || `HTTP ${res.status}`)
  }
  return res.json()
}

export default function App() {
  const [tab, setTab] = useState('overview')
  const [overview, setOverview] = useState(null)
  const [health, setHealth] = useState(null)
  const [seriesList, setSeriesList] = useState([])
  const [selectedSeries, setSelectedSeries] = useState(null)
  const [selectedEpisodeScript, setSelectedEpisodeScript] = useState(null)
  const [gallery, setGallery] = useState([])
  const [galleryFilter, setGalleryFilter] = useState({ series_id: '', genre: '', image_role: '' })
  const [queue, setQueue] = useState([])
  const [logs, setLogs] = useState([])
  const [settings, setSettings] = useState(null)
  const [genres, setGenres] = useState([])
  const [artStyles, setArtStyles] = useState([])
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')

  const notify = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 4500)
  }

  const loadAll = async () => {
    try {
      const [ov, hl, sr, q, lg, st, gn, sty] = await Promise.all([
        fetchJson(`${API}/dashboard/overview`),
        fetchJson(`${API}/health`),
        fetchJson(`${API}/series`),
        fetchJson(`${API}/publishing/queue`),
        fetchJson(`${API}/publishing/logs`),
        fetchJson(`${API}/settings`),
        fetchJson(`${API}/genres`),
        fetchJson(`${API}/art-styles`),
      ])
      setOverview(ov)
      setHealth(hl)
      setSeriesList(sr)
      setQueue(q)
      setLogs(lg)
      setSettings(st)
      setGenres(gn)
      setArtStyles(sty)
    } catch (err) {
      notify(`Load error: ${err.message}`)
    }
  }

  const loadGallery = async (filters = galleryFilter) => {
    const params = new URLSearchParams()
    if (filters.series_id) params.set('series_id', filters.series_id)
    if (filters.genre) params.set('genre', filters.genre)
    if (filters.image_role) params.set('image_role', filters.image_role)
    const items = await fetchJson(`${API}/gallery?${params.toString()}`)
    setGallery(items)
  }

  useEffect(() => {
    loadAll()
    loadGallery()
  }, [])

  const handleGenerateSeries = async () => {
    setBusy(true)
    try {
      const res = await fetchJson(`${API}/series/generate`, {
        method: 'POST',
        body: JSON.stringify({}),
      })
      notify(`Created series: ${res.series?.title}`)
      await loadAll()
      await loadGallery()
    } catch (err) {
      notify(`Error: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  const handleProduceEpisode = async (seriesId = null) => {
    setBusy(true)
    try {
      const res = await fetchJson(`${API}/episodes/produce`, {
        method: 'POST',
        body: JSON.stringify({ series_id: seriesId, queue_for_publishing: true }),
      })
      notify(`Produced Ep ${res.episode_number} (QC: ${res.qc_passed ? 'PASSED' : 'FAILED'})`)
      await loadAll()
      await loadGallery()
      if (selectedSeries) {
        const detail = await fetchJson(`${API}/series/${selectedSeries.series.id}`)
        setSelectedSeries(detail)
      }
    } catch (err) {
      notify(`Error: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  const openSeriesDetail = async (id) => {
    const detail = await fetchJson(`${API}/series/${id}`)
    setSelectedSeries(detail)
    setSelectedEpisodeScript(null)
  }

  const openEpisodeScript = async (epId) => {
    const data = await fetchJson(`${API}/episodes/${epId}/script`)
    setSelectedEpisodeScript(data)
  }

  const toggleScheduler = async () => {
    const endpoint = overview?.scheduler_paused ? 'resume' : 'pause'
    await fetchJson(`${API}/scheduler/${endpoint}`, { method: 'POST' })
    notify(`Scheduler ${endpoint}d`)
    await loadAll()
  }

  const handleRetryQueue = async (queueId) => {
    setBusy(true)
    try {
      const res = await fetchJson(`${API}/publishing/retry/${queueId}`, { method: 'POST' })
      notify(`Retry result: ${res.status}${res.error ? ` (${res.error})` : ''}`)
      await loadAll()
    } finally {
      setBusy(false)
    }
  }

  const handleSaveSettings = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const updated = await fetchJson(`${API}/settings`, {
        method: 'PUT',
        body: JSON.stringify({ updates: settings }),
      })
      setSettings(updated)
      notify('Settings saved')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          AI COMIC FACTORY
          <small>Zero-Cost Autonomous Studio</small>
        </div>

        <button className={`nav-btn ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          <LayoutDashboard size={17} /> Overview
        </button>
        <button className={`nav-btn ${tab === 'stories' ? 'active' : ''}`} onClick={() => setTab('stories')}>
          <BookOpen size={17} /> Story Management
        </button>
        <button className={`nav-btn ${tab === 'gallery' ? 'active' : ''}`} onClick={() => { setTab('gallery'); loadGallery() }}>
          <ImageIcon size={17} /> Comic Gallery
        </button>
        <button className={`nav-btn ${tab === 'publishing' ? 'active' : ''}`} onClick={() => setTab('publishing')}>
          <Send size={17} /> Publishing
        </button>
        <button className={`nav-btn ${tab === 'settings' ? 'active' : ''}`} onClick={() => setTab('settings')}>
          <SettingsIcon size={17} /> Settings
        </button>
      </aside>

      <main className="main">
        {toast && (
          <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)', background: 'rgba(245,158,11,0.12)' }}>
            {toast}
          </div>
        )}

        {tab === 'overview' && (
          <>
            <div className="header-row">
              <h1>Studio Overview</h1>
              <div className="actions">
                <button className="btn" onClick={loadAll} disabled={busy}>
                  <RefreshCw size={15} /> Refresh
                </button>
                <button className="btn" onClick={handleGenerateSeries} disabled={busy}>
                  <Plus size={15} /> New Series
                </button>
                <button className="btn btn-primary" onClick={() => handleProduceEpisode(null)} disabled={busy}>
                  <Sparkles size={15} /> {busy ? 'Producing...' : 'Produce Next Episode'}
                </button>
              </div>
            </div>

            {overview && (
              <div className="grid-stats">
                <div className="card"><div className="stat-label">Total Series</div><div className="stat-value">{overview.total_series}</div></div>
                <div className="card"><div className="stat-label">Total Episodes</div><div className="stat-value">{overview.total_episodes}</div></div>
                <div className="card"><div className="stat-label">Generated Pages</div><div className="stat-value">{overview.total_generated_pages}</div></div>
                <div className="card"><div className="stat-label">Published Carousels</div><div className="stat-value">{overview.published_carousel_posts}</div></div>
                <div className="card"><div className="stat-label">Published Pages</div><div className="stat-value">{overview.published_individual_posts}</div></div>
                <div className="card"><div className="stat-label">Scheduled Posts</div><div className="stat-value">{overview.scheduled_posts}</div></div>
                <div className="card"><div className="stat-label">Failed Generations</div><div className="stat-value">{overview.failed_generations}</div></div>
              </div>
            )}

            {health && (
              <div className="card" style={{ marginBottom: 20 }}>
                <h3 style={{ marginTop: 0 }}>Local Engine & API Health</h3>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <span className={`pill ${health.ollama?.online ? 'ok' : 'warn'}`}>
                    Ollama ({health.ollama?.model}): {health.ollama?.online ? 'Online' : 'Offline (Fallback Ready)'}
                  </span>
                  <span className={`pill ${health.comfyui?.online ? 'ok' : 'warn'}`}>
                    ComfyUI: {health.comfyui?.online ? 'Online' : 'Offline (Fallback Renderer Ready)'}
                  </span>
                  <span className={`pill ${health.instagram?.valid ? 'ok' : 'err'}`}>
                    Instagram API: {health.instagram?.valid ? 'Connected' : 'Not Connected'}
                  </span>
                  <span className={`pill ${health.scheduler?.paused ? 'warn' : 'ok'}`}>
                    Scheduler: {health.scheduler?.paused ? 'Paused' : 'Active'}
                  </span>
                </div>
              </div>
            )}

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Recent Automation Runs</h3>
              <table className="table">
                <thead>
                  <tr><th>ID</th><th>Workflow</th><th>Trigger</th><th>Status</th><th>Started</th></tr>
                </thead>
                <tbody>
                  {(overview?.recent_runs || []).map((r) => (
                    <tr key={r.id}>
                      <td>#{r.id}</td>
                      <td>{r.workflow_name}</td>
                      <td>{r.trigger_source}</td>
                      <td><span className={`pill ${r.status === 'completed' ? 'ok' : r.status === 'failed' ? 'err' : 'warn'}`}>{r.status}</span></td>
                      <td>{r.started_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {tab === 'stories' && (
          <>
            <div className="header-row">
              <h1>Story Management</h1>
              <button className="btn btn-primary" onClick={handleGenerateSeries} disabled={busy}>
                <Plus size={15} /> Generate New Series
              </button>
            </div>

            <div className="card" style={{ marginBottom: 20 }}>
              <table className="table">
                <thead>
                  <tr><th>Title</th><th>Genre</th><th>Art Style</th><th>Progress</th><th>Status</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {seriesList.map((s) => (
                    <tr key={s.id}>
                      <td><strong>{s.title}</strong></td>
                      <td>{s.primary_genre}{s.secondary_genre ? ` + ${s.secondary_genre}` : ''}</td>
                      <td>{s.art_style}</td>
                      <td>{s.current_episode} / {s.total_episodes} eps</td>
                      <td><span className={`pill ${s.status === 'completed' ? 'ok' : 'warn'}`}>{s.status}</span></td>
                      <td>
                        <button className="btn" onClick={() => openSeriesDetail(s.id)}>Inspect</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {selectedSeries && (
              <div className="card">
                <div className="header-row">
                  <h2 style={{ margin: 0 }}>{selectedSeries.series.title}</h2>
                  <button className="btn btn-primary" onClick={() => handleProduceEpisode(selectedSeries.series.id)} disabled={busy}>
                    <Sparkles size={15} /> Produce Episode
                  </button>
                </div>
                <p style={{ color: 'var(--muted)' }}>{selectedSeries.series.concept}</p>
                <p><strong>World:</strong> {selectedSeries.series.world_setting}</p>
                <p><strong>Central Conflict:</strong> {selectedSeries.series.central_conflict}</p>

                <h4>Characters ({selectedSeries.characters.length})</h4>
                <div className="grid-stats">
                  {selectedSeries.characters.map((c) => (
                    <div key={c.id} className="card" style={{ background: 'var(--surface-2)' }}>
                      <strong>{c.name}</strong> <span className="pill">{c.role}</span>
                      <div style={{ fontSize: '0.82rem', color: 'var(--muted)', marginTop: 6 }}>
                        <div>Hair: {c.hair_color} {c.hairstyle}</div>
                        <div>Eyes: {c.eye_color}</div>
                        <div>Outfit: {c.clothing}</div>
                      </div>
                    </div>
                  ))}
                </div>

                <h4>Episodes ({selectedSeries.episodes.length})</h4>
                <table className="table">
                  <thead><tr><th>Ep</th><th>Title</th><th>Status</th><th>Action</th></tr></thead>
                  <tbody>
                    {selectedSeries.episodes.map((ep) => (
                      <tr key={ep.id}>
                        <td>#{ep.episode_number}</td>
                        <td>{ep.title}</td>
                        <td><span className="pill ok">{ep.status}</span></td>
                        <td><button className="btn" onClick={() => openEpisodeScript(ep.id)}>View Script</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {selectedEpisodeScript && (
                  <div className="card" style={{ marginTop: 16, background: 'var(--surface-2)' }}>
                    <h4>Episode {selectedEpisodeScript.episode.episode_number}: {selectedEpisodeScript.episode.title}</h4>
                    <p>{selectedEpisodeScript.episode.summary}</p>
                    {selectedEpisodeScript.panels.map((p) => (
                      <div key={p.id} style={{ padding: '8px 0', borderTop: '1px solid var(--border)' }}>
                        <strong>[{p.format_type.toUpperCase()} #{p.panel_order}]</strong> {p.panel_description}
                        <div style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>
                          Narration: {p.narration || '—'} | Dialogue: {p.dialogue_json}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {tab === 'gallery' && (
          <>
            <div className="header-row">
              <h1>Comic Gallery</h1>
              <div className="actions">
                <select
                  value={galleryFilter.series_id}
                  onChange={(e) => {
                    const next = { ...galleryFilter, series_id: e.target.value }
                    setGalleryFilter(next)
                    loadGallery(next)
                  }}
                >
                  <option value="">All Series</option>
                  {seriesList.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
                </select>
                <select
                  value={galleryFilter.image_role}
                  onChange={(e) => {
                    const next = { ...galleryFilter, image_role: e.target.value }
                    setGalleryFilter(next)
                    loadGallery(next)
                  }}
                >
                  <option value="">All Formats</option>
                  <option value="carousel_slide">Carousel Slides</option>
                  <option value="individual_page">Individual Comic Pages</option>
                  <option value="character_ref">Character Reference Sheets</option>
                </select>
              </div>
            </div>

            <div className="gallery-grid">
              {gallery.map((img) => (
                <div key={img.id} className="gallery-item">
                  <img src={img.media_url} alt={img.series_title} loading="lazy" />
                  <div className="gallery-meta">
                    <strong>{img.series_title}</strong>
                    <span style={{ color: 'var(--muted)' }}>
                      {img.image_role} {img.episode_number ? `• Ep ${img.episode_number}` : ''} {img.slide_number ? `#${img.slide_number}` : ''}
                    </span>
                    <a className="btn" href={`${API}/images/${img.id}/download`} style={{ marginTop: 4, textDecoration: 'none', justifyContent: 'center' }}>
                      <Download size={14} /> Download
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {tab === 'publishing' && (
          <>
            <div className="header-row">
              <h1>Publishing Queue & Logs</h1>
              <div className="actions">
                <button className="btn" onClick={toggleScheduler}>
                  {overview?.scheduler_paused ? <><Play size={15} /> Resume Scheduler</> : <><Pause size={15} /> Pause Scheduler</>}
                </button>
              </div>
            </div>

            <div className="card" style={{ marginBottom: 20 }}>
              <h3 style={{ marginTop: 0 }}>Queue</h3>
              <table className="table">
                <thead>
                  <tr><th>Series</th><th>Ep</th><th>Format</th><th>Scheduled</th><th>Status</th><th>IG Media ID</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {queue.map((q) => (
                    <tr key={q.id}>
                      <td>{q.series_title}</td>
                      <td>#{q.episode_number}</td>
                      <td>{q.post_format}</td>
                      <td>{q.scheduled_for}</td>
                      <td><span className={`pill ${q.status === 'published' ? 'ok' : q.status === 'failed' ? 'err' : 'warn'}`}>{q.status}</span></td>
                      <td>{q.instagram_media_id || '—'}</td>
                      <td>
                        {q.status !== 'published' && (
                          <button className="btn" onClick={() => handleRetryQueue(q.id)} disabled={busy}>Retry / Publish</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Recent Publishing Logs</h3>
              <table className="table">
                <thead><tr><th>Time</th><th>Format</th><th>Action</th><th>Status</th><th>Error</th></tr></thead>
                <tbody>
                  {logs.map((l) => (
                    <tr key={l.id}>
                      <td>{l.created_at}</td>
                      <td>{l.post_format}</td>
                      <td>{l.action}</td>
                      <td><span className={`pill ${l.status === 'success' ? 'ok' : 'err'}`}>{l.status}</span></td>
                      <td style={{ color: '#fca5a5' }}>{l.error_message || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {tab === 'settings' && settings && (
          <>
            <div className="header-row">
              <h1>Studio Settings</h1>
            </div>
            <form className="card" onSubmit={handleSaveSettings}>
              <div className="form-grid">
                <div className="field">
                  <label>Default Carousel Slides (5-8)</label>
                  <input type="number" min={5} max={8} value={settings.default_carousel_slides} onChange={(e) => setSettings({ ...settings, default_carousel_slides: Number(e.target.value) })} />
                </div>
                <div className="field">
                  <label>Series Min Episodes</label>
                  <input type="number" min={3} max={20} value={settings.default_series_length_min} onChange={(e) => setSettings({ ...settings, default_series_length_min: Number(e.target.value) })} />
                </div>
                <div className="field">
                  <label>Series Max Episodes</label>
                  <input type="number" min={5} max={30} value={settings.default_series_length_max} onChange={(e) => setSettings({ ...settings, default_series_length_max: Number(e.target.value) })} />
                </div>
                <div className="field">
                  <label>Carousel Publish Hour (0-23)</label>
                  <input type="number" min={0} max={23} value={settings.carousel_publish_hour} onChange={(e) => setSettings({ ...settings, carousel_publish_hour: Number(e.target.value) })} />
                </div>
                <div className="field">
                  <label>Individual Page Publish Hour (0-23)</label>
                  <input type="number" min={0} max={23} value={settings.individual_publish_hour} onChange={(e) => setSettings({ ...settings, individual_publish_hour: Number(e.target.value) })} />
                </div>
                <div className="field">
                  <label>Ollama Local Model</label>
                  <input type="text" value={settings.ollama_model} onChange={(e) => setSettings({ ...settings, ollama_model: e.target.value })} />
                </div>
                <div className="field">
                  <label>ComfyUI Checkpoint</label>
                  <input type="text" value={settings.comfyui_checkpoint} onChange={(e) => setSettings({ ...settings, comfyui_checkpoint: e.target.value })} />
                </div>
                <div className="field">
                  <label>Auto Publish Enabled</label>
                  <select value={String(settings.auto_publish)} onChange={(e) => setSettings({ ...settings, auto_publish: e.target.value === 'true' })}>
                    <option value="true">Enabled (Automatic)</option>
                    <option value="false">Disabled (Manual Queue)</option>
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 18 }}>
                <button className="btn btn-primary" type="submit" disabled={busy}>Save Settings</button>
              </div>
            </form>
          </>
        )}
      </main>
    </div>
  )
}
