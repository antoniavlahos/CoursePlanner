import { useState, useEffect, useCallback } from 'react'
import { usePlan } from '../App.jsx'
import { getCourses, getDepartments, addCourseToPlan } from '../api.js'
import CourseDetailDrawer from '../components/CourseDetailDrawer.jsx'

const TERMS = { 1: 'Fall', 2: 'Spring', 3: 'Summer' }

// ── Add-to-Plan modal ─────────────────────────────────────────────────────────
function AddModal({ course, plan, onClose, onAdded }) {
  const [year, setYear] = useState(1)
  const [semester, setSemester] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const offeredTerms = course.terms_offered ?? []
  const semName = TERMS[semester]
  const notOffered = offeredTerms.length > 0 && !offeredTerms.includes(semName)

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

        {/* Course info strip */}
        <div style={{ background: '#f8f8f8', borderRadius: 8, padding: '10px 14px', marginBottom: 20 }}>
          <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '1rem', color: 'var(--blue)', marginBottom: 2 }}>
            {course.course_number}
          </div>
          <div style={{ fontWeight: 600, fontSize: '.92rem', marginBottom: 4 }}>{course.title}</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '.78rem', color: 'var(--muted)' }}>{course.credits} credits · {course.department}</span>
            {course.prerequisites.length > 0 && (
              <span style={{ fontSize: '.75rem', background: '#fff3cd', color: '#856404', padding: '1px 8px', borderRadius: 12 }}>
                Prereqs: {course.prerequisites.join(', ')}
              </span>
            )}
          </div>
        </div>

        {/* Year picker */}
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

        {/* Semester picker */}
        <div className="form-group">
          <label>Semester</label>
          <div className="pill-group">
            {[[ 1, 'Fall', '🍂' ], [ 2, 'Spring', '🌱' ], [ 3, 'Summer', '☀️' ]].map(([val, name, icon]) => (
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

// ── Course card ───────────────────────────────────────────────────────────────
function CourseCard({ course, plan, onDetails, onAdd }) {
  return (
    <div className="course-card">
      <div style={{ flex: 1 }}>
        {/* Clickable course number + title open the detail drawer */}
        <div
          className="course-num course-link"
          onClick={() => onDetails(course)}
          title="View details"
        >
          {course.course_number}
        </div>
        <div
          className="course-title course-link"
          onClick={() => onDetails(course)}
          style={{ color: 'var(--text)' }}
        >
          {course.title}
        </div>
        <div className="course-desc">
          {course.description.length > 130
            ? course.description.slice(0, 130) + '…'
            : course.description}
        </div>
        <div className="course-meta">
          <span className="meta-tag meta-credits">{course.credits} cr</span>
          <span className="meta-tag meta-dept">{course.department}</span>
          <span className="meta-tag meta-terms">{course.terms_offered.join(', ')}</span>
          {course.prerequisites.length > 0 && (
            <span className="meta-tag meta-prereq">
              Prereqs: {course.prerequisites.slice(0, 3).join(', ')}{course.prerequisites.length > 3 ? '…' : ''}
            </span>
          )}
        </div>
      </div>

      {plan && (
        <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <button className="btn btn-success btn-sm" onClick={() => onAdd(course)}>
            Add to Plan
          </button>
          <button
            className="btn btn-sm"
            style={{ background: '#f0f0f0', color: 'var(--text)' }}
            onClick={() => onDetails(course)}
          >
            Details
          </button>
        </div>
      )}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function Catalog() {
  const { currentPlanId, currentPlan } = usePlan()
  const [courses, setCourses]       = useState([])
  const [departments, setDepartments] = useState([])
  const [query, setQuery]           = useState('')
  const [dept, setDept]             = useState('')
  const [loading, setLoading]       = useState(true)
  const [addedTick, setAddedTick]   = useState(0)

  // Detail drawer state
  const [drawerCourse, setDrawerCourse]   = useState(null)
  // Add-modal state (separate so drawer can stay open or close first)
  const [addModalCourse, setAddModalCourse] = useState(null)

  useEffect(() => { getDepartments().then(setDepartments) }, [])

  const search = useCallback(() => {
    setLoading(true)
    getCourses(query, dept)
      .then(setCourses)
      .finally(() => setLoading(false))
  }, [query, dept])

  useEffect(() => { search() }, [dept, addedTick])

  function handleKey(e) { if (e.key === 'Enter') search() }

  function openDetails(course) {
    setDrawerCourse(course)
  }

  function openAdd(course) {
    setDrawerCourse(null)   // close drawer first so modals don't stack
    setAddModalCourse(course)
  }

  return (
    <>
      <h1 className="page-title">Course Catalog</h1>

      <div className="search-bar">
        <input
          placeholder="Search by course number or title…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
        />
        <select value={dept} onChange={(e) => setDept(e.target.value)}>
          <option value="">All Departments</option>
          {departments.map((d) => (
            <option key={d.code} value={d.code}>{d.code} – {d.name}</option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={search} style={{ width: 90, flexShrink: 0 }}>
          Search
        </button>
      </div>

      {!currentPlanId && (
        <div style={{ background: '#fff8e1', color: '#856404', padding: '10px 14px', borderRadius: 8, marginBottom: 14, fontSize: '.85rem' }}>
          ⚠️ No plan selected. Create or load a plan in <strong>Settings</strong> to add courses.
        </div>
      )}

      {loading ? (
        <div className="loading">Loading courses…</div>
      ) : (
        <>
          <div style={{ fontSize: '.8rem', color: 'var(--muted)', marginBottom: 10 }}>
            {courses.length} course{courses.length !== 1 ? 's' : ''} found
            <span style={{ marginLeft: 8, opacity: .7 }}>— click a course name to see full details</span>
          </div>
          {courses.length === 0 ? (
            <div className="empty-state">
              <h3>No courses found</h3>
              <p>Try a different search term or department filter.</p>
            </div>
          ) : (
            courses.map((c) => (
              <CourseCard
                key={c.id}
                course={c}
                plan={currentPlan}
                onDetails={openDetails}
                onAdd={openAdd}
              />
            ))
          )}
        </>
      )}

      {/* Detail drawer */}
      {drawerCourse && (
        <CourseDetailDrawer
          course={drawerCourse}
          onClose={() => setDrawerCourse(null)}
          actions={currentPlan && (
            <button
              className="btn btn-success"
              onClick={() => openAdd(drawerCourse)}
            >
              + Add to Plan
            </button>
          )}
        />
      )}

      {/* Add-to-plan modal */}
      {addModalCourse && currentPlan && (
        <AddModal
          course={addModalCourse}
          plan={currentPlan}
          onClose={() => setAddModalCourse(null)}
          onAdded={() => setAddedTick((t) => t + 1)}
        />
      )}
    </>
  )
}
