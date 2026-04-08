import { useState, useEffect, useCallback, useRef } from 'react'
import { usePlan } from '../App.jsx'
import { getPlanCourses, removePlanCourse, updatePlanCourse, downloadPlanPdf, getCourses, addCourseToPlan, createShareLink } from '../api.js'
import CourseDetailDrawer from '../components/CourseDetailDrawer.jsx'

const TERM = { 1: 'Fall', 2: 'Spring', 3: 'Summer' }
const STATUSES = ['planned', 'in_progress', 'completed']

const STATUS_COLOR = {
  planned:     '#9ca3af',
  in_progress: '#f59e0b',
  completed:   '#22c55e',
}
const STATUS_LABEL = {
  planned:     'Planned',
  in_progress: 'In Progress',
  completed:   'Completed',
}

// ── GPA helpers ───────────────────────────────────────────────────────────────
const GRADE_POINTS = {
  'A+': 4.0, 'A': 4.0, 'A-': 3.7,
  'B+': 3.3, 'B': 3.0, 'B-': 2.7,
  'C+': 2.3, 'C': 2.0, 'C-': 1.7,
  'D+': 1.3, 'D': 1.0, 'D-': 0.7,
  'F': 0.0,
}

function gradePoints(grade) {
  if (!grade) return null
  return GRADE_POINTS[grade.trim().toUpperCase()] ?? null  // S/U/W not counted
}

function calcGPA(items) {  // [{credits, grade}]
  let totalPts = 0, totalCr = 0
  for (const { credits, grade } of items) {
    const pts = gradePoints(grade)
    if (pts !== null) { totalPts += pts * credits; totalCr += credits }
  }
  return totalCr > 0 ? (totalPts / totalCr).toFixed(2) : null
}

function gpaColor(gpa) {
  if (gpa === null) return 'var(--muted)'
  const n = parseFloat(gpa)
  if (n >= 3.5) return '#22c55e'
  if (n >= 3.0) return '#84cc16'
  if (n >= 2.0) return '#f59e0b'
  return '#ef4444'
}

function toRelYear(yearVal, plan) {
  if (!plan) return yearVal
  if (yearVal > plan.duration_years) {
    const rel = yearVal - plan.start_year + 1
    return Math.max(1, Math.min(plan.duration_years, rel))
  }
  return yearVal
}

// ── Share modal ───────────────────────────────────────────────────────────────
function ShareModal({ url, onClose }) {
  const [copied, setCopied] = useState(false)

  async function handleOk() {
    let ok = false
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(url); ok = true } catch { /* fall through */ }
    }
    if (!ok) {
      const ta = document.createElement('textarea')
      ta.value = url
      ta.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0'
      document.body.appendChild(ta)
      ta.focus(); ta.select()
      ok = document.execCommand('copy')
      document.body.removeChild(ta)
    }
    if (ok) { setCopied(true); setTimeout(onClose, 900) }
    else onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" style={{ width: 420 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">Share Plan</div>
        <p style={{ margin: '0 0 10px', fontSize: '.9rem', color: 'var(--muted)' }}>
          Anyone with this link can view a read-only copy of your plan.
        </p>
        <div className="form-group">
          <input
            readOnly
            value={url}
            onFocus={(e) => e.target.select()}
            style={{ fontFamily: 'monospace', fontSize: '.8rem' }}
          />
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-success" onClick={handleOk}>
            {copied ? '✓ Copied!' : 'OK — Copy Link'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Grade modal ───────────────────────────────────────────────────────────────
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

// ── Plan semester card ────────────────────────────────────────────────────────
function PlanSemesterCard({
  label, courses, semGpa, cumGpa,
  onToggle, onRemove, onViewDetails,
  isDragOver,
  onDragOver, onDrop, onDragLeave, onDragStart,
}) {
  const totalCredits = courses.reduce((s, pc) => s + pc.course.credits, 0)

  return (
    <div
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragLeave={onDragLeave}
      style={{
        border: isDragOver ? '2px dashed var(--gold)' : '1px solid var(--border)',
        borderRadius: 10, overflow: 'hidden',
        background: isDragOver ? '#fffdf5' : '#fff',
        transition: 'border .12s, background .12s',
        minHeight: 80,
      }}
    >
      {/* Header */}
      <div style={{
        background: 'var(--blue)', color: '#fff',
        padding: '8px 14px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 6,
      }}>
        <span style={{ fontWeight: 700, fontSize: '.92rem' }}>{label}</span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{
            background: 'rgba(207,185,145,.25)', color: '#CFB991',
            borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
          }}>
            {totalCredits} cr
          </span>
          {semGpa !== null && semGpa !== undefined && (
            <span style={{
              background: 'rgba(255,255,255,.18)', color: '#fff',
              borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
            }}>
              Sem {semGpa}
            </span>
          )}
          {cumGpa !== null && cumGpa !== undefined && (
            <span style={{
              background: 'rgba(207,185,145,.45)', color: '#fff',
              borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 700,
              letterSpacing: '.2px',
            }}>
              Cum {cumGpa}
            </span>
          )}
        </div>
      </div>

      {/* Course rows */}
      <div style={{ padding: '4px 0' }}>
        {courses.length === 0 && (
          <div style={{
            padding: '18px 14px', color: '#d1d5db',
            textAlign: 'center', fontSize: '.78rem', userSelect: 'none',
          }}>
            No courses — drag here or add from Catalog
          </div>
        )}

        {courses.map((pc) => (
          <div
            key={pc.id}
            draggable
            onDragStart={(e) => {
              const ghost = document.createElement('div')
              ghost.textContent = pc.course.course_number
              ghost.style.cssText =
                'position:fixed;top:-999px;padding:4px 10px;background:#000;color:#CFB991;' +
                'font-family:monospace;font-size:13px;border-radius:6px;pointer-events:none'
              document.body.appendChild(ghost)
              e.dataTransfer.setDragImage(ghost, 0, 0)
              setTimeout(() => document.body.removeChild(ghost), 0)
              onDragStart(pc)
            }}
            style={{
              padding: '6px 10px 6px 0',
              display: 'flex', alignItems: 'center', gap: 6,
              borderBottom: '1px solid #f3f4f6',
              borderLeft: `3px solid ${STATUS_COLOR[pc.status] || '#d1d5db'}`,
              cursor: 'grab',
              transition: 'background .1s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#f9fafb' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '' }}
          >
            {/* Drag grip */}
            <span style={{
              color: '#d1d5db', fontSize: '1rem', lineHeight: 1,
              flexShrink: 0, userSelect: 'none', paddingLeft: 6,
            }} title="Drag to move">
              ⠿
            </span>

            {/* Course info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', gap: 5, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span
                  className="mono course-link"
                  style={{ fontSize: '.75rem', color: 'var(--blue)', fontWeight: 700 }}
                  onClick={() => onViewDetails(pc.course)}
                >
                  {pc.course.course_number}
                </span>
                <span style={{
                  fontSize: '.65rem', fontWeight: 600, padding: '0 6px',
                  borderRadius: 10, whiteSpace: 'nowrap',
                  background: `${STATUS_COLOR[pc.status]}22`,
                  color: STATUS_COLOR[pc.status],
                }}>
                  {STATUS_LABEL[pc.status] || pc.status}
                </span>
              </div>
              <div
                className="course-link"
                style={{ fontSize: '.8rem', fontWeight: 500, lineHeight: 1.3 }}
                onClick={() => onViewDetails(pc.course)}
              >
                {pc.course.title}
              </div>
              <div style={{ fontSize: '.7rem', color: 'var(--muted)', marginTop: 1 }}>
                {pc.course.credits} cr · {pc.course.department}
                {pc.grade && (
                  <span style={{ marginLeft: 8, fontWeight: 700, color: '#374151' }}>
                    {pc.grade}
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 3, flexShrink: 0, paddingRight: 8 }}>
              <button
                title="Cycle status (planned → in progress → completed)"
                onClick={(e) => { e.stopPropagation(); onToggle(pc) }}
                style={{
                  background: 'none', border: '1px solid #e5e7eb',
                  cursor: 'pointer', color: '#6b7280',
                  fontSize: '.78rem', padding: '2px 7px', borderRadius: 4,
                  transition: 'all .12s', lineHeight: 1,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#f3f4f6'
                  e.currentTarget.style.borderColor = '#9ca3af'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = ''
                  e.currentTarget.style.borderColor = '#e5e7eb'
                }}
              >
                ↻
              </button>
              <button
                title="Remove from plan"
                onClick={(e) => { e.stopPropagation(); onRemove(pc) }}
                style={{
                  background: 'none', border: 'none',
                  cursor: 'pointer', color: '#d1d5db',
                  fontSize: '1rem', padding: '0 3px', borderRadius: 4,
                  transition: 'color .12s', lineHeight: 1,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#d1d5db' }}
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Transfer Credits card ─────────────────────────────────────────────────────
function TransferCreditsCard({
  courses, planId, onReload,
  isDragOver, onDragOver, onDrop, onDragLeave, onDragStart,
}) {
  const [query,     setQuery]     = useState('')
  const [results,   setResults]   = useState([])
  const [searching, setSearching] = useState(false)
  const [adding,    setAdding]    = useState(null)

  // Debounced course search
  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    const timer = setTimeout(async () => {
      setSearching(true)
      try {
        const data = await getCourses(query)
        // Filter out courses already added as transfer credits
        const existing = new Set(courses.map((pc) => pc.course.id))
        setResults(data.filter((c) => !existing.has(c.id)).slice(0, 8))
      } catch { /* ignore */ }
      finally { setSearching(false) }
    }, 300)
    return () => clearTimeout(timer)
  }, [query, courses])

  async function handleAdd(course) {
    setAdding(course.id)
    setResults([])
    setQuery('')
    try {
      const newPc = await addCourseToPlan(planId, { course_id: course.id, year: 0, semester: 0 })
      // Mark as completed immediately — transfer credits are already earned
      if (newPc?.id) await updatePlanCourse(newPc.id, { status: 'completed' })
      onReload()
    } catch (err) {
      alert('Failed to add course: ' + err.message)
    } finally {
      setAdding(null)
    }
  }

  async function handleRemove(pc) {
    if (!window.confirm(`Remove ${pc.course.course_number} from transfer credits?`)) return
    await removePlanCourse(pc.id)
    onReload()
  }

  const totalCredits = courses.reduce((s, pc) => s + pc.course.credits, 0)

  return (
    <div style={{ marginBottom: 28 }}>
      {/* Section label */}
      <div style={{
        fontSize: '.78rem', fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '1px', color: 'var(--muted)', marginBottom: 8,
      }}>
        Transfer Credits
      </div>

      <div
        onDragOver={onDragOver}
        onDrop={onDrop}
        onDragLeave={onDragLeave}
        style={{
          border: isDragOver ? '2px dashed #92400e' : '1px solid var(--border)',
          borderRadius: 10,
          overflow: 'visible',
          background: isDragOver ? '#fffbf5' : '#fff',
          transition: 'border .12s, background .12s',
        }}
      >
        {/* Card header */}
        <div style={{
          background: '#92400e', color: '#fff',
          padding: '8px 14px', borderRadius: '10px 10px 0 0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 6,
        }}>
          <span style={{ fontWeight: 700, fontSize: '.92rem' }}>Transfer Credits</span>
          <span style={{
            background: 'rgba(255,255,255,.2)', color: '#fff',
            borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
          }}>
            {totalCredits} cr
          </span>
        </div>

        {/* Course rows */}
        <div style={{ padding: '4px 0' }}>
          {courses.length === 0 && (
            <div style={{
              padding: '14px', color: '#d1d5db',
              textAlign: 'center', fontSize: '.78rem', userSelect: 'none',
            }}>
              No transfer credits — drag a course here or search below
            </div>
          )}
          {courses.map((pc) => (
            <div
              key={pc.id}
              draggable
              onDragStart={(e) => {
                const ghost = document.createElement('div')
                ghost.textContent = pc.course.course_number
                ghost.style.cssText =
                  'position:fixed;top:-999px;padding:4px 10px;background:#92400e;color:#fff;' +
                  'font-family:monospace;font-size:13px;border-radius:6px;pointer-events:none'
                document.body.appendChild(ghost)
                e.dataTransfer.setDragImage(ghost, 0, 0)
                setTimeout(() => document.body.removeChild(ghost), 0)
                onDragStart(pc)
              }}
              style={{
                padding: '6px 10px 6px 0',
                display: 'flex', alignItems: 'center', gap: 6,
                borderBottom: '1px solid #f3f4f6',
                borderLeft: '3px solid #22c55e',
                cursor: 'grab',
                transition: 'background .1s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = '#f9fafb' }}
              onMouseLeave={(e) => { e.currentTarget.style.background = '' }}
            >
              {/* Drag grip */}
              <span style={{
                color: '#d1d5db', fontSize: '1rem', lineHeight: 1,
                flexShrink: 0, userSelect: 'none', paddingLeft: 6,
              }} title="Drag to move">⠿</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', gap: 5, alignItems: 'baseline', flexWrap: 'wrap' }}>
                  <span className="mono" style={{ fontSize: '.75rem', color: 'var(--blue)', fontWeight: 700 }}>
                    {pc.course.course_number}
                  </span>
                  <span style={{
                    fontSize: '.65rem', fontWeight: 600, padding: '0 6px',
                    borderRadius: 10, background: '#dcfce7', color: '#16a34a',
                  }}>
                    Transfer
                  </span>
                </div>
                <div style={{ fontSize: '.8rem', fontWeight: 500, lineHeight: 1.3 }}>
                  {pc.course.title}
                </div>
                <div style={{ fontSize: '.7rem', color: 'var(--muted)', marginTop: 1 }}>
                  {pc.course.credits} cr · {pc.course.department}
                  {pc.grade && (
                    <span style={{ marginLeft: 8, fontWeight: 700, color: '#374151' }}>{pc.grade}</span>
                  )}
                </div>
              </div>
              <button
                title="Remove from transfer credits"
                onClick={() => handleRemove(pc)}
                style={{
                  background: 'none', border: 'none',
                  cursor: 'pointer', color: '#d1d5db',
                  fontSize: '1rem', padding: '0 3px', borderRadius: 4,
                  lineHeight: 1, flexShrink: 0, paddingRight: 8,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#d1d5db' }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Search / add */}
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f3f4f6', position: 'relative' }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search courses to add (e.g. CS 18000, Calculus)…"
            style={{
              width: '100%', padding: '6px 10px', borderRadius: 6,
              border: '1px solid #e5e7eb', fontSize: '.82rem', boxSizing: 'border-box',
            }}
          />
          {searching && (
            <div style={{ fontSize: '.72rem', color: 'var(--muted)', marginTop: 4 }}>Searching…</div>
          )}
          {adding && (
            <div style={{ fontSize: '.72rem', color: 'var(--muted)', marginTop: 4 }}>Adding…</div>
          )}

          {/* Results dropdown */}
          {results.length > 0 && (
            <div style={{
              position: 'absolute', left: 14, right: 14, zIndex: 200,
              background: '#fff', border: '1px solid #e5e7eb',
              borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,.10)',
              maxHeight: 260, overflowY: 'auto',
            }}>
              {results.map((course) => (
                <div
                  key={course.id}
                  onClick={() => !adding && handleAdd(course)}
                  style={{
                    padding: '8px 12px', cursor: 'pointer',
                    borderBottom: '1px solid #f3f4f6',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = '#f9fafb' }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = '' }}
                >
                  <div style={{ minWidth: 0 }}>
                    <span className="mono" style={{ fontSize: '.78rem', fontWeight: 700, color: 'var(--blue)' }}>
                      {course.course_number}
                    </span>
                    <span style={{ fontSize: '.8rem', marginLeft: 8 }}>{course.title}</span>
                  </div>
                  <span style={{ fontSize: '.72rem', color: 'var(--muted)', flexShrink: 0, marginLeft: 8 }}>
                    {course.credits} cr
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function MyPlan() {
  const { currentPlanId, currentPlan } = usePlan()
  const [planCourses, setPlanCourses]   = useState([])
  const [loading, setLoading]           = useState(true)
  const [pendingGrade, setPendingGrade]     = useState(null)
  const [drawerCourse, setDrawerCourse]     = useState(null)
  const [pdfDownloading, setPdfDownloading] = useState(false)
  const [shareWorking,   setShareWorking]   = useState(false)
  const [shareUrl,       setShareUrl]       = useState(null)

  // Drag-and-drop
  const dragRef                       = useRef(null)   // stores the pc being dragged
  const [dragOverKey, setDragOverKey] = useState(null) // "year-semester"

  const reload = useCallback(() => {
    if (!currentPlanId) { setPlanCourses([]); setLoading(false); return }
    setLoading(true)
    getPlanCourses(currentPlanId)
      .then(setPlanCourses)
      .finally(() => setLoading(false))
  }, [currentPlanId])

  useEffect(() => { reload() }, [reload])

  // ── Status toggle ─────────────────────────────────────────────────────────
  async function handleToggle(pc) {
    const idx  = STATUSES.indexOf(pc.status)
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

  async function handleDownloadPdf() {
    setPdfDownloading(true)
    try {
      const blob = await downloadPlanPdf(currentPlanId)
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `${(currentPlan?.name || 'plan').replace(/\s+/g, '_')}_course_plan.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('Failed to generate PDF: ' + err.message)
    } finally {
      setPdfDownloading(false)
    }
  }

  async function handleCopyShareLink() {
    setShareWorking(true)
    try {
      let token = currentPlan?.share_token
      if (!token) {
        const data = await createShareLink(currentPlanId)
        token = data.share_token
      }
      setShareUrl(`${window.location.origin}/shared/${token}`)
    } catch (err) {
      alert('Could not generate link: ' + err.message)
    } finally {
      setShareWorking(false)
    }
  }

  // ── Drag-and-drop ─────────────────────────────────────────────────────────
  function handleDragStart(pc) {
    dragRef.current = pc
  }

  function handleDragOver(e, year, semester) {
    e.preventDefault()
    const key = `${year}-${semester}`
    if (dragOverKey !== key) setDragOverKey(key)
  }

  function handleDragLeave(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragOverKey(null)
  }

  async function handleDrop(e, toYear, toSemester) {
    e.preventDefault()
    setDragOverKey(null)
    const pc = dragRef.current
    dragRef.current = null
    if (!pc) return

    const relYear = toRelYear(pc.year, currentPlan)
    if (relYear === toYear && pc.semester === toSemester) return

    // Auto-update status when moving to/from the transfer card
    const intoTransfer = toYear === 0 && toSemester === 0
    const outOfTransfer = pc.year === 0 && pc.semester === 0
    const newStatus = intoTransfer ? 'completed' : outOfTransfer ? 'planned' : undefined

    // Optimistic update — move immediately in local state
    setPlanCourses((prev) =>
      prev.map((p) =>
        p.id === pc.id
          ? { ...p, year: toYear, semester: toSemester, ...(newStatus ? { status: newStatus, grade: outOfTransfer ? null : p.grade } : {}) }
          : p
      )
    )
    // Persist to backend
    try {
      await updatePlanCourse(pc.id, {
        year: toYear,
        semester: toSemester,
        ...(newStatus ? { status: newStatus, ...(outOfTransfer ? { grade: null } : {}) } : {}),
      })
    } catch {
      reload()  // revert on failure
    }
  }

  // ── Guard ─────────────────────────────────────────────────────────────────
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

  // ── Derived values ────────────────────────────────────────────────────────
  // Separate transfer credits (sentinel: year=0, semester=0) from regular plan
  const transferCourses = planCourses.filter((pc) => pc.year === 0 && pc.semester === 0)
  const mainCourses     = planCourses.filter((pc) => !(pc.year === 0 && pc.semester === 0))

  const transferCredits  = transferCourses.reduce((s, pc) => s + pc.course.credits, 0)
  const totalCredits     = planCourses.reduce((s, pc) => s + pc.course.credits, 0)
  const completedCredits = planCourses
    .filter((pc) => pc.status === 'completed')
    .reduce((s, pc) => s + pc.course.credits, 0)

  const duration   = currentPlan?.duration_years ?? 4
  const startYear  = currentPlan?.start_year ?? new Date().getFullYear()

  // Normalise all year values and build a lookup: "year-semester" → [pc, ...]
  // Only use mainCourses so transfer credits don't appear in the semester grid
  const slotMap = {}
  for (const pc of mainCourses) {
    const yr  = toRelYear(pc.year, currentPlan)
    const key = `${yr}-${pc.semester}`
    if (!slotMap[key]) slotMap[key] = []
    slotMap[key].push(pc)
  }

  // Determine which semesters to show:
  // Always show Fall (1) + Spring (2) for every year.
  // Show Summer (3) only in years where summer courses exist.
  const hasSummer = mainCourses.some((pc) => pc.semester === 3)
  const semesterTypes = hasSummer ? [1, 2, 3] : [1, 2]

  // ── GPA per semester ───────────────────────────────────────────────────────
  // Walk semesters chronologically, accumulating completed+graded courses to
  // produce both a per-semester GPA and a running cumulative GPA.
  const cumulativeAccum = []
  const semGpaMap  = {}   // "yr-sem" → semester GPA string | null
  const cumGpaMap  = {}   // "yr-sem" → cumulative GPA string | null

  for (let yr = 1; yr <= duration; yr++) {
    for (const sem of semesterTypes) {
      const key     = `${yr}-${sem}`
      const courses = slotMap[key] || []
      const semItems = courses
        .filter((pc) => pc.status === 'completed')
        .map((pc) => ({ credits: pc.course.credits, grade: pc.grade }))
      semGpaMap[key] = calcGPA(semItems)
      cumulativeAccum.push(...semItems)
      cumGpaMap[key] = calcGPA(cumulativeAccum)
    }
  }

  // Overall cumulative GPA (all completed courses)
  const overallGpa = calcGPA(
    planCourses
      .filter((pc) => pc.status === 'completed')
      .map((pc) => ({ credits: pc.course.credits, grade: pc.grade }))
  )

  // Semester label helper
  function semLabel(year, semester) {
    const calYear = startYear + (year - 1) + (semester === 2 ? 1 : 0)
    return `${TERM[semester]} ${calYear}`
  }

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <h1 className="page-title" style={{ margin: 0 }}>My Plan</h1>
        {planCourses.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            <button
              className="btn btn-outline"
              onClick={handleCopyShareLink}
              disabled={shareWorking}
              title="Copy read-only share link"
              style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#000' }}
            >
              {shareWorking ? <>Loading…</> : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                  </svg>
                  Share
                </>
              )}
            </button>
            <button
              className="btn btn-outline"
              onClick={handleDownloadPdf}
              disabled={pdfDownloading}
              title="Download course plan as PDF"
              style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#000' }}
            >
              {pdfDownloading ? <>Generating…</> : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  Download PDF
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Summary strip */}
      {currentPlan && (
        <div className="summary-strip">
          <div>
            <div className="label">Plan</div>
            <div className="value">{currentPlan.name}</div>
          </div>
          <div>
            <div className="label">
              {currentPlan.plan_type === 'double_major' ? 'Double Major'
                : currentPlan.plan_type === 'major_minor' ? 'Major + Minor'
                : 'Department'}
            </div>
            <div className="value">
              {currentPlan.plan_type === 'double_major' && currentPlan.secondary_department
                ? `${currentPlan.department} & ${currentPlan.secondary_department}`
                : currentPlan.plan_type === 'major_minor' && currentPlan.secondary_department
                ? `${currentPlan.department} + ${currentPlan.secondary_department}`
                : currentPlan.department}
            </div>
          </div>
          <div>
            <div className="label">Duration</div>
            <div className="value">
              {duration} yr ({startYear}–{startYear + duration - 1})
            </div>
          </div>
          {transferCredits > 0 && (
            <div>
              <div className="label">Transfer Credits</div>
              <div className="value" style={{ color: '#92400e' }}>{transferCredits}</div>
            </div>
          )}
          <div>
            <div className="label">Credits Planned</div>
            <div className="value">{totalCredits}</div>
          </div>
          <div>
            <div className="label">Credits Completed</div>
            <div className="value" style={{ color: 'var(--green)' }}>{completedCredits}</div>
          </div>
          {overallGpa !== null && (
            <div>
              <div className="label">Cumulative GPA</div>
              <div className="value" style={{ color: gpaColor(overallGpa) }}>{overallGpa}</div>
            </div>
          )}
        </div>
      )}

      {/* Status legend */}
      {!loading && planCourses.length > 0 && (
        <div style={{
          display: 'flex', gap: 14, alignItems: 'center',
          marginBottom: 14, fontSize: '.75rem', color: 'var(--muted)',
        }}>
          <span style={{ fontWeight: 600 }}>Status:</span>
          {Object.entries(STATUS_COLOR).map(([key, color]) => (
            <span key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{
                display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                background: color, flexShrink: 0,
              }} />
              {STATUS_LABEL[key]}
            </span>
          ))}
          <span style={{ marginLeft: 'auto', opacity: .7 }}>
            Drag ⠿ to move courses between semesters
          </span>
        </div>
      )}

      {/* Transfer Credits card — always visible when a plan is loaded */}
      {!loading && (
        <TransferCreditsCard
          courses={transferCourses}
          planId={currentPlanId}
          onReload={reload}
          isDragOver={dragOverKey === '0-0'}
          onDragOver={(e) => handleDragOver(e, 0, 0)}
          onDrop={(e) => handleDrop(e, 0, 0)}
          onDragLeave={handleDragLeave}
          onDragStart={handleDragStart}
        />
      )}

      {loading ? (
        <div className="loading">Loading plan…</div>
      ) : mainCourses.length === 0 ? (
        <div className="empty-state">
          <h3>No Courses in Plan</h3>
          <p>Go to <strong>Course Catalog</strong> to add courses to your plan.</p>
        </div>
      ) : (
        /* Year × Semester grid */
        Array.from({ length: duration }, (_, i) => i + 1).map((yr) => (
          <div key={yr} style={{ marginBottom: 24 }}>
            {/* Year header */}
            <div style={{
              fontSize: '.78rem', fontWeight: 700, textTransform: 'uppercase',
              letterSpacing: '1px', color: 'var(--muted)', marginBottom: 8,
            }}>
              Year {yr} · {startYear + yr - 1}–{startYear + yr}
            </div>

            {/* Semester cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: hasSummer ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)',
              gap: 12,
            }}>
              {semesterTypes.map((sem) => {
                const key     = `${yr}-${sem}`
                const courses = (slotMap[key] || []).sort((a, b) =>
                  a.course.course_number.localeCompare(b.course.course_number)
                )
                return (
                  <PlanSemesterCard
                    key={key}
                    label={semLabel(yr, sem)}
                    courses={courses}
                    semGpa={semGpaMap[key]}
                    cumGpa={cumGpaMap[key]}
                    onToggle={handleToggle}
                    onRemove={handleRemove}
                    onViewDetails={setDrawerCourse}
                    isDragOver={dragOverKey === key}
                    onDragOver={(e) => handleDragOver(e, yr, sem)}
                    onDrop={(e) => handleDrop(e, yr, sem)}
                    onDragLeave={handleDragLeave}
                    onDragStart={handleDragStart}
                  />
                )
              })}
            </div>
          </div>
        ))
      )}

      {shareUrl && (
        <ShareModal url={shareUrl} onClose={() => setShareUrl(null)} />
      )}

      {pendingGrade && (
        <GradeModal
          onConfirm={handleGradeConfirm}
          onCancel={() => setPendingGrade(null)}
        />
      )}

      {drawerCourse && (
        <CourseDetailDrawer
          course={drawerCourse}
          onClose={() => setDrawerCourse(null)}
        />
      )}
    </>
  )
}
