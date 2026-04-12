/**
 * App.jsx
 *
 * Root component. Defines all client-side routes using react-router-dom.
 * Every URL maps to exactly one page component.
 */

import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import DashboardPage from './pages/DashboardPage'
import WaitingPage   from './pages/WaitingPage'
import AssignedPage  from './pages/AssignedPage'
import SearchPage    from './pages/SearchPage'
import GoalsPage     from './pages/GoalsPage'

export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Navbar />
      <main>
        <Routes>
          <Route path="/"         element={<DashboardPage />} />
          <Route path="/waiting"  element={<WaitingPage />} />
          <Route path="/assigned" element={<AssignedPage />} />
          <Route path="/search"   element={<SearchPage />} />
          <Route path="/goals"    element={<GoalsPage />} />
        </Routes>
      </main>
    </div>
  )
}
