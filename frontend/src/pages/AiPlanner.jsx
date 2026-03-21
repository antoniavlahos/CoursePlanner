import { useState, useEffect, useRef } from 'react'
import { usePlan } from '../App.jsx'
import {
  getAiStatus, getAiRecommendations, getAiProgramPlan,
  getPlanCourses, addCourseToPlan,
} from '../api.js'
import CourseDetailDrawer from '../components/CourseDetailDrawer.jsx'

const SEM_NAME = { 1: 'Fall', 2: 'Spring', 3: 'Summer' }

// ── Add-to-Plan modal (same as Catalog) ──────────────────────────────────────
function AddModal({ course, plan, onClose, onAdded }) {
  const [year, setYear] = useState(1)
  const [semester, setSemester] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const offeredTerms = course.terms_offered ?? []
  const notOffered = offeredTerms.length > 0 && !offeredTerms.includes(SEM_NAME[semester])

  async function handleAdd() {
    setLoading(true)
    setError('')
    try {
      await addCourseToPlan(plan.id, { course_id: course.id, semester, year })
      onAdded()
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
        <div className="modal-title">Add to Plan</div>

        <div style={{ background: '#f8f8f8', borderRadius: 8, padding: '10px 14px', marginBottom: 20 }}>
          <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '1rem', color: 'var(--blue)', marginBottom: 2 }}>
            {course.course_number}
          </div>
          <div style={{ fontWeight: 600, fontSize: '.92rem', marginBottom: 4 }}>{course.title}</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '.78rem', color: 'var(--muted)' }}>{course.credits} credits · {course.department}</span>
            {course.prerequisites?.length > 0 && (
              <span style={{ fontSize: '.75rem', background: '#fff3cd', color: '#856404', padding: '1px 8px', borderRadius: 12 }}>
                Prereqs: {course.prerequisites.join(', ')}
              </span>
            )}
          </div>
        </div>

        <div className="form-group">
          <label>Year</label>
          <div className="pill-group">
            {Array.from({ length: plan.duration_years }, (_, i) => i + 1).map((y) => (
              <label key={y}>
                <input type="radio" name="year" value={y} checked={year === y} onChange={() => setYear(y)} />
                Year {y}
                <span className="pill-sub">{plan.start_year + y - 1}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Semester</label>
          <div className="pill-group">
            {[[1, 'Fall', '🍂'], [2, 'Spring', '🌱'], [3, 'Summer', '☀️']].map(([val, name, icon]) => (
              <label key={val}>
                <input type="radio" name="sem" value={val} checked={semester === val} onChange={() => setSemester(val)} />
                {icon} {name}
              </label>
            ))}
          </div>
        </div>

        {notOffered && (
          <div style={{
            background: '#fffbea', color: '#92400e',
            border: '1px solid #fcd34d', borderRadius: 8,
            padding: '8px 12px', marginBottom: 8, fontSize: '.82rem',
          }}>
            ⚠️ <strong>{course.course_number}</strong> is typically offered in{' '}
            {offeredTerms.join(' & ')} only. You can still add it.
          </div>
        )}

        {error && <div className="error-msg">{error}</div>}

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-success" onClick={handleAdd} disabled={loading}>
            {loading ? 'Adding…' : '+ Add to Plan'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Type badge colours ────────────────────────────────────────────────────────
const TYPE_BADGE = {
  required:   { bg: '#1a1a1a', color: '#CFB991', label: 'Major Req'  },
  university: { bg: '#1e3a5f', color: '#93c5fd', label: 'Univ Req'   },
  prereq:     { bg: '#3b0764', color: '#d8b4fe', label: 'Prerequisite'},
  elective:   { bg: '#064e3b', color: '#6ee7b7', label: 'Elective'   },
}

function TypeBadge({ type }) {
  const t = TYPE_BADGE[type] || TYPE_BADGE.elective
  return (
    <span style={{
      display: 'inline-block', padding: '1px 8px', borderRadius: 12,
      fontSize: '.68rem', fontWeight: 700, letterSpacing: '.3px',
      background: t.bg, color: t.color,
    }}>
      {t.label}
    </span>
  )
}

// ── Semester card (supports drag-and-drop + delete) ──────────────────────────
function SemesterCard({
  sem, appliedSet, onViewDetails,
  isDragOver,
  onDragOver, onDrop, onDragLeave,
  onDragStart, onDelete,
}) {
  // Live credit total (recomputed from current courses after moves/deletes)
  const liveCredits = sem.courses.reduce((s, c) => s + c.credits, 0)

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
      }}>
        <span style={{ fontWeight: 700, fontSize: '.92rem' }}>{sem.label}</span>
        <span style={{
          background: 'rgba(207,185,145,.25)', color: '#CFB991',
          borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
        }}>
          {liveCredits} cr
        </span>
      </div>

      {/* Course rows */}
      <div style={{ padding: '4px 0' }}>
        {sem.courses.length === 0 && (
          <div style={{
            padding: '18px 14px', color: '#d1d5db',
            textAlign: 'center', fontSize: '.78rem', userSelect: 'none',
          }}>
            Drop courses here
          </div>
        )}

        {sem.courses.map((course) => (
          <div
            key={course.id}
            draggable
            onDragStart={(e) => {
              // Custom ghost: show course number only
              const ghost = document.createElement('div')
              ghost.textContent = course.course_number
              ghost.style.cssText =
                'position:fixed;top:-999px;padding:4px 10px;background:#000;color:#CFB991;' +
                'font-family:monospace;font-size:13px;border-radius:6px;pointer-events:none'
              document.body.appendChild(ghost)
              e.dataTransfer.setDragImage(ghost, 0, 0)
              setTimeout(() => document.body.removeChild(ghost), 0)
              onDragStart(course, sem.year, sem.semester)
            }}
            style={{
              padding: '6px 10px 6px 6px',
              display: 'flex', alignItems: 'center', gap: 6,
              opacity: appliedSet.has(course.id) ? 0.45 : 1,
              borderBottom: '1px solid #f3f4f6',
              cursor: 'grab',
              transition: 'background .1s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#f9fafb' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '' }}
          >
            {/* Drag grip */}
            <span style={{
              color: '#d1d5db', fontSize: '1rem', lineHeight: 1,
              flexShrink: 0, userSelect: 'none', paddingLeft: 4,
            }} title="Drag to move">
              ⠿
            </span>

            {/* Course info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', gap: 5, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span
                  className="mono course-link"
                  style={{ fontSize: '.75rem', color: 'var(--blue)', fontWeight: 700 }}
                  onClick={() => onViewDetails(course)}
                >
                  {course.course_number}
                </span>
                <TypeBadge type={course.type} />
              </div>
              <div
                className="course-link"
                style={{ fontSize: '.8rem', fontWeight: 500, lineHeight: 1.3 }}
                onClick={() => onViewDetails(course)}
              >
                {course.title}
              </div>
              <div style={{ fontSize: '.7rem', color: 'var(--muted)' }}>
                {course.credits} cr
                {appliedSet.has(course.id) && (
                  <span style={{ color: 'var(--green)', fontWeight: 600, marginLeft: 6 }}>✓ applied</span>
                )}
              </div>
              {course.type === 'elective' && course.reason && (
                <div style={{
                  fontSize: '.69rem', color: '#9ca3af',
                  fontStyle: 'italic', lineHeight: 1.3, marginTop: 2,
                }}>
                  {course.reason}
                </div>
              )}
            </div>

            {/* Delete button */}
            <button
              title="Remove from plan"
              onClick={(e) => { e.stopPropagation(); onDelete(course.id, sem.year, sem.semester) }}
              style={{
                flexShrink: 0, background: 'none', border: 'none',
                cursor: 'pointer', color: '#d1d5db', fontSize: '1rem',
                lineHeight: 1, padding: '0 2px', borderRadius: 4,
                transition: 'color .12s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = '#d1d5db' }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function AiPlanner() {
  const { currentPlanId, currentPlan } = usePlan()

  // Course search state
  const [aiAvailable, setAiAvailable]         = useState(null)
  const [interests, setInterests]             = useState('')
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading]                 = useState(false)
  const [error, setError]                     = useState('')
  const [addedIds, setAddedIds]               = useState(new Set())
  const [aiRanked, setAiRanked]               = useState(null)

  // Program plan state
  const [planLoading, setPlanLoading]   = useState(false)
  const [planError, setPlanError]       = useState('')
  const [programPlan, setProgramPlan]   = useState(null)   // { semesters, unscheduled, ... }
  const [appliedSet, setAppliedSet]     = useState(new Set())
  const [applying, setApplying]         = useState(false)
  const [maxCredits, setMaxCredits]     = useState(15)

  // Drawer
  const [drawerCourse, setDrawerCourse] = useState(null)

  // Add-to-plan modal
  const [addModalCourse, setAddModalCourse] = useState(null)

  // Active tab: 'search' | 'plan'
  const [activeTab, setActiveTab] = useState('search')

  // Drag-and-drop state (ref = no re-render during drag)
  const dragRef     = useRef({ courseId: null, fromYear: null, fromSemester: null })
  const [dragOverKey, setDragOverKey] = useState(null)   // "year-semester" of hovered drop target

  useEffect(() => {
    getAiStatus()
      .then((s) => setAiAvailable(s.available))
      .catch(() => setAiAvailable(false))
  }, [])

  // ── Course search ───────────────────────────────────────────────────────────
  async function handleRecommend() {
    if (!currentPlanId) { setError('No plan selected.'); return }
    if (!interests.trim()) { setError('Please describe what you are looking for.'); return }
    setLoading(true); setError(''); setRecommendations([]); setAiRanked(null)
    try {
      const pcs = await getPlanCourses(currentPlanId)
      const completed = pcs.filter((pc) => pc.status === 'completed').map((pc) => pc.course.course_number)
      const recs = await getAiRecommendations({
        interests,
        completed_courses: completed,
        department: currentPlan?.department ?? 'CS',
      })
      if (recs.length === 0)
        setError('No matching courses found. Try different keywords or a more specific description.')
      else
        setAiRanked(recs[0]?.ai_ranked ?? false)
      setRecommendations(recs)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd(course) {
    if (!currentPlanId) return
    await addCourseToPlan(currentPlanId, { course_id: course.id, semester: 1, year: 1 })
    setAddedIds((prev) => new Set([...prev, course.id]))
  }

  // ── Program plan ────────────────────────────────────────────────────────────
  async function handleGeneratePlan() {
    if (!currentPlanId) { setPlanError('No plan selected.'); return }
    setPlanLoading(true); setPlanError(''); setProgramPlan(null); setAppliedSet(new Set())
    try {
      const pcs = await getPlanCourses(currentPlanId)
      const completed = pcs.filter((pc) => pc.status === 'completed').map((pc) => pc.course.course_number)
      const result = await getAiProgramPlan({
        interests,
        completed_courses: completed,
        department: currentPlan?.department ?? 'CS',
        duration_years: currentPlan?.duration_years ?? 4,
        start_year: currentPlan?.start_year ?? 2025,
        max_credits_per_semester: maxCredits,
      })
      if (!result.semesters?.length)
        setPlanError('Could not generate a plan — check that your department has requirements set up.')
      else
        setProgramPlan(result)
    } catch (e) {
      setPlanError(e.message)
    } finally {
      setPlanLoading(false)
    }
  }

  async function handleApplyPlan() {
    if (!programPlan || !currentPlanId) return
    setApplying(true)

    // Gather courses already in the plan so we don't duplicate
    const pcs       = await getPlanCourses(currentPlanId)
    const existingIds = new Set(pcs.map((pc) => pc.course.id))

    const toAdd = []
    for (const sem of programPlan.semesters) {
      for (const course of sem.courses) {
        if (!existingIds.has(course.id) && !appliedSet.has(course.id)) {
          toAdd.push({ course, year: sem.year, semester: sem.semester })
        }
      }
    }

    // Add in parallel (batches of 5 to avoid overwhelming the server)
    const BATCH = 5
    for (let i = 0; i < toAdd.length; i += BATCH) {
      await Promise.all(
        toAdd.slice(i, i + BATCH).map(({ course, year, semester }) =>
          addCourseToPlan(currentPlanId, {
            course_id: course.id,
            year,
            semester,
            semester_type: 'regular',
          }).then(() => setAppliedSet((prev) => new Set([...prev, course.id])))
        )
      )
    }
    setApplying(false)
  }

  // ── Drag-and-drop handlers ──────────────────────────────────────────────────
  function handleDragStart(course, year, semester) {
    dragRef.current = { courseId: course.id, fromYear: year, fromSemester: semester }
  }

  function handleDragOver(e, year, semester) {
    e.preventDefault()
    const key = `${year}-${semester}`
    if (dragOverKey !== key) setDragOverKey(key)
  }

  function handleDragLeave(e) {
    // Only clear when leaving the card entirely (not a child element)
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOverKey(null)
    }
  }

  function handleDrop(e, toYear, toSemester) {
    e.preventDefault()
    setDragOverKey(null)

    const { courseId, fromYear, fromSemester } = dragRef.current
    dragRef.current = { courseId: null, fromYear: null, fromSemester: null }

    if (!courseId || (fromYear === toYear && fromSemester === toSemester)) return

    setProgramPlan((prev) => {
      if (!prev) return prev
      // Find the course object in its source semester
      const sourceSem = prev.semesters.find(
        (s) => s.year === fromYear && s.semester === fromSemester
      )
      const course = sourceSem?.courses.find((c) => c.id === courseId)
      if (!course) return prev

      const newSemesters = prev.semesters.map((sem) => {
        if (sem.year === fromYear && sem.semester === fromSemester) {
          const courses = sem.courses.filter((c) => c.id !== courseId)
          return { ...sem, courses, credits: courses.reduce((s, c) => s + c.credits, 0) }
        }
        if (sem.year === toYear && sem.semester === toSemester) {
          const courses = [...sem.courses, course]
          return { ...sem, courses, credits: courses.reduce((s, c) => s + c.credits, 0) }
        }
        return sem
      })
      return { ...prev, semesters: newSemesters }
    })
  }

  function handleDeleteCourse(courseId, year, semester) {
    setProgramPlan((prev) => {
      if (!prev) return prev
      const newSemesters = prev.semesters.map((sem) => {
        if (sem.year === year && sem.semester === semester) {
          const courses = sem.courses.filter((c) => c.id !== courseId)
          return { ...sem, courses, credits: courses.reduce((s, c) => s + c.credits, 0) }
        }
        return sem
      })
      return { ...prev, semesters: newSemesters }
    })
  }

  // ── Guard: no plan ──────────────────────────────────────────────────────────
  if (!currentPlanId) {
    return (
      <>
        <h1 className="page-title">AI Planner</h1>
        <div className="empty-state">
          <h3>No Plan Selected</h3>
          <p>Create or load a plan in Settings first.</p>
        </div>
      </>
    )
  }

  // ── Compute totals for program plan header ──────────────────────────────────
  const totalApplied = appliedSet.size
  const totalCourses = programPlan
    ? programPlan.semesters.reduce((s, sem) => s + sem.courses.length, 0)
    : 0

  return (
    <>
      <h1 className="page-title">AI Course Planner</h1>

      {/* ── Tab bar ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '2px solid var(--border)' }}>
        {[
          { key: 'search', label: '🔍 Find Courses' },
          { key: 'plan',   label: '📋 Full Program Plan' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            style={{
              padding: '9px 20px', border: 'none', cursor: 'pointer',
              fontWeight: 600, fontSize: '.88rem',
              background: 'transparent',
              borderBottom: activeTab === key ? '2px solid var(--blue)' : '2px solid transparent',
              color: activeTab === key ? 'var(--blue)' : 'var(--muted)',
              marginBottom: -2,
              transition: 'color .15s, border-color .15s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/*  TAB: FIND COURSES                                                */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'search' && (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Find Courses</div>
            <p style={{ fontSize: '.85rem', color: 'var(--muted)', marginBottom: 12 }}>
              Describe what you want to study or build. The planner searches every course's
              title and description, then ranks the best matches.
            </p>
            <div className="form-group">
              <textarea
                rows={4}
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleRecommend() }}
                placeholder={
                  'Try: "machine learning and neural networks"\n' +
                  '"web development with React and APIs"\n' +
                  '"entrepreneurship and product design"\n' +
                  '"cybersecurity and ethical hacking"'
                }
                style={{ resize: 'vertical' }}
              />
            </div>

            {aiAvailable === false && (
              <div style={{
                background: '#fffbea', color: '#92400e',
                border: '1px solid #fcd34d', borderRadius: 8,
                padding: '10px 14px', marginBottom: 12, fontSize: '.82rem',
              }}>
                <strong>Ollama not detected</strong> — results will use keyword matching.
                {' '}To enable AI: <code>brew install ollama</code> → <code>ollama serve</code> → <code>ollama pull llama3.2</code>
              </div>
            )}

            {error && <div className="error-msg" style={{ marginBottom: 10 }}>{error}</div>}

            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button
                className="btn btn-primary"
                onClick={handleRecommend}
                disabled={loading || !interests.trim()}
              >
                {loading ? '⏳ Searching…' : '🔍 Find Courses'}
              </button>
              <span style={{ fontSize: '.75rem', color: 'var(--muted)' }}>
                {loading ? 'Scanning course catalog…' : 'Tip: Cmd+Enter to search'}
              </span>
            </div>
          </div>

          {recommendations.length > 0 && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div className="card-title" style={{ margin: 0 }}>
                  {recommendations.length} Course{recommendations.length !== 1 ? 's' : ''} Found
                </div>
                {aiRanked !== null && (
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 5,
                    fontSize: '.75rem', fontWeight: 600, padding: '3px 10px',
                    borderRadius: 20,
                    background: aiRanked ? '#f0f4ff' : '#f0fdf4',
                    color: aiRanked ? '#3730a3' : '#166534',
                    border: `1px solid ${aiRanked ? '#c7d2fe' : '#bbf7d0'}`,
                  }}>
                    {aiRanked ? '🤖 AI Ranked' : '🔍 Keyword Match'}
                  </span>
                )}
              </div>

              {recommendations.map(({ course, reason }) => (
                <div key={course.id} style={{
                  borderBottom: '1px solid var(--border)', padding: '14px 0',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 14,
                }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', marginBottom: 3 }}>
                      <span className="mono course-link" style={{ color: 'var(--blue)', fontWeight: 700 }}
                        onClick={() => setDrawerCourse(course)} title="View details">
                        {course.course_number}
                      </span>
                      <span className="course-link" style={{ fontWeight: 600 }}
                        onClick={() => setDrawerCourse(course)} title="View details">
                        {course.title}
                      </span>
                    </div>
                    {reason && (
                      <div style={{ fontSize: '.82rem', color: 'var(--muted)', marginBottom: 6, fontStyle: 'italic', lineHeight: 1.45 }}>
                        {reason}
                      </div>
                    )}
                    {course.description && (
                      <div style={{
                        fontSize: '.8rem', color: '#4b5563', marginBottom: 8, lineHeight: 1.5,
                        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                      }}>
                        {course.description}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span className="meta-tag meta-credits">{course.credits} cr</span>
                      <span className="meta-tag meta-dept">{course.department}</span>
                      {course.terms_offered?.length > 0 && (
                        <span className="meta-tag" style={{ background: '#f3f4f6', color: '#6b7280' }}>
                          {course.terms_offered.join(' · ')}
                        </span>
                      )}
                      <button className="btn btn-sm"
                        style={{ marginLeft: 2, padding: '2px 10px', fontSize: '.75rem' }}
                        onClick={() => setDrawerCourse(course)}>
                        Details
                      </button>
                    </div>
                  </div>
                  <button
                    className="btn btn-success btn-sm"
                    style={{ flexShrink: 0, marginTop: 2 }}
                    disabled={addedIds.has(course.id)}
                    onClick={() => setAddModalCourse(course)}
                  >
                    {addedIds.has(course.id) ? '✓ Added' : '+ Plan'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/*  TAB: FULL PROGRAM PLAN                                           */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'plan' && (
        <>
          {/* ── Options card ─────────────────────────────────────────── */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Generate Your Full Program Plan</div>
            <p style={{ fontSize: '.85rem', color: 'var(--muted)', marginBottom: 14 }}>
              Builds a complete semester-by-semester schedule that satisfies your department's
              required courses, university graduation requirements, and all prerequisites —
              automatically sorted so every course appears after its prerequisites.
              Describe your interests below to fill remaining credit slots with relevant electives.
            </p>

            <div className="form-group" style={{ marginBottom: 10 }}>
              <label>Interests for elective selection <span style={{ fontWeight: 400, color: 'var(--muted)' }}>(optional)</span></label>
              <textarea
                rows={2}
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                placeholder='e.g. "machine learning, robotics, systems programming"'
                style={{ resize: 'vertical' }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 14 }}>
              <label>Max credits per semester</label>
              <div className="pill-group" style={{ maxWidth: 360 }}>
                {[12, 15, 17, 19].map((cr) => (
                  <label key={cr}>
                    <input type="radio" name="maxcr" value={cr}
                      checked={maxCredits === cr}
                      onChange={() => setMaxCredits(cr)} />
                    {cr} cr
                  </label>
                ))}
              </div>
            </div>

            {planError && <div className="error-msg" style={{ marginBottom: 10 }}>{planError}</div>}

            <button
              className="btn btn-primary"
              onClick={handleGeneratePlan}
              disabled={planLoading}
            >
              {planLoading ? '⏳ Building plan…' : '📋 Generate Full Program Plan'}
            </button>
          </div>

          {/* ── Plan results ──────────────────────────────────────────── */}
          {programPlan && (
            <>
              {/* Summary bar */}
              <div className="card" style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  {[
                    { label: 'Semesters',      value: programPlan.semesters.length },
                    { label: 'Courses',         value: totalCourses },
                    { label: 'Planned Credits', value: programPlan.total_credits },
                    { label: 'Major Required',  value: programPlan.dept_required },
                    { label: 'Univ Required',   value: programPlan.univ_required },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <div style={{ fontSize: '.72rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.5px' }}>{label}</div>
                      <div style={{ fontWeight: 700, fontSize: '1.3rem', color: 'var(--blue)' }}>{value}</div>
                    </div>
                  ))}

                  <div style={{ marginLeft: 'auto', display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
                    {/* AI / keyword badge */}
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 5,
                      fontSize: '.75rem', fontWeight: 600, padding: '3px 10px',
                      borderRadius: 20,
                      background: programPlan.ai_ranked ? '#f0f4ff' : '#f0fdf4',
                      color:      programPlan.ai_ranked ? '#3730a3' : '#166534',
                      border:     `1px solid ${programPlan.ai_ranked ? '#c7d2fe' : '#bbf7d0'}`,
                    }}>
                      {programPlan.ai_ranked ? '🤖 AI Planned' : '🔍 Keyword Match'}
                    </span>
                    {/* Legend */}
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                      {Object.entries(TYPE_BADGE).map(([key, t]) => (
                        <span key={key} style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: 12,
                          fontSize: '.68rem', fontWeight: 700,
                          background: t.bg, color: t.color,
                        }}>
                          {t.label}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Apply button */}
                <div style={{ marginTop: 14, display: 'flex', gap: 12, alignItems: 'center' }}>
                  <button
                    className="btn btn-primary"
                    onClick={handleApplyPlan}
                    disabled={applying || totalApplied >= totalCourses}
                  >
                    {applying
                      ? '⏳ Applying…'
                      : totalApplied >= totalCourses
                        ? `✓ All ${totalCourses} Courses Applied`
                        : `Apply All ${totalCourses} Courses to My Plan`}
                  </button>
                  {totalApplied > 0 && totalApplied < totalCourses && (
                    <span style={{ fontSize: '.8rem', color: 'var(--muted)' }}>
                      {totalApplied} of {totalCourses} applied
                    </span>
                  )}
                </div>
              </div>

              {/* Semester grid — 2 columns per row (Fall | Spring) */}
              {Array.from({ length: currentPlan?.duration_years ?? 4 }, (_, i) => i + 1).map((yr) => {
                const yearSems = programPlan.semesters.filter((s) => s.year === yr)
                if (!yearSems.length) return null
                return (
                  <div key={yr} style={{ marginBottom: 20 }}>
                    <div style={{
                      fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '1px', color: 'var(--muted)', marginBottom: 8,
                    }}>
                      Year {yr}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                      {yearSems.map((sem) => (
                        <SemesterCard
                          key={`${sem.year}-${sem.semester}`}
                          sem={sem}
                          appliedSet={appliedSet}
                          onViewDetails={setDrawerCourse}
                          isDragOver={dragOverKey === `${sem.year}-${sem.semester}`}
                          onDragOver={(e) => handleDragOver(e, sem.year, sem.semester)}
                          onDrop={(e) => handleDrop(e, sem.year, sem.semester)}
                          onDragLeave={handleDragLeave}
                          onDragStart={handleDragStart}
                          onDelete={handleDeleteCourse}
                        />
                      ))}
                    </div>
                  </div>
                )
              })}

              {/* Unscheduled courses (overflow) */}
              {programPlan.unscheduled?.length > 0 && (
                <div className="card" style={{ marginTop: 8, borderLeft: '3px solid #f59e0b' }}>
                  <div className="card-title" style={{ color: '#92400e' }}>
                    ⚠️ {programPlan.unscheduled.length} Course{programPlan.unscheduled.length !== 1 ? 's' : ''} Couldn't Fit
                  </div>
                  <p style={{ fontSize: '.82rem', color: 'var(--muted)', marginBottom: 10 }}>
                    These courses have prerequisites that block earlier scheduling, or your plan duration
                    may need to be extended. You can add them manually from the Catalog.
                  </p>
                  {programPlan.unscheduled.map((course) => (
                    <div key={course.id} style={{ display: 'flex', gap: 8, alignItems: 'baseline', marginBottom: 4 }}>
                      <span className="mono" style={{ fontSize: '.8rem', color: 'var(--blue)' }}>{course.course_number}</span>
                      <span style={{ fontSize: '.82rem' }}>{course.title}</span>
                      <span style={{ fontSize: '.75rem', color: 'var(--muted)' }}>{course.credits} cr</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ── Add-to-plan modal ────────────────────────────────────────────── */}
      {addModalCourse && currentPlan && (
        <AddModal
          course={addModalCourse}
          plan={currentPlan}
          onClose={() => setAddModalCourse(null)}
          onAdded={() => setAddedIds((prev) => new Set([...prev, addModalCourse.id]))}
        />
      )}

      {/* ── Course detail drawer ─────────────────────────────────────────── */}
      {drawerCourse && (
        <CourseDetailDrawer
          course={drawerCourse}
          onClose={() => setDrawerCourse(null)}
          actions={
            activeTab === 'search'
              ? (
                <button
                  className="btn btn-primary"
                  disabled={addedIds.has(drawerCourse.id)}
                  onClick={() => { setDrawerCourse(null); setAddModalCourse(drawerCourse) }}
                >
                  {addedIds.has(drawerCourse.id) ? '✓ Already Added' : '+ Add to Plan'}
                </button>
              )
              : null
          }
        />
      )}
    </>
  )
}
