import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { getSharedPlan, getSharedPlanCourses } from '../api.js'

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

function toRelYear(yearVal, plan) {
  if (!plan) return yearVal
  if (yearVal > plan.duration_years) {
    const rel = yearVal - plan.start_year + 1
    return Math.max(1, Math.min(plan.duration_years, rel))
  }
  return yearVal
}

// ── Read-only semester card ───────────────────────────────────────────────────
function ReadOnlySemesterCard({ label, courses }) {
  const totalCredits = courses.reduce((s, pc) => s + pc.course.credits, 0)
  return (
    <div style={{
      border: '1px solid var(--border, #e0e0e0)',
      borderRadius: 10, overflow: 'hidden', background: '#fff',
      minHeight: 80,
    }}>
      {/* Header */}
      <div style={{
        background: '#1a1a2e', color: '#fff',
        padding: '8px 14px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 6,
      }}>
        <span style={{ fontWeight: 700, fontSize: '.92rem' }}>{label}</span>
        <span style={{
          background: 'rgba(207,185,145,.25)', color: '#CFB991',
          borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
        }}>
          {totalCredits} cr
        </span>
      </div>

      {/* Course rows */}
      <div style={{ padding: '4px 0' }}>
        {courses.length === 0 && (
          <div style={{
            padding: '18px 14px', color: '#d1d5db',
            textAlign: 'center', fontSize: '.78rem',
          }}>
            No courses planned
          </div>
        )}
        {courses.map((pc) => (
          <div
            key={pc.id}
            style={{
              padding: '6px 14px 6px 0',
              display: 'flex', alignItems: 'center', gap: 6,
              borderBottom: '1px solid #f3f4f6',
              borderLeft: `3px solid ${STATUS_COLOR[pc.status] || '#d1d5db'}`,
            }}
          >
            <div style={{ flex: 1, minWidth: 0, paddingLeft: 10 }}>
              <div style={{ display: 'flex', gap: 5, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span style={{
                  fontFamily: 'monospace', fontSize: '.75rem',
                  color: '#000', fontWeight: 700,
                }}>
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
              <div style={{ fontSize: '.8rem', fontWeight: 500, lineHeight: 1.3 }}>
                {pc.course.title}
              </div>
              <div style={{ fontSize: '.7rem', color: '#6b7280', marginTop: 1 }}>
                {pc.course.credits} cr · {pc.course.department}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Read-only transfer credits card ──────────────────────────────────────────
function ReadOnlyTransferCard({ courses }) {
  const totalCredits = courses.reduce((s, pc) => s + pc.course.credits, 0)
  if (courses.length === 0) return null
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{
        fontSize: '.78rem', fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '1px', color: '#6b7280', marginBottom: 8,
      }}>
        Transfer Credits
      </div>
      <div style={{ border: '1px solid #e0e0e0', borderRadius: 10, overflow: 'hidden', background: '#fff' }}>
        <div style={{
          background: '#92400e', color: '#fff',
          padding: '8px 14px', borderRadius: '10px 10px 0 0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontWeight: 700, fontSize: '.92rem' }}>Transfer Credits</span>
          <span style={{
            background: 'rgba(255,255,255,.2)', color: '#fff',
            borderRadius: 20, padding: '1px 9px', fontSize: '.75rem', fontWeight: 600,
          }}>
            {totalCredits} cr
          </span>
        </div>
        <div style={{ padding: '4px 0' }}>
          {courses.map((pc) => (
            <div key={pc.id} style={{
              padding: '6px 14px 6px 0',
              display: 'flex', alignItems: 'center',
              borderBottom: '1px solid #f3f4f6',
              borderLeft: '3px solid #22c55e',
            }}>
              <div style={{ flex: 1, minWidth: 0, paddingLeft: 10 }}>
                <div style={{ display: 'flex', gap: 5, alignItems: 'baseline', flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '.75rem', color: '#000', fontWeight: 700 }}>
                    {pc.course.course_number}
                  </span>
                  <span style={{
                    fontSize: '.65rem', fontWeight: 600, padding: '0 6px',
                    borderRadius: 10, background: '#dcfce7', color: '#16a34a',
                  }}>
                    Transfer
                  </span>
                </div>
                <div style={{ fontSize: '.8rem', fontWeight: 500, lineHeight: 1.3 }}>{pc.course.title}</div>
                <div style={{ fontSize: '.7rem', color: '#6b7280', marginTop: 1 }}>
                  {pc.course.credits} cr · {pc.course.department}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SharedPlan() {
  const { token } = useParams()
  const [plan, setPlan]         = useState(null)
  const [courses, setCourses]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [p, cs] = await Promise.all([getSharedPlan(token), getSharedPlanCourses(token)])
        setPlan(p)
        setCourses(cs)
      } catch (err) {
        setError(err.message || 'This plan link is invalid or has been revoked.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#F0F2F5' }}>
        Loading shared plan…
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#F0F2F5', gap: 12 }}>
        <div style={{ fontSize: '2rem' }}>🔒</div>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', color: '#374151' }}>Plan not available</div>
        <div style={{ fontSize: '.9rem', color: '#6b7280' }}>{error}</div>
      </div>
    )
  }

  // ── Derived values ───────────────────────────────────────────────────────
  const duration  = plan.duration_years ?? 4
  const startYear = plan.start_year ?? new Date().getFullYear()

  const transferCourses = courses.filter((pc) => pc.year === 0 && pc.semester === 0)
  const mainCourses     = courses.filter((pc) => !(pc.year === 0 && pc.semester === 0))

  const transferCredits  = transferCourses.reduce((s, pc) => s + pc.course.credits, 0)
  const totalCredits     = courses.reduce((s, pc) => s + pc.course.credits, 0)
  const completedCredits = courses
    .filter((pc) => pc.status === 'completed')
    .reduce((s, pc) => s + pc.course.credits, 0)

  const slotMap = {}
  for (const pc of mainCourses) {
    const yr  = toRelYear(pc.year, plan)
    const key = `${yr}-${pc.semester}`
    if (!slotMap[key]) slotMap[key] = []
    slotMap[key].push(pc)
  }

  const hasSummer   = mainCourses.some((pc) => pc.semester === 3)
  const semTypes    = hasSummer ? [1, 2, 3] : [1, 2]

  function semLabel(year, semester) {
    const calYear = startYear + (year - 1) + (semester === 2 ? 1 : 0)
    return `${TERM[semester]} ${calYear}`
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F0F2F5' }}>
      {/* Read-only banner */}
      <div style={{
        background: '#1a1a2e', color: '#CFB991',
        padding: '10px 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <img src="/purdue-logo.svg" alt="Purdue" style={{ height: 28, opacity: .9 }} />
          <span style={{ fontWeight: 700, fontSize: '.95rem' }}>Course Planner</span>
        </div>
        <span style={{
          fontSize: '.78rem', background: 'rgba(207,185,145,.15)',
          border: '1px solid rgba(207,185,145,.3)',
          borderRadius: 20, padding: '3px 12px', fontWeight: 600,
        }}>
          👁 Read-only shared view
        </span>
      </div>

      <div style={{ maxWidth: 960, margin: '0 auto', padding: '28px 20px' }}>
        {/* Plan title row — left: name + subtitle  |  right: owner + email */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap', marginBottom: 18 }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontSize: '1.6rem', fontWeight: 800, color: '#1a1a2e' }}>
              {plan.name}
            </h1>
            <div style={{ fontSize: '.88rem', color: '#6b7280' }}>
              {plan.plan_type === 'double_major' && plan.secondary_department
                ? `${plan.department} & ${plan.secondary_department} (Double Major)`
                : plan.plan_type === 'major_minor' && plan.secondary_department
                ? `${plan.department} + ${plan.secondary_department} (Minor)`
                : plan.department
              } · {duration}-Year Plan · {startYear}–{startYear + duration - 1}
            </div>
          </div>
          {(plan.first_name || plan.last_name || plan.email) && (
            <div style={{ textAlign: 'right' }}>
              {(plan.first_name || plan.last_name) && (
                <div style={{ fontSize: '1.6rem', color: '#1a1a2e', fontWeight: 700 }}>
                  {[plan.first_name, plan.last_name].filter(Boolean).join(' ')}
                </div>
              )}
              {plan.email && (
                <div style={{ fontSize: '.82rem', color: '#6b7280', marginTop: 2 }}>
                  {plan.email}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Summary strip */}
        <div style={{
          background: '#fff', borderRadius: 8, padding: '12px 18px',
          display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap',
          boxShadow: '0 1px 3px rgba(0,0,0,.06)', marginBottom: 24,
        }}>
          {transferCredits > 0 && (
            <div>
              <div style={{ fontSize: '.75rem', color: '#6b7280' }}>Transfer Credits</div>
              <div style={{ fontWeight: 700, color: '#92400e', fontSize: '1rem' }}>{transferCredits}</div>
            </div>
          )}
          <div>
            <div style={{ fontSize: '.75rem', color: '#6b7280' }}>Credits Planned</div>
            <div style={{ fontWeight: 700, color: '#000', fontSize: '1rem' }}>{totalCredits}</div>
          </div>
          <div>
            <div style={{ fontSize: '.75rem', color: '#6b7280' }}>Credits Completed</div>
            <div style={{ fontWeight: 700, color: '#22c55e', fontSize: '1rem' }}>{completedCredits}</div>
          </div>
        </div>

        {/* Status legend */}
        {courses.length > 0 && (
          <div style={{
            display: 'flex', gap: 14, alignItems: 'center',
            marginBottom: 14, fontSize: '.75rem', color: '#6b7280',
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
          </div>
        )}

        {/* Transfer Credits */}
        <ReadOnlyTransferCard courses={transferCourses} />

        {/* Year × Semester grid */}
        {mainCourses.length === 0 && transferCourses.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#9ca3af' }}>
            No courses in this plan yet.
          </div>
        ) : (
          Array.from({ length: duration }, (_, i) => i + 1).map((yr) => (
            <div key={yr} style={{ marginBottom: 24 }}>
              <div style={{
                fontSize: '.78rem', fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: '1px', color: '#6b7280', marginBottom: 8,
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
                  const semCourses = (slotMap[key] || []).sort((a, b) =>
                    a.course.course_number.localeCompare(b.course.course_number)
                  )
                  return (
                    <ReadOnlySemesterCard
                      key={key}
                      label={semLabel(yr, sem)}
                      courses={semCourses}
                    />
                  )
                })}
              </div>
            </div>
          ))
        )}

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: 32, fontSize: '.75rem', color: '#9ca3af' }}>
          Shared via Purdue Course Planner · Read-only view
        </div>
      </div>
    </div>
  )
}
