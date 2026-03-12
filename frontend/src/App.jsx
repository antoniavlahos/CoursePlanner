import { createContext, useContext, useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom'
import Catalog from './pages/Catalog.jsx'
import MyPlan from './pages/MyPlan.jsx'
import Requirements from './pages/Requirements.jsx'
import AiPlanner from './pages/AiPlanner.jsx'
import Settings from './pages/Settings.jsx'
import { getPlan } from './api.js'

// ── Plan Context ──────────────────────────────────────────────────────────────
export const PlanContext = createContext({
  currentPlanId: null,
  currentPlan: null,
  setCurrentPlanId: () => {},
})

export function usePlan() {
  return useContext(PlanContext)
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
const NAV = [
  { to: '/catalog',      icon: '📚', label: 'Course Catalog' },
  { to: '/plan',         icon: '📋', label: 'My Plan' },
  { to: '/requirements', icon: '✅', label: 'Requirements' },
  { to: '/ai',           icon: '🤖', label: 'AI Planner' },
  { to: '/settings',     icon: '⚙️',  label: 'Settings' },
]

function Sidebar() {
  const { currentPlan, setCurrentPlanId } = usePlan()
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <img src="/purdue-logo.svg" alt="Purdue University" className="sidebar-logo" />
        <span className="sidebar-subtitle">Course Planner</span>
      </div>
      <hr className="sidebar-divider" />
      {NAV.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}
        >
          <span>{icon}</span>
          <span>{label}</span>
        </NavLink>
      ))}
      <hr className="sidebar-divider" />
      {currentPlan ? (
        <div className="sidebar-plan">
          <div className="label">Current Plan</div>
          <div className="name">{currentPlan.name}</div>
          <div className="detail">{currentPlan.department} · {currentPlan.duration_years}yr · {currentPlan.start_year}</div>
        </div>
      ) : (
        <div className="sidebar-plan">
          <div className="label">No plan selected</div>
        </div>
      )}
      <div className="sidebar-btns">
        <NavLink to="/settings" className="btn btn-gold btn-full btn-sm">+ New / Load Plan</NavLink>
      </div>
    </nav>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [currentPlanId, setCurrentPlanIdRaw] = useState(() => {
    const stored = localStorage.getItem('currentPlanId')
    return stored ? parseInt(stored, 10) : null
  })
  const [currentPlan, setCurrentPlan] = useState(null)

  const setCurrentPlanId = (id) => {
    setCurrentPlanIdRaw(id)
    if (id) localStorage.setItem('currentPlanId', id)
    else localStorage.removeItem('currentPlanId')
  }

  useEffect(() => {
    if (!currentPlanId) { setCurrentPlan(null); return }
    getPlan(currentPlanId)
      .then(setCurrentPlan)
      .catch(() => { setCurrentPlan(null); setCurrentPlanId(null) })
  }, [currentPlanId])

  return (
    <PlanContext.Provider value={{ currentPlanId, currentPlan, setCurrentPlanId }}>
      <Router>
        <div className="layout">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Navigate to="/catalog" replace />} />
              <Route path="/catalog" element={<Catalog />} />
              <Route path="/plan" element={<MyPlan />} />
              <Route path="/requirements" element={<Requirements />} />
              <Route path="/ai" element={<AiPlanner />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </Router>
    </PlanContext.Provider>
  )
}
