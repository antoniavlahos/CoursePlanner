import { useState, useEffect } from 'react'
import { usePlan } from '../App.jsx'
import { getPlanCourses, getDeptRequirements, getUniversityRequirements } from '../api.js'
import CourseDetailDrawer from '../components/CourseDetailDrawer.jsx'

const TERM = { 1: 'Fall', 2: 'Spring', 3: 'Summer' }

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

// ── Semester card ─────────────────────────────────────────────────────────────
function GpaSemesterCard({ label, semGpa, cumGpa, courses, onViewDetails }) {
  const totalCredits = courses.reduce((s, pc) => s + pc.course.credits, 0)

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: 10, overflow: 'hidden', background: '#fff',
    }}>
      {/* Header */}
      <div style={{
        background: 'var(--blue)', color: '#fff',
        padding: '8px 14px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 6,
      }}>
        <span style={{ fontWeight: 700, fontSize: '.92rem' }}>{label}</span>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Credits pill */}
          <span style={{
            background: 'rgba(207,185,145,.25)', color: '#CFB991',
            borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
          }}>
            {totalCredits} cr
          </span>

          {/* Semester GPA pill */}
          {semGpa !== null && (
            <span style={{
              background: 'rgba(255,255,255,.18)', color: '#fff',
              borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
            }}>
              Sem {semGpa}
            </span>
          )}

          {/* Cumulative GPA pill – highlighted in gold */}
          {cumGpa !== null && (
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
            textAlign: 'center', fontSize: '.78rem',
          }}>
            No courses
          </div>
        )}

        {courses.map((pc) => (
          <div key={pc.id} style={{
            padding: '6px 12px 6px 0',
            display: 'flex', alignItems: 'center',
            borderBottom: '1px solid #f3f4f6',
            borderLeft: `3px solid ${STATUS_COLOR[pc.status] || '#d1d5db'}`,
          }}>
            <div style={{ flex: 1, minWidth: 0, paddingLeft: 10 }}>
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
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function Requirements() {
  const { currentPlanId, currentPlan } = usePlan()
  const [planCourses, setPlanCourses] = useState([])
  const [deptReqs, setDeptReqs] = useState(null)
  const [univReqs, setUnivReqs] = useState([])
  const [loading, setLoading] = useState(true)
  const [drawerCourse, setDrawerCourse] = useState(null)

  useEffect(() => {
    if (!currentPlanId || !currentPlan) { setLoading(false); return }
    setLoading(true)
    Promise.all([
      getPlanCourses(currentPlanId),
      getDeptRequirements(currentPlan.department).catch(() => null),
      getUniversityRequirements(),
    ])
      .then(([pcs, dept, univ]) => {
        setPlanCourses(pcs)
        setDeptReqs(dept)
        setUnivReqs(univ)
      })
      .finally(() => setLoading(false))
  }, [currentPlanId, currentPlan])

  if (!currentPlanId) {
    return (
      <>
        <h1 className="page-title">Requirements</h1>
        <div className="empty-state">
          <h3>No Plan Selected</h3>
          <p>Create or load a plan in Settings.</p>
        </div>
      </>
    )
  }

  // ── Derived values ───────────────────────────────────────────────────────
  const completedPCs   = planCourses.filter((pc) => pc.status === 'completed')
  const completedNums  = new Set(completedPCs.map((pc) => pc.course.course_number))
  const completedCredits = completedPCs.reduce((s, pc) => s + pc.course.credits, 0)
  const totalRequired  = deptReqs?.required_credits ?? 120
  const progress       = Math.min(100, Math.round((completedCredits / totalRequired) * 100))

  // Overall cumulative GPA (all completed courses)
  const overallGpa = calcGPA(
    completedPCs.map((pc) => ({ credits: pc.course.credits, grade: pc.grade }))
  )

  // ── Semester grid data ───────────────────────────────────────────────────
  const duration  = currentPlan?.duration_years ?? 4
  const startYear = currentPlan?.start_year ?? new Date().getFullYear()

  // Group courses by "year-semester" key
  const slotMap = {}
  for (const pc of planCourses) {
    const key = `${pc.year}-${pc.semester}`
    if (!slotMap[key]) slotMap[key] = []
    slotMap[key].push(pc)
  }

  // Collect all year-semester combos that have courses, in chronological order
  const hasSummer = planCourses.some((pc) => pc.semester === 3)
  const semTypes  = hasSummer ? [1, 2, 3] : [1, 2]

  // Compute semester + cumulative GPA for each slot, walking in chronological order
  const cumulativeAccum = []   // grows as we visit semesters in order
  const semGpaMap  = {}        // key → semester GPA string | null
  const cumGpaMap  = {}        // key → cumulative GPA string | null

  for (let yr = 1; yr <= duration; yr++) {
    for (const sem of semTypes) {
      const key     = `${yr}-${sem}`
      const courses = slotMap[key] || []

      // Semester GPA: only courses completed this specific semester
      const semItems = courses
        .filter((pc) => pc.status === 'completed')
        .map((pc) => ({ credits: pc.course.credits, grade: pc.grade }))
      semGpaMap[key] = calcGPA(semItems)

      // Cumulative GPA: all completed courses up to and including this semester
      cumulativeAccum.push(...semItems)
      cumGpaMap[key] = calcGPA(cumulativeAccum)
    }
  }

  function semLabel(year, semester) {
    const calYear = startYear + (year - 1) + (semester === 2 ? 1 : 0)
    return `${TERM[semester]} ${calYear}`
  }

  return (
    <>
      <h1 className="page-title">Requirements</h1>

      {loading ? (
        <div className="loading">Loading…</div>
      ) : (
        <>
          {/* ── Graduation Progress ──────────────────────────────────────── */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Graduation Progress</div>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: '.75rem', color: 'var(--muted)' }}>Credits Completed</div>
                <div style={{ fontWeight: 700, fontSize: '1.4rem', color: 'var(--blue)' }}>{completedCredits}</div>
              </div>
              <div>
                <div style={{ fontSize: '.75rem', color: 'var(--muted)' }}>Credits Required</div>
                <div style={{ fontWeight: 700, fontSize: '1.4rem' }}>{totalRequired}</div>
              </div>
              <div>
                <div style={{ fontSize: '.75rem', color: 'var(--muted)' }}>Progress</div>
                <div style={{ fontWeight: 700, fontSize: '1.4rem', color: progress === 100 ? 'var(--green)' : 'var(--blue)' }}>{progress}%</div>
              </div>
              {overallGpa !== null && (
                <div>
                  <div style={{ fontSize: '.75rem', color: 'var(--muted)' }}>Cumulative GPA</div>
                  <div style={{ fontWeight: 700, fontSize: '1.4rem', color: gpaColor(overallGpa) }}>{overallGpa}</div>
                </div>
              )}
            </div>
            <div style={{ background: '#e9ecef', borderRadius: 6, height: 10, overflow: 'hidden' }}>
              <div style={{
                width: `${progress}%`, height: '100%',
                background: progress === 100 ? 'var(--green)' : 'var(--blue)',
                transition: 'width .4s',
              }} />
            </div>
          </div>

          {/* ── Semester GPA Overview ────────────────────────────────────── */}
          {planCourses.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{
                fontSize: '.78rem', fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '1px', color: 'var(--muted)', marginBottom: 10,
              }}>
                Semester Overview
              </div>

              {/* Legend */}
              <div style={{
                display: 'flex', gap: 14, alignItems: 'center',
                marginBottom: 10, fontSize: '.75rem', color: 'var(--muted)',
              }}>
                <span style={{ fontWeight: 600 }}>Status:</span>
                {Object.entries(STATUS_COLOR).map(([key, color]) => (
                  <span key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{
                      display: 'inline-block', width: 8, height: 8,
                      borderRadius: '50%', background: color, flexShrink: 0,
                    }} />
                    {STATUS_LABEL[key]}
                  </span>
                ))}
                <span style={{ marginLeft: 'auto', opacity: .7, fontStyle: 'italic' }}>
                  Sem = semester GPA · Cum = cumulative GPA
                </span>
              </div>

              {Array.from({ length: duration }, (_, i) => i + 1).map((yr) => {
                // Only render the year row if at least one semester has courses
                const yearHasCourses = semTypes.some(
                  (sem) => (slotMap[`${yr}-${sem}`] || []).length > 0
                )
                if (!yearHasCourses) return null

                return (
                  <div key={yr} style={{ marginBottom: 20 }}>
                    <div style={{
                      fontSize: '.78rem', fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '1px', color: 'var(--muted)', marginBottom: 8,
                    }}>
                      Year {yr} · {startYear + yr - 1}–{startYear + yr}
                    </div>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: hasSummer ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)',
                      gap: 12,
                    }}>
                      {semTypes.map((sem) => {
                        const key     = `${yr}-${sem}`
                        const courses = (slotMap[key] || []).sort((a, b) =>
                          a.course.course_number.localeCompare(b.course.course_number)
                        )
                        // Skip empty summer columns unless summer is used
                        if (!hasSummer && sem === 3) return null
                        // Skip slots with no courses unless it's a regular semester
                        if (courses.length === 0 && sem === 3) return null
                        return (
                          <GpaSemesterCard
                            key={key}
                            label={semLabel(yr, sem)}
                            semGpa={semGpaMap[key]}
                            cumGpa={cumGpaMap[key]}
                            courses={courses}
                            onViewDetails={setDrawerCourse}
                          />
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* ── Department Requirements ──────────────────────────────────── */}
          {deptReqs && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-title">
                {deptReqs.name} Required Courses
                <span style={{ fontWeight: 400, fontSize: '.8rem', marginLeft: 8, color: 'var(--muted)' }}>
                  ({deptReqs.required_courses.filter((c) => completedNums.has(c)).length}/{deptReqs.required_courses.length} completed)
                </span>
              </div>
              {deptReqs.required_courses.map((courseNum) => {
                const done = completedNums.has(courseNum)
                return (
                  <div key={courseNum} className="req-item">
                    <span className="req-icon">{done ? '✅' : '⭕'}</span>
                    <div>
                      <div className="req-name" style={{ color: done ? 'var(--green)' : 'var(--muted)' }}>
                        {courseNum}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* ── University Requirements ──────────────────────────────────── */}
          <div className="card">
            <div className="card-title">University Requirements</div>
            {univReqs.map((req) => {
              const met = req.courses_required.length > 0
                ? req.courses_required.some((c) => completedNums.has(c))
                : completedCredits >= req.credits_required
              return (
                <div key={req.id} className="req-item">
                  <span className="req-icon">{met ? '✅' : '⭕'}</span>
                  <div>
                    <div className="req-name" style={{ color: met ? 'var(--green)' : 'var(--text)' }}>
                      {req.name}
                      <span style={{
                        marginLeft: 8, fontSize: '.72rem',
                        background: '#e8edf7', color: 'var(--blue)',
                        padding: '1px 7px', borderRadius: 12,
                      }}>
                        {req.category}
                      </span>
                    </div>
                    <div className="req-desc">{req.description} · {req.credits_required} credits</div>
                  </div>
                </div>
              )
            })}
          </div>
        </>
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
