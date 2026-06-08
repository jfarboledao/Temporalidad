import { NavLink } from 'react-router-dom'

function MusicIcon() {
  return (
    <svg
      className="nav-logo-icon"
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </svg>
  )
}

export function Navbar() {
  return (
    <nav className="app-nav">
      <div className="app-nav-logo">
        <MusicIcon />
        <span>Temporalidad</span>
      </div>
      <div className="app-nav-links">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          Análisis Polifónico
        </NavLink>
        <NavLink
          to="/vessels"
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          Temporal Vessels
        </NavLink>
      </div>
      <div className="nav-spacer" />
      <span className="nav-badge">v1.0</span>
    </nav>
  )
}
