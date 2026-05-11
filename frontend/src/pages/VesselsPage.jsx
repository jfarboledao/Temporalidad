import { useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const ACCEPTED_EXTENSIONS = ['.krn', '.xml', '.musicxml', '.mxl']

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
            Upload .krn, .xml, or .musicxml files — or an entire folder — and the backend will
            run <span>analyze_temporal_vessels</span>, computing flux rate, gestalt length,
            tension index, and information entropy across time windows.
          </p>
          <div className="stats-row">
            <div className="stat-card">
              <span className="stat-value">04</span>
              <span className="stat-label">vessels measured</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{fileCount}</span>
              <span className="stat-label">files queued</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">4 QL</span>
              <span className="stat-label">default window</span>
            </div>
          </div>
        </div>

        {/* Drop zone — click opens individual file picker; folder picker has its own button */}
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
            <span className="drop-label">Files or folder</span>
            <h2>
              {fileCount === 0
                ? 'Drop score files here'
                : `${fileCount} file${fileCount !== 1 ? 's' : ''} selected`}
            </h2>
            <p>
              Drop .krn / .xml / .musicxml files here, or click to browse. Use
              &ldquo;Select folder&rdquo; below to upload an entire directory at once.
            </p>
            {fileCount > 0 && (
              <div className="file-meta">
                <span>{fileCount} file{fileCount !== 1 ? 's' : ''}</span>
                <span>{totalKB} KB total</span>
              </div>
            )}
          </div>

          {/* Hidden inputs — clicks are routed from the buttons in the action bar */}
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
          {isLoading
            ? `Analyzing ${fileCount} file${fileCount !== 1 ? 's' : ''}…`
            : 'Run vessels analysis'}
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={(e) => { e.stopPropagation(); folderInputRef.current?.click() }}
        >
          Select folder
        </button>
        <button className="secondary-button" onClick={clearAll} type="button">
          Clear all
        </button>
        <span className="hint">Backend: {API_URL}/api/vessels</span>
      </section>

      {/* Queued file chips */}
      {fileCount > 0 && (
        <section className="file-list-panel">
          <p className="file-list-header">Queued files ({fileCount})</p>
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

      {error ? <section className="alert-box">{error}</section> : null}

      {results ? (
        <>
          {/* Skipped files warning */}
          {results.total_files_skipped > 0 && (
            <section className="alert-box vessels-skipped-box">
              {results.total_files_skipped} archivo
              {results.total_files_skipped !== 1 ? 's omitidos' : ' omitido'}:{' '}
              {results.skipped.map((s) => s.filename).join(', ')}
            </section>
          )}

          {/* Per-file results */}
          {results.files.map((fileResult, fi) => (
            <div key={`${fileResult.filename}-${fi}`} className="vessels-file-block">
              <p className="vessels-file-label">
                File {fi + 1} of {results.total_files_processed}
              </p>
              <section className="results-grid">
                {/* Summary card */}
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
                  </ul>
                </article>

                {/* Normalized chart */}
                <article className="result-card graph-card">
                  <p className="card-label">Normalized vessel profile</p>
                  {fileResult.grafico_normalizado ? (
                    <img
                      className="graph-image"
                      src={`data:image/png;base64,${fileResult.grafico_normalizado}`}
                      alt="Normalized vessel profile over relative time"
                    />
                  ) : (
                    <div className="empty-state">No chart data returned.</div>
                  )}
                </article>

                {/* Raw chart */}
                <article className="result-card graph-card">
                  <p className="card-label">Raw vessel profile</p>
                  {fileResult.grafico_raw ? (
                    <img
                      className="graph-image"
                      src={`data:image/png;base64,${fileResult.grafico_raw}`}
                      alt="Raw vessel profile over beats"
                    />
                  ) : (
                    <div className="empty-state">No chart data returned.</div>
                  )}
                </article>

                {/* Window metrics table */}
                <article className="result-card table-card">
                  <p className="card-label">
                    Window metrics{fileResult.windows.length > 12 ? ' (first 12 of ' + fileResult.windows.length + ')' : ''}
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
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>
              </section>
            </div>
          ))}
        </>
      ) : null}
    </main>
  )
}
