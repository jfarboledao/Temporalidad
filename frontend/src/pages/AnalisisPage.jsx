import { useMemo, useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const ACCEPTED_EXTENSIONS = ['.krn', '.xml', '.musicxml', '.mxl']

function UploadIcon() {
  return (
    <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
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

function formatError(error) {
  if (!error) return ''
  if (typeof error === 'string') return error
  if (error?.detail) return error.detail
  return 'No se pudo completar el análisis.'
}

export function AnalisisPage() {
  const inputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState(null)

  const fileLabel = useMemo(() => {
    if (!selectedFile) return 'Drop a score here'
    return selectedFile.name
  }, [selectedFile])

  const clearSelection = () => {
    setSelectedFile(null)
    setAnalysis(null)
    setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  const selectFile = (file) => {
    if (!file) return
    const dotIndex = file.name.lastIndexOf('.')
    const extension = dotIndex >= 0 ? file.name.slice(dotIndex).toLowerCase() : ''
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError('Solo se aceptan archivos .krn, .xml, .musicxml o .mxl.')
      return
    }
    setError('')
    setAnalysis(null)
    setSelectedFile({ file })
  }

  const handleInputChange = (event) => selectFile(event.target.files?.[0])
  const handleDragOver = (event) => { event.preventDefault(); setIsDragging(true) }
  const handleDragLeave = (event) => { event.preventDefault(); setIsDragging(false) }
  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    selectFile(event.dataTransfer.files?.[0])
  }

  const runAnalysis = async () => {
    if (!selectedFile?.file) { setError('Selecciona un archivo primero.'); return }
    const formData = new FormData()
    formData.append('file', selectedFile.file)
    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_URL}/api/analizar`, { method: 'POST', body: formData })
      const payload = await response.json()
      if (!response.ok) throw new Error(formatError(payload))
      setAnalysis(payload)
    } catch (requestError) {
      setAnalysis(null)
      setError(formatError(requestError.message ?? requestError))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Temporalidad polifónica</p>
          <h1>Analyze polyphonic music scores.</h1>
          <p className="lead">
            Upload a score file and the backend runs <span>analizar_polifonia</span>.
            The resulting graphs and interval data are returned and rendered below.
          </p>
          <div className="stats-row">
            <div className="stat-card">
              <span className="stat-value">02</span>
              <span className="stat-label">Graphs generated</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{ACCEPTED_EXTENSIONS.length}</span>
              <span className="stat-label">Formats supported</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">FastAPI</span>
              <span className="stat-label">Analysis backend</span>
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
          onClick={() => inputRef.current?.click()}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              inputRef.current?.click()
            }
          }}
        >
          <div className="drop-zone-glow" />
          <div className="drop-zone-inner">
            <div className="drop-zone-icon">
              {selectedFile ? <FileIcon /> : <UploadIcon />}
            </div>
            <span className="drop-label">{selectedFile ? 'File selected' : 'File input'}</span>
            <h2>{fileLabel}</h2>
            <p>
              {selectedFile
                ? 'Click to replace, or drag a new file here.'
                : 'Click to browse or drag a score file here.'}
            </p>
            {selectedFile?.file ? (
              <div className="file-meta">
                <span>{selectedFile.file.name.split('.').pop()?.toUpperCase()}</span>
                <span>{Math.max(1, Math.round(selectedFile.file.size / 1024))} KB</span>
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
            ref={inputRef}
            className="file-input"
            type="file"
            accept={ACCEPTED_EXTENSIONS.join(',')}
            onChange={handleInputChange}
          />
        </div>
      </section>

      <section className="action-bar">
        <button className="primary-button" onClick={runAnalysis} disabled={isLoading || !selectedFile}>
          {isLoading ? (
            <>
              <span className="btn-spinner" />
              Analyzing…
            </>
          ) : 'Run analysis'}
        </button>
        {selectedFile && (
          <button className="secondary-button" onClick={clearSelection} type="button">
            Clear file
          </button>
        )}
        <span className="hint">{API_URL}/api/analizar</span>
      </section>

      {error ? (
        <section className="alert-box">
          <AlertIcon />
          {error}
        </section>
      ) : null}

      {analysis ? (
        <>
          <div className="results-header">
            <span className="results-header-label">Analysis results</span>
            <div className="results-header-line" />
          </div>
          <section className="results-grid">
            <article className="result-card accent-card">
              <p className="card-label">Summary</p>
              <h3>{analysis.filename}</h3>
              <ul className="summary-list">
                <li>
                  <span>Total events</span>
                  <strong>{analysis.total_eventos}</strong>
                </li>
                <li>
                  <span>Filtered rows</span>
                  <strong>{analysis.resultados.length}</strong>
                </li>
                <li>
                  <span>Status</span>
                  <strong>{analysis.resultados.length > 0 ? 'Ready' : 'No qualifying data'}</strong>
                </li>
              </ul>
            </article>

            <article className="result-card graph-card">
              <p className="card-label">Interval transitions</p>
              {analysis.grafico_resultados ? (
                <img
                  className="graph-image"
                  src={`data:image/png;base64,${analysis.grafico_resultados}`}
                  alt="Heatmap of interval transitions"
                />
              ) : (
                <div className="empty-state">No chart data returned for interval transitions.</div>
              )}
            </article>

            <article className="result-card graph-card">
              <p className="card-label">Movement profile</p>
              {analysis.grafico_movimientos ? (
                <img
                  className="graph-image"
                  src={`data:image/png;base64,${analysis.grafico_movimientos}`}
                  alt="Bar chart of movement types"
                />
              ) : (
                <div className="empty-state">No chart data returned for movement types.</div>
              )}
            </article>

            <article className="result-card table-card">
              <p className="card-label">Raw rows</p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>i_prev</th>
                      <th>mov</th>
                      <th>i_curr</th>
                      <th>v1_delta</th>
                      <th>v2_delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.resultados.slice(0, 12).map((row, index) => (
                      <tr key={`${row.i_prev}-${row.i_curr}-${index}`}>
                        <td>{row.i_prev}</td>
                        <td>{row.mov}</td>
                        <td>{row.i_curr}</td>
                        <td>{row.v1_delta}</td>
                        <td>{row.v2_delta}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </section>
        </>
      ) : null}
    </main>
  )
}
