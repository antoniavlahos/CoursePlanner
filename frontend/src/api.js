const BASE = '/api'

function getToken() {
  return localStorage.getItem('authToken')
}

async function req(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(BASE + path, { headers, ...options })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const register = (email, password, firstName, lastName) =>
  req('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, first_name: firstName, last_name: lastName }) })

export const login = (email, password) =>
  req('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })

export const getMe = () => req('/auth/me')
export const updateMe = (firstName, lastName) =>
  req('/auth/me', { method: 'PATCH', body: JSON.stringify({ first_name: firstName, last_name: lastName }) })

// ── Courses ───────────────────────────────────────────────────────────────────
export const getCourses = (q = '', dept = '') =>
  req(`/courses?q=${encodeURIComponent(q)}&dept=${encodeURIComponent(dept)}`)

export const getCourse = (id) => req(`/courses/${id}`)

// ── Departments ───────────────────────────────────────────────────────────────
export const getDepartments = () => req('/departments')
export const getDeptRequirements = (code) => req(`/departments/${code}/requirements`)
export const getUniversityRequirements = () => req('/requirements')

// ── Plans ─────────────────────────────────────────────────────────────────────
export const getPlans = () => req('/plans')
export const getPlan = (id) => req(`/plans/${id}`)
export const createPlan = (body) => req('/plans', { method: 'POST', body: JSON.stringify(body) })
export const deletePlan  = (id)       => req(`/plans/${id}`, { method: 'DELETE' })
export const updatePlan  = (id, body) => req(`/plans/${id}`, { method: 'PATCH', body: JSON.stringify(body) })

// ── Plan Courses ──────────────────────────────────────────────────────────────
export const getPlanCourses = (planId) => req(`/plans/${planId}/courses`)
export const addCourseToPlan = (planId, body) =>
  req(`/plans/${planId}/courses`, { method: 'POST', body: JSON.stringify(body) })
export const removePlanCourse = (pcId) => req(`/plan-courses/${pcId}`, { method: 'DELETE' })
export const updatePlanCourse = (pcId, body) =>
  req(`/plan-courses/${pcId}`, { method: 'PATCH', body: JSON.stringify(body) })

// ── Plan Sharing ──────────────────────────────────────────────────────────────
export const createShareLink  = (planId) => req(`/plans/${planId}/share`, { method: 'POST' })
export const revokeShareLink  = (planId) => req(`/plans/${planId}/share`, { method: 'DELETE' })
export const getSharedPlan    = (token)  => req(`/shared/${token}`)
export const getSharedPlanCourses = (token) => req(`/shared/${token}/courses`)

// ── PDF Export ────────────────────────────────────────────────────────────────
export async function downloadPlanPdf(planId) {
  const token = localStorage.getItem('authToken')
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}/plans/${planId}/pdf`, { headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || `HTTP ${res.status}`)
  }
  return res.blob()
}

// ── AI ────────────────────────────────────────────────────────────────────────
export const getAiStatus = () => req('/ai/status')
export const getAiRecommendations = (body) =>
  req('/ai/recommend', { method: 'POST', body: JSON.stringify(body) })
export const getAiProgramPlan = (body) =>
  req('/ai/program-plan', { method: 'POST', body: JSON.stringify(body) })
