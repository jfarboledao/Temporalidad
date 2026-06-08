import { useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const ACCEPTED_EXTENSIONS = ['.krn', '.xml', '.musicxml', '.mxl']

const METRIC_LABELS = {
  flux_rate: 'Flux Rate',
  avg_gestalt: 'Avg Gestalt',
  tension_index: 'Tension Index',
  entropy: 'Entropy',
  vertical_density: 'Vertical Density',
  poly_activity: 'Poly Activity',
}

const CENTURY_METRIC_COLS = [
  { key: 'flux_rate',        label: 'Flux Rate' },
  { key: 'avg_gestalt',      label: 'Avg Gestalt' },
  { key: 'tension_index',    label: 'Tension' },
  { key: 'entropy',          label: 'Entropy' },
  { key: 'vertical_density', label: 'Vert. Density' },
  { key: 'poly_activity',    label: 'Poly Activity' },
]

function centuryLabel(n) {
  const num = parseInt(n, 10)
  if (isNaN(num)) return String(n)
  const mod10 = num % 10
  const mod100 = num % 100
  const suffix = [11, 12, 13].includes(mod100)
    ? 'th'
    : mod10 === 1 ? 'st' : mod10 === 2 ? 'nd' : mod10 === 3 ? 'rd' : 'th'
  return `${num}${suffix} century`
}

function formatError(error) {
  if (!error) return ''
  if (typeof error === 'string') return error
  if (error?.detail) return error.detail
  return 'No se pudo completar el análisis.'
}

function filterValidFiles(fileList) {
  return Array.from(fileList).filter((f) => {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase()
    return ACCEPTED_EXTENSIONS.includes(ext)
  })
}

function fmt(n, decimals = 3) {
  return typeof n === 'number' ? n.toFixed(decimals) : '—'
}

function UploadIcon() {
  return (
    <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}

function FolderIcon() {
  return (
    <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </svg>
  )
}

function AlertIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }} aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}

export function VesselsPage() {
  const filesInputRef = useRef(null)
  const folderInputRef = useRef(null)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState(null)

  const addFiles = (fileList) => {
    const valid = filterValidFiles(fileList)
    if (valid.length === 0) {
      setError('No se encontraron archivos .krn, .xml, .musicxml o .mxl.')
      return
    }
    setError('')
    setResults(null)
    setSelectedFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name))
      const newOnes = valid.filter((f) => !existingNames.has(f.name))
      return [...prev, ...newOnes]
    })
  }

  const clearAll = () => {
    setSelectedFiles([])
    setResults(null)
    setError('')
    if (filesInputRef.current) filesInputRef.current.value = ''
    if (folderInputRef.current) folderInputRef.current.value = ''
  }

  const removeFile = (index) => setSelectedFiles((prev) => prev.filter((_, i) => i !== index))

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true) }
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false) }
  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    addFiles(e.dataTransfer.files)
  }

  const runAnalysis = async () => {
    if (selectedFiles.length === 0) { setError('Selecciona al menos un archivo.'); return }
    const formData = new FormData()
    selectedFiles.forEach((f) => formData.append('files', f))
    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_URL}/api/vessels`, { method: 'POST', body: formData })
      const payload = await response.json()
      if (!response.ok) throw new Error(formatError(payload))
      setResults(payload)
    } catch (err) {
      setResults(null)
      setError(formatError(err.message ?? err))
    } finally {
      setIsLoading(false)
    }
  }

  const fileCount = selectedFiles.length
  const totalKB = Math.max(1, Math.round(selectedFiles.reduce((s, f) => s + f.size, 0) / 1024))

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">MailmansVessels · Temporal Analysis</p>
          <h1>Analyze the shape of time in music.</h1>
          <p className="lead">
            Upload .krn, .xml, or .musicxml files — or an entire folder — and the backend runs{' '}
            <span>analyze_temporal_vessels</span>, computing flux rate, gestalt, tension,
            entropy, and polyphonic density across time windows.
          </p>
          <div className="stats-row">
            <div className="stat-card">
              <span className="stat-value">06</span>
              <span className="stat-label">Vessels measured</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{fileCount || '—'}</span>
              <span className="stat-label">Files queued</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">4 QL</span>
              <span className="stat-label">Default window</span>
            </div>
          </div>
        </div>

        <div
          className={`drop-zone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragEnter={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onClick={() => filesInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              filesInputRef.current?.click()
            }
          }}
        >
          <div className="drop-zone-glow" />
          <div className="drop-zone-inner">
            <div className="drop-zone-icon">
              {fileCount > 0 ? <FolderIcon /> : <UploadIcon />}
            </div>
            <span className="drop-label">{fileCount > 0 ? 'Files selected' : 'Files or folder'}</span>
            <h2>
              {fileCount === 0
                ? 'Drop score files here'
                : `${fileCount} file${fileCount !== 1 ? 's' : ''} selected`}
            </h2>
            <p>
              {fileCount > 0
                ? 'Click to add more files, or drag them here.'
                : 'Click to browse, or drag files here. Use "Select folder" for entire directories.'}
            </p>
            {fileCount > 0 ? (
              <div className="file-meta">
                <span>{fileCount} file{fileCount !== 1 ? 's' : ''}</span>
                <span>{totalKB} KB total</span>
              </div>
            ) : (
              <div className="file-formats">
                {ACCEPTED_EXTENSIONS.map((ext) => (
                  <span key={ext} className="format-badge">{ext}</span>
                ))}
              </div>
            )}
          </div>

          <input
            ref={filesInputRef}
            className="file-input"
            type="file"
            accept={ACCEPTED_EXTENSIONS.join(',')}
            multiple
            onChange={(e) => { if (e.target.files) addFiles(e.target.files) }}
          />
          {/* webkitdirectory enables folder selection in Chrome/Edge/Safari */}
          <input
            ref={folderInputRef}
            className="file-input"
            type="file"
            // eslint-disable-next-line react/no-unknown-property
            webkitdirectory=""
            multiple
            onChange={(e) => { if (e.target.files) addFiles(e.target.files) }}
          />
        </div>
      </section>

      <section className="action-bar">
        <button
          className="primary-button"
          onClick={runAnalysis}
          disabled={isLoading || fileCount === 0}
        >
          {isLoading ? (
            <>
              <span className="btn-spinner" />
              Analyzing {fileCount} file{fileCount !== 1 ? 's' : ''}…
            </>
          ) : 'Run vessels analysis'}
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={(e) => { e.stopPropagation(); folderInputRef.current?.click() }}
        >
          Select folder
        </button>
        {fileCount > 0 && (
          <button className="secondary-button" onClick={clearAll} type="button">
            Clear all
          </button>
        )}
        <span className="hint">{API_URL}/api/vessels</span>
      </section>

      {fileCount > 0 && (
        <section className="file-list-panel">
          <p className="file-list-header">Queued — {fileCount} file{fileCount !== 1 ? 's' : ''}</p>
          <div className="file-chips">
            {selectedFiles.map((f, i) => (
              <div key={`${f.name}-${i}`} className="file-chip">
                <span className="file-chip-name" title={f.name}>{f.name}</span>
                <span className="file-chip-size">{Math.max(1, Math.round(f.size / 1024))} KB</span>
                <button
                  className="file-chip-remove"
                  onClick={() => removeFile(i)}
                  type="button"
                  aria-label={`Remove ${f.name}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {error ? (
        <section className="alert-box">
          <AlertIcon />
          {error}
        </section>
      ) : null}

      {results ? (
        <>
          {results.total_files_skipped > 0 && (
            <section className="alert-box vessels-skipped-box">
              {results.total_files_skipped} archivo
              {results.total_files_skipped !== 1 ? 's omitidos' : ' omitido'}:{' '}
              {results.skipped.map((s) => s.filename).join(', ')}
            </section>
          )}

          {results.century_summary && results.century_summary.rows.length > 0 && (
            <>
              <div className="results-header">
                <span className="results-header-label">Century summary</span>
                <div className="results-header-line" />
              </div>
              <div className="century-summary-block">
                {results.century_summary.files_without_century?.length > 0 && (
                  <p className="century-no-century-note">
                    Century could not be determined for:{' '}
                    {results.century_summary.files_without_century.join(', ')}
                  </p>
                )}
                {results.century_summary.chart && (
                  <article className="result-card graph-card century-chart-card">
                    <p className="card-label">Vessel profile by century — normalized means</p>
                    <img
                      className="graph-image"
                      src={`data:image/png;base64,${results.century_summary.chart}`}
                      alt="Century vessel profile chart"
                    />
                  </article>
                )}
                <article className="result-card table-card century-table-card">
                  <p className="card-label">Mean vessel metrics per century</p>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Century</th>
                          <th>Files</th>
                          {CENTURY_METRIC_COLS.map((c) => (
                            <th key={c.key}>{c.label}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {results.century_summary.rows.map((row, ri) => (
                          <tr key={`century-${row.century}-${ri}`}>
                            <td>{centuryLabel(row.century)}</td>
                            <td>{row.file_count}</td>
                            {CENTURY_METRIC_COLS.map((c) => (
                              <td key={c.key}>{fmt(row[c.key])}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>
              </div>
            </>
          )}

          {results.files.map((fileResult, fi) => (
            <div key={`${fileResult.filename}-${fi}`} className="vessels-file-block">
              <div className="results-header">
                <span className="results-header-label">
                  File {fi + 1} of {results.total_files_processed}
                </span>
                <div className="results-header-line" />
              </div>

              <section className="results-grid">
                <article className="result-card accent-card">
                  <p className="card-label">Vessel summary</p>
                  <h3 className="vessels-filename">{fileResult.filename}</h3>
                  <ul className="summary-list">
                    <li>
                      <span>Windows analyzed</span>
                      <strong>{fileResult.summary.total_windows}</strong>
                    </li>
                    <li>
                      <span>Total beats</span>
                      <strong>{fmt(fileResult.summary.total_beats, 1)}</strong>
                    </li>
                    <li>
                      <span>Avg flux rate</span>
                      <strong>{fmt(fileResult.summary.avg_flux_rate)}</strong>
                    </li>
                    <li>
                      <span>Avg entropy</span>
                      <strong>{fmt(fileResult.summary.avg_entropy)}</strong>
                    </li>
                    <li>
                      <span>Peak entropy beat</span>
                      <strong>{fmt(fileResult.summary.peak_entropy_beat, 1)}</strong>
                    </li>
                    <li>
                      <span>Avg tension index</span>
                      <strong>{fmt(fileResult.summary.avg_tension, 1)}</strong>
                    </li>
                    <li>
                      <span>Avg vertical density</span>
                      <strong>{fmt(fileResult.summary.avg_vertical_density)}</strong>
                    </li>
                    <li>
                      <span>Avg poly activity</span>
                      <strong>{fmt(fileResult.summary.avg_poly_activity)}</strong>
                    </li>
                  </ul>
                </article>

                <article className="result-card table-card">
                  <p className="card-label">
                    Window metrics{fileResult.windows.length > 12 ? ` — first 12 of ${fileResult.windows.length}` : ''}
                  </p>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Beat</th>
                          <th>Flux Rate</th>
                          <th>Avg Gestalt</th>
                          <th>Tension</th>
                          <th>Entropy</th>
                          <th>Vert. Density</th>
                          <th>Poly Activity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {fileResult.windows.slice(0, 12).map((row, ri) => (
                          <tr key={`${row.start_beat}-${ri}`}>
                            <td>{fmt(row.start_beat, 1)}</td>
                            <td>{fmt(row.flux_rate)}</td>
                            <td>{fmt(row.avg_gestalt)}</td>
                            <td>{fmt(row.tension_index, 1)}</td>
                            <td>{fmt(row.entropy)}</td>
                            <td>{fmt(row.vertical_density)}</td>
                            <td>{fmt(row.poly_activity)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>
              </section>

              {fileResult.graficos_normalized && Object.keys(fileResult.graficos_normalized).length > 0 && (
                <section className="vessels-charts-section">
                  <p className="vessels-charts-heading">Vessel profiles — Normalized</p>
                  <div className="vessels-charts-grid">
                    {Object.entries(fileResult.graficos_normalized).map(([metric, b64]) => (
                      <article key={`norm-${metric}`} className="result-card graph-card">
                        <p className="card-label">{METRIC_LABELS[metric] ?? metric}</p>
                        <img
                          className="graph-image"
                          src={`data:image/png;base64,${b64}`}
                          alt={`${METRIC_LABELS[metric] ?? metric} normalized profile`}
                        />
                      </article>
                    ))}
                  </div>
                </section>
              )}

              {fileResult.graficos_raw && Object.keys(fileResult.graficos_raw).length > 0 && (
                <section className="vessels-charts-section">
                  <p className="vessels-charts-heading">Vessel profiles — Raw values</p>
                  <div className="vessels-charts-grid">
                    {Object.entries(fileResult.graficos_raw).map(([metric, b64]) => (
                      <article key={`raw-${metric}`} className="result-card graph-card">
                        <p className="card-label">{METRIC_LABELS[metric] ?? metric}</p>
                        <img
                          className="graph-image"
                          src={`data:image/png;base64,${b64}`}
                          alt={`${METRIC_LABELS[metric] ?? metric} raw profile`}
                        />
                      </article>
                    ))}
                  </div>
                </section>
              )}
            </div>
          ))}
        </>
      ) : null}
    </main>
  )
}
