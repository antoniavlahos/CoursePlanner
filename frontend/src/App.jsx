import { createContext, useContext, useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, NavLink, useNavigate } from 'react-router-dom'
import Catalog from './pages/Catalog.jsx'
import MyPlan from './pages/MyPlan.jsx'
import Requirements from './pages/Requirements.jsx'
import AiPlanner from './pages/AiPlanner.jsx'
import Settings from './pages/Settings.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import { getPlan, getMe } from './api.js'

// ── Auth Context ───────────────────────────────────────────────────────────────
const AuthContext = createContext({ auth: null, setAuth: () => {}, logout: () => {} })
export function useAuth() { return useContext(AuthContext) }

// ── Plan Context ───────────────────────────────────────────────────────────────
export const PlanContext = createContext({
  currentPlanId: null,
  currentPlan: null,
  setCurrentPlanId: () => {},
})
export function usePlan() { return useContext(PlanContext) }

// ── Sidebar ────────────────────────────────────────────────────────────────────
const NAV = [
  { to: '/catalog',      icon: '📚', label: 'Course Catalog' },
  { to: '/plan',         icon: '📋', label: 'My Plan' },
  { to: '/requirements', icon: '✅', label: 'Requirements' },
  { to: '/ai',           icon: '🤖', label: 'AI Planner' },
  { to: '/settings',     icon: '⚙️',  label: 'Settings' },
]

function Sidebar() {
  const { currentPlan } = usePlan()
  const { auth, logout } = useAuth()
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
        <div className="sidebar-user">
          <span className="sidebar-user-email">{auth?.user?.email}</span>
          <button className="btn btn-outline btn-sm btn-full" onClick={logout}>Sign out</button>
        </div>
      </div>
    </nav>
  )
}

// ── Protected layout ───────────────────────────────────────────────────────────
function AppLayout() {
  const { auth } = useAuth()
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

  if (!auth) return <Navigate to="/login" replace />

  return (
    <PlanContext.Provider value={{ currentPlanId, currentPlan, setCurrentPlanId }}>
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
    </PlanContext.Provider>
  )
}

// ── App ────────────────────────────────────────────────────────────────────────
export default function App() {
  const [auth, setAuth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('authToken')
    if (!token) { setLoading(false); return }
    getMe()
      .then(user => setAuth({ user, token }))
      .catch(() => localStorage.removeItem('authToken'))
      .finally(() => setLoading(false))
  }, [])

  function logout() {
    localStorage.removeItem('authToken')
    localStorage.removeItem('currentPlanId')
    setAuth(null)
  }


  if (loading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#F0F2F5' }}>Loading…</div>
  }

  return (
    <AuthContext.Provider value={{ auth, setAuth, logout }}>
      <Router>
        <Routes>
          <Route path="/login" element={auth ? <Navigate to="/catalog" replace /> : <Login />} />
          <Route path="/register" element={auth ? <Navigate to="/catalog" replace /> : <Register />} />
          <Route path="/*" element={<AppLayout />} />
        </Routes>
      </Router>
    </AuthContext.Provider>
  )
}
