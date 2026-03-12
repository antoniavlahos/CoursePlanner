import { useState, useEffect, useCallback } from 'react'
import { usePlan } from '../App.jsx'
import { getPlanCourses, removePlanCourse, updatePlanCourse } from '../api.js'

const TERM = { 1: 'Fall', 2: 'Spring', 3: 'Summer' }
const STATUSES = ['planned', 'in_progress', 'completed']

function toRelYear(yearVal, plan) {
  if (!plan) return yearVal
  if (yearVal > plan.duration_years) {
    const rel = yearVal - plan.start_year + 1
    return Math.max(1, Math.min(plan.duration_years, rel))
  }
  return yearVal
}

function GradeModal({ onConfirm, onCancel }) {
  const [grade, setGrade] = useState('')
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-box" style={{ width: 320 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">Enter Grade</div>
        <div className="form-group">
          <label>Grade (A, B, C, D, F, S, U…)</label>
          <input
            autoFocus
            value={grade}
            onChange={(e) => setGrade(e.target.value.toUpperCase())}
            placeholder="e.g. A"
            onKeyDown={(e) => { if (e.key === 'Enter' && grade) onConfirm(grade) }}
          />
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn btn-success" onClick={() => grade && onConfirm(grade)} disabled={!grade}>
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

export default function MyPlan() {
  const { currentPlanId, currentPlan } = usePlan()
  const [planCourses, setPlanCourses] = useState([])
  const [loading, setLoading] = useState(true)
  const [pendingGrade, setPendingGrade] = useState(null) // { pc, nextStatus }

  const reload = useCallback(() => {
    if (!currentPlanId) { setPlanCourses([]); setLoading(false); return }
    setLoading(true)
    getPlanCourses(currentPlanId)
      .then(setPlanCourses)
      .finally(() => setLoading(false))
  }, [currentPlanId])

  useEffect(() => { reload() }, [reload])

  async function handleToggle(pc) {
    const idx = STATUSES.indexOf(pc.status)
    const next = STATUSES[(idx + 1) % STATUSES.length]
    if (next === 'completed') {
      setPendingGrade({ pc, nextStatus: next })
    } else {
      await updatePlanCourse(pc.id, { status: next, grade: null })
      reload()
    }
  }

  async function handleGradeConfirm(grade) {
    const { pc, nextStatus } = pendingGrade
    setPendingGrade(null)
    await updatePlanCourse(pc.id, { status: nextStatus, grade })
    reload()
  }

  async function handleRemove(pc) {
    if (!window.confirm(`Remove ${pc.course.course_number} from your plan?`)) return
    await removePlanCourse(pc.id)
    reload()
  }

  if (!currentPlanId) {
    return (
      <>
        <h1 className="page-title">My Plan</h1>
        <div className="empty-state">
          <h3>No Plan Selected</h3>
          <p>Create or load a plan in <strong>Settings</strong> to get started.</p>
        </div>
      </>
    )
  }

  const totalCredits = planCourses.reduce((s, pc) => s + pc.course.credits, 0)
  const completedCredits = planCourses
    .filter((pc) => pc.status === 'completed')
    .reduce((s, pc) => s + pc.course.credits, 0)

  const sorted = [...planCourses].sort((a, b) => {
    const ay = toRelYear(a.year, currentPlan)
    const by = toRelYear(b.year, currentPlan)
    return ay !== by ? ay - by : a.semester - b.semester
  })

  return (
    <>
      <h1 className="page-title">My Plan</h1>

      {currentPlan && (
        <div className="summary-strip">
          <div>
            <div className="label">Plan</div>
            <div className="value">{currentPlan.name}</div>
          </div>
          <div>
            <div className="label">Department</div>
            <div className="value">{currentPlan.department}</div>
          </div>
          <div>
            <div className="label">Duration</div>
            <div className="value">{currentPlan.duration_years} years ({currentPlan.start_year}–{currentPlan.start_year + currentPlan.duration_years - 1})</div>
          </div>
          <div>
            <div className="label">Credits Planned</div>
            <div className="value">{totalCredits}</div>
          </div>
          <div>
            <div className="label">Credits Completed</div>
            <div className="value" style={{ color: 'var(--green)' }}>{completedCredits}</div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading">Loading plan…</div>
      ) : planCourses.length === 0 ? (
        <div className="empty-state">
          <h3>No Courses in Plan</h3>
          <p>Go to <strong>Course Catalog</strong> to add courses to your plan.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Course #</th>
                <th>Title</th>
                <th>Cr</th>
                <th>Dept</th>
                <th>Year</th>
                <th>Semester</th>
                <th>Status</th>
                <th>Grade</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((pc) => {
                const relYear = toRelYear(pc.year, currentPlan)
                const calYear = currentPlan ? currentPlan.start_year + relYear - 1 : relYear
                return (
                  <tr key={pc.id} className={`row-${pc.status}`}>
                    <td className="mono">{pc.course.course_number}</td>
                    <td>{pc.course.title}</td>
                    <td style={{ textAlign: 'center' }}>{pc.course.credits}</td>
                    <td style={{ textAlign: 'center' }}>{pc.course.department}</td>
                    <td style={{ textAlign: 'center' }}>Yr {relYear} ({calYear})</td>
                    <td style={{ textAlign: 'center' }}>{TERM[pc.semester] || pc.semester}</td>
                    <td>
                      <span className={`status-badge status-${pc.status}`}>
                        {pc.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>{pc.grade || '—'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button
                          className="btn btn-teal btn-sm"
                          onClick={() => handleToggle(pc)}
                          title="Cycle status"
                        >
                          ↻
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleRemove(pc)}
                          title="Remove"
                        >
                          ✕
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {pendingGrade && (
        <GradeModal
          onConfirm={handleGradeConfirm}
          onCancel={() => setPendingGrade(null)}
        />
      )}
    </>
  )
}
