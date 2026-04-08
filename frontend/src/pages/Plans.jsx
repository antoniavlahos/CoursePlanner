import { useState, useEffect } from 'react'
import { usePlan } from '../App.jsx'
import { getPlans, createPlan, deletePlan, updatePlan, getDepartments, createShareLink, revokeShareLink } from '../api.js'

const PLAN_TYPES = [
  { value: 'single',       label: 'Single Major' },
  { value: 'double_major', label: 'Double Major' },
  { value: 'major_minor',  label: 'Major + Minor' },
]

function CreatePlanModal({ departments, onCreated, onClose }) {
  const [name, setName]           = useState('')
  const [duration, setDuration]   = useState(4)
  const [startYear, setStartYear] = useState(new Date().getFullYear())
  const [dept, setDept]           = useState(departments[0]?.code ?? 'CS')
  const [planType, setPlanType]   = useState('single')
  const [secondaryDept, setSecondaryDept] = useState(departments[1]?.code ?? '')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')

  const needsSecondary = planType !== 'single'
  const secondaryLabel = planType === 'major_minor' ? 'Minor' : 'Second Major'

  async function handleCreate() {
    if (!name.trim()) { setError('Plan name is required.'); return }
    if (needsSecondary && !secondaryDept) { setError(`${secondaryLabel} is required.`); return }
    if (needsSecondary && secondaryDept === dept) { setError(`${secondaryLabel} must differ from the primary major.`); return }
    setLoading(true)
    setError('')
    try {
      const plan = await createPlan({
        name: name.trim(),
        duration_years: duration,
        start_year: startYear,
        department: dept,
        plan_type: planType,
        secondary_department: needsSecondary ? secondaryDept : '',
      })
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
          <label>Plan Type</label>
          <div className="pill-group">
            {PLAN_TYPES.map(({ value, label }) => (
              <label key={value}>
                <input type="radio" name="planType" value={value} checked={planType === value} onChange={() => setPlanType(value)} />
                {label}
              </label>
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: needsSecondary ? '1fr 1fr' : '1fr', gap: 12 }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label>{needsSecondary ? 'Primary Major' : 'Department / Major'}</label>
            <select value={dept} onChange={(e) => setDept(e.target.value)}>
              {departments.map((d) => (
                <option key={d.code} value={d.code}>{d.code} – {d.name}</option>
              ))}
            </select>
          </div>
          {needsSecondary && (
            <div className="form-group" style={{ margin: 0 }}>
              <label>{secondaryLabel}</label>
              <select value={secondaryDept} onChange={(e) => setSecondaryDept(e.target.value)}>
                {departments.map((d) => (
                  <option key={d.code} value={d.code}>{d.code} – {d.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
          <div className="form-group">
            <label>Duration (years)</label>
            <select value={duration} onChange={(e) => setDuration(+e.target.value)}>
              {[2, 3, 4, 5, 6].map((y) => <option key={y} value={y}>{y} years</option>)}
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

function EditPlanModal({ plan, departments, onSaved, onClose }) {
  const [name, setName]           = useState(plan.name)
  const [duration, setDuration]   = useState(plan.duration_years)
  const [startYear, setStartYear] = useState(plan.start_year)
  const [dept, setDept]           = useState(plan.department)
  const [planType, setPlanType]   = useState(plan.plan_type ?? 'single')
  const [secondaryDept, setSecondaryDept] = useState(plan.secondary_department ?? '')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')

  const needsSecondary = planType !== 'single'
  const secondaryLabel = planType === 'major_minor' ? 'Minor' : 'Second Major'

  async function handleSave() {
    if (!name.trim()) { setError('Plan name is required.'); return }
    if (needsSecondary && !secondaryDept) { setError(`${secondaryLabel} is required.`); return }
    if (needsSecondary && secondaryDept === dept) { setError(`${secondaryLabel} must differ from the primary major.`); return }
    setLoading(true)
    setError('')
    try {
      const updated = await updatePlan(plan.id, {
        name: name.trim(),
        duration_years: duration,
        start_year: startYear,
        department: dept,
        plan_type: planType,
        secondary_department: needsSecondary ? secondaryDept : '',
      })
      onSaved(updated)
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
        <div className="modal-title">Edit Plan</div>

        <div className="form-group">
          <label>Plan Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>

        <div className="form-group">
          <label>Plan Type</label>
          <div className="pill-group">
            {PLAN_TYPES.map(({ value, label }) => (
              <label key={value}>
                <input type="radio" name="editPlanType" value={value} checked={planType === value} onChange={() => setPlanType(value)} />
                {label}
              </label>
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: needsSecondary ? '1fr 1fr' : '1fr', gap: 12 }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label>{needsSecondary ? 'Primary Major' : 'Department / Major'}</label>
            <select value={dept} onChange={(e) => setDept(e.target.value)}>
              {departments.map((d) => (
                <option key={d.code} value={d.code}>{d.code} – {d.name}</option>
              ))}
            </select>
          </div>
          {needsSecondary && (
            <div className="form-group" style={{ margin: 0 }}>
              <label>{secondaryLabel}</label>
              <select value={secondaryDept} onChange={(e) => setSecondaryDept(e.target.value)}>
                {departments.map((d) => (
                  <option key={d.code} value={d.code}>{d.code} – {d.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
          <div className="form-group">
            <label>Duration (years)</label>
            <select value={duration} onChange={(e) => setDuration(+e.target.value)}>
              {[2, 3, 4, 5, 6].map((y) => <option key={y} value={y}>{y} years</option>)}
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
          <button className="btn btn-success" onClick={handleSave} disabled={loading}>
            {loading ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Plans() {
  const { currentPlanId, currentPlan, setCurrentPlanId } = usePlan()

  const [plans, setPlans]           = useState([])
  const [departments, setDepartments] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [editingPlan, setEditingPlan] = useState(null)
  const [loading, setLoading]       = useState(true)

  // ── Share link state ────────────────────────────────────────────────────────
  const [shareToken,   setShareToken]   = useState(null)
  const [shareWorking, setShareWorking] = useState(false)
  const [copied,       setCopied]       = useState(false)

  useEffect(() => {
    setShareToken(currentPlan?.share_token ?? null)
    setCopied(false)
  }, [currentPlan?.id])

  const shareUrl = shareToken ? `${window.location.origin}/shared/${shareToken}` : null

  async function handleGenerateLink() {
    if (!currentPlanId) return
    setShareWorking(true)
    try {
      const data = await createShareLink(currentPlanId)
      setShareToken(data.share_token)
    } catch (err) {
      alert('Could not generate link: ' + err.message)
    } finally {
      setShareWorking(false)
    }
  }

  async function handleRevokeLink() {
    if (!window.confirm('Revoke this link? Anyone with the current link will lose access.')) return
    setShareWorking(true)
    try {
      await revokeShareLink(currentPlanId)
      setShareToken(null)
      setCopied(false)
    } catch (err) {
      alert('Could not revoke link: ' + err.message)
    } finally {
      setShareWorking(false)
    }
  }

  function handleCopy() {
    if (!shareUrl) return
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    })
  }

  useEffect(() => {
    getDepartments().then(setDepartments).catch(() => {})
  }, [])

  const reload = () => {
    setLoading(true)
    getPlans()
      .then(setPlans)
      .catch(() => {})
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
      <h1 className="page-title">Plans</h1>

      {/* Current Plan */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Current Plan</div>
        {currentPlan ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--blue)' }}>{currentPlan.name}</div>
              <div style={{ fontSize: '.82rem', color: 'var(--muted)', marginTop: 2 }}>
                {currentPlan.plan_type === 'double_major' && currentPlan.secondary_department
                  ? `${currentPlan.department} & ${currentPlan.secondary_department}`
                  : currentPlan.plan_type === 'major_minor' && currentPlan.secondary_department
                  ? `${currentPlan.department} + ${currentPlan.secondary_department} (Minor)`
                  : currentPlan.department
                } · {currentPlan.duration_years} years · {currentPlan.start_year}–{currentPlan.start_year + currentPlan.duration_years - 1}
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

      {/* Share Plan */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Share Plan</div>
        {!currentPlan ? (
          <p style={{ color: 'var(--muted)', margin: 0 }}>Select a plan to generate a shareable link.</p>
        ) : shareUrl ? (
          <>
            <p style={{ fontSize: '.84rem', color: 'var(--muted)', marginTop: 0, marginBottom: 10 }}>
              Anyone with this link can view <strong>{currentPlan.name}</strong> in read-only mode — no login required.
            </p>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
              <input
                readOnly
                value={shareUrl}
                style={{
                  flex: 1, padding: '7px 10px', borderRadius: 6,
                  border: '1px solid var(--border)', fontSize: '.82rem',
                  background: '#f9fafb', color: '#374151', cursor: 'text',
                }}
                onFocus={(e) => e.target.select()}
              />
              <button className="btn btn-primary btn-sm" onClick={handleCopy}>
                {copied ? '✓ Copied!' : 'Copy'}
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <a
                href={shareUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-outline btn-sm"
                style={{ color: '#000', textDecoration: 'none' }}
              >
                Preview ↗
              </a>
              <button className="btn btn-danger btn-sm" onClick={handleRevokeLink} disabled={shareWorking}>
                {shareWorking ? 'Revoking…' : 'Revoke Link'}
              </button>
            </div>
          </>
        ) : (
          <>
            <p style={{ fontSize: '.84rem', color: 'var(--muted)', marginTop: 0, marginBottom: 12 }}>
              Generate a read-only link for <strong>{currentPlan.name}</strong> that anyone can view without logging in.
            </p>
            <button className="btn btn-primary" onClick={handleGenerateLink} disabled={shareWorking}>
              {shareWorking ? 'Generating…' : '🔗 Generate Share Link'}
            </button>
          </>
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
                      <button className="btn btn-sm" style={{ background: '#000', color: '#fff', borderColor: '#000' }} onClick={() => setEditingPlan(p)}>
                        Edit
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

      {editingPlan && (
        <EditPlanModal
          plan={editingPlan}
          departments={departments}
          onSaved={(updated) => {
            reload()
            if (updated.id === currentPlanId) setCurrentPlanId(updated.id)
          }}
          onClose={() => setEditingPlan(null)}
        />
      )}
    </>
  )
}
