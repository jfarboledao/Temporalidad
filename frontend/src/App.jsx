import { useMemo, useRef, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const ACCEPTED_EXTENSIONS = ['.krn', '.xml', '.musicxml', '.mxl']

function formatError(error) {
  if (!error) {
    return ''
  }

  if (typeof error === 'string') {
    return error
  }

  if (error?.detail) {
    return error.detail
  }

  return 'No se pudo completar el análisis.'
}

function App() {
  const inputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState(null)

  const fileLabel = useMemo(() => {
    if (!selectedFile) {
      return 'Suelta un archivo .krn, .xml, .musicxml o .mxl aquí'
    }

    return selectedFile.name
  }, [selectedFile])

  const clearSelection = () => {
    setSelectedFile(null)
    setAnalysis(null)
    setError('')
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  const selectFile = (file) => {
    if (!file) {
      return
    }

    const dotIndex = file.name.lastIndexOf('.')
    const extension = dotIndex >= 0 ? file.name.slice(dotIndex).toLowerCase() : ''
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError('Solo se aceptan archivos .krn, .xml, .musicxml o .mxl.')
      return
    }

    setError('')
    setAnalysis(null)
    setSelectedFile({
      file,
    })
  }

  const handleInputChange = (event) => {
    const file = event.target.files?.[0]
    selectFile(file)
  }

  const handleDragOver = (event) => {
    event.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (event) => {
    event.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    const file = event.dataTransfer.files?.[0]
    selectFile(file)
  }

  const runAnalysis = async () => {
    if (!selectedFile?.file) {
      setError('Selecciona un archivo primero.')
      return
    }

    const formData = new FormData()
    formData.append('file', selectedFile.file)

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/api/analizar`, {
        method: 'POST',
        body: formData,
      })

      const payload = await response.json()
      if (!response.ok) {
        throw new Error(formatError(payload))
      }

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
          <h1>Drop a score, get the analysis graphs.</h1>
          <p className="lead">
            Upload a .krn, .xml, .musicxml, or .mxl file and the backend will run
            <span>analizar_polifonia</span>. The resulting plots are returned to the
            browser and rendered below.
          </p>

          <div className="stats-row">
            <div className="stat-card">
              <span className="stat-value">02</span>
              <span className="stat-label">graphs generated</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{ACCEPTED_EXTENSIONS.length}</span>
              <span className="stat-label">supported formats</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">FastAPI</span>
              <span className="stat-label">analysis backend</span>
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
            <span className="drop-label">File input</span>
            <h2>{fileLabel}</h2>
            <p>Drop the score here or click to browse your files.</p>
            {selectedFile?.file ? (
              <div className="file-meta">
                <span>{selectedFile.file.type || 'unknown type'}</span>
                <span>{Math.max(1, Math.round(selectedFile.file.size / 1024))} KB</span>
              </div>
            ) : null}
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
          {isLoading ? 'Analyzing...' : 'Run analysis'}
        </button>
        <button className="secondary-button" onClick={clearSelection} type="button">
          Clear file
        </button>
        <span className="hint">Backend endpoint: {API_URL}/api/analizar</span>
      </section>

      {error ? <section className="alert-box">{error}</section> : null}

      {analysis ? (
        <section className="results-grid">
          <article className="result-card accent-card">
            <p className="card-label">Analysis summary</p>
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
      ) : null}
    </main>
  )
}

export default App
