import { useState, useEffect } from 'react'
import { usePlan } from '../App.jsx'
import { getPlans, createPlan, deletePlan, getDepartments } from '../api.js'

function CreatePlanModal({ departments, onCreated, onClose }) {
  const [name, setName] = useState('')
  const [duration, setDuration] = useState(4)
  const [startYear, setStartYear] = useState(new Date().getFullYear())
  const [dept, setDept] = useState(departments[0]?.code ?? 'CS')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleCreate() {
    if (!name.trim()) { setError('Plan name is required.'); return }
    setLoading(true)
    setError('')
    try {
      const plan = await createPlan({ name: name.trim(), duration_years: duration, start_year: startYear, department: dept })
      onCreated(plan)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">Create New Plan</div>

        <div className="form-group">
          <label>Plan Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. CS 4-Year Plan" autoFocus />
        </div>

        <div className="form-group">
          <label>Department / Major</label>
          <select value={dept} onChange={(e) => setDept(e.target.value)}>
            {departments.map((d) => (
              <option key={d.code} value={d.code}>{d.code} – {d.name}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group">
            <label>Duration (years)</label>
            <select value={duration} onChange={(e) => setDuration(+e.target.value)}>
              {[3, 4, 5].map((y) => <option key={y} value={y}>{y} years</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Start Year</label>
            <input type="number" value={startYear} onChange={(e) => setStartYear(+e.target.value)} min={2020} max={2040} />
          </div>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-success" onClick={handleCreate} disabled={loading}>
            {loading ? 'Creating…' : 'Create Plan'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Settings() {
  const { currentPlanId, currentPlan, setCurrentPlanId } = usePlan()
  const [plans, setPlans] = useState([])
  const [departments, setDepartments] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)

  const reload = () => {
    setLoading(true)
    Promise.all([getPlans(), getDepartments()])
      .then(([p, d]) => { setPlans(p); setDepartments(d) })
      .finally(() => setLoading(false))
  }
  useEffect(reload, [])

  async function handleDelete(id) {
    if (!window.confirm('Delete this plan? This cannot be undone.')) return
    await deletePlan(id)
    if (currentPlanId === id) setCurrentPlanId(null)
    reload()
  }

  function handleLoad(plan) {
    setCurrentPlanId(plan.id)
  }

  return (
    <>
      <h1 className="page-title">Settings</h1>

      {/* Current Plan */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Current Plan</div>
        {currentPlan ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--blue)' }}>{currentPlan.name}</div>
              <div style={{ fontSize: '.82rem', color: 'var(--muted)', marginTop: 2 }}>
                {currentPlan.department} · {currentPlan.duration_years} years · {currentPlan.start_year}–{currentPlan.start_year + currentPlan.duration_years - 1}
              </div>
            </div>
            <button className="btn btn-danger btn-sm" onClick={() => handleDelete(currentPlan.id)}>
              Delete Plan
            </button>
          </div>
        ) : (
          <p style={{ color: 'var(--muted)', margin: 0 }}>No plan selected. Create or load a plan below.</p>
        )}
      </div>

      {/* Create plan */}
      <div className="action-bar">
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>+ Create New Plan</button>
      </div>

      {/* Plan list */}
      <div className="card">
        <div className="card-title">All Plans</div>
        {loading ? (
          <div className="loading">Loading…</div>
        ) : plans.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>No plans yet. Create your first plan above.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Dept</th>
                <th>Duration</th>
                <th>Start Year</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p.id} style={{ background: p.id === currentPlanId ? '#f0f4ff' : undefined }}>
                  <td>
                    {p.name}
                    {p.id === currentPlanId && (
                      <span style={{ marginLeft: 8, fontSize: '.72rem', background: 'var(--gold)', color: 'var(--blue)', padding: '1px 7px', borderRadius: 12, fontWeight: 700 }}>active</span>
                    )}
                  </td>
                  <td>{p.department}</td>
                  <td>{p.duration_years} yrs</td>
                  <td>{p.start_year}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => handleLoad(p)}>
                        Load
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p.id)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreatePlanModal
          departments={departments}
          onCreated={(p) => { setCurrentPlanId(p.id); reload() }}
          onClose={() => setShowCreate(false)}
        />
      )}
    </>
  )
}
