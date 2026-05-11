import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Navbar } from './components/Navbar'
import { AnalisisPage } from './pages/AnalisisPage'
import { VesselsPage } from './pages/VesselsPage'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<AnalisisPage />} />
        <Route path="/vessels" element={<VesselsPage />} />
      </Routes>
    </BrowserRouter>
  )
}
