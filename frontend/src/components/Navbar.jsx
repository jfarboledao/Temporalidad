import { NavLink } from 'react-router-dom'

export function Navbar() {
  return (
    <nav className="app-nav">
      <span className="app-nav-logo">Temporalidad</span>
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
    </nav>
  )
}
