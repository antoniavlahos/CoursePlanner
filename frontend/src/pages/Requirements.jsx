import { useState, useEffect } from 'react'
import { usePlan } from '../App.jsx'
import { getPlanCourses, getDeptRequirements, getUniversityRequirements } from '../api.js'

export default function Requirements() {
  const { currentPlanId, currentPlan } = usePlan()
  const [planCourses, setPlanCourses] = useState([])
  const [deptReqs, setDeptReqs] = useState(null)
  const [univReqs, setUnivReqs] = useState([])
  const [loading, setLoading] = useState(true)

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

  const completedNums = new Set(
    planCourses.filter((pc) => pc.status === 'completed').map((pc) => pc.course.course_number)
  )
  const completedCredits = planCourses
    .filter((pc) => pc.status === 'completed')
    .reduce((s, pc) => s + pc.course.credits, 0)
  const totalRequired = deptReqs?.required_credits ?? 120
  const progress = Math.min(100, Math.round((completedCredits / totalRequired) * 100))

  return (
    <>
      <h1 className="page-title">Requirements</h1>

      {loading ? (
        <div className="loading">Loading…</div>
      ) : (
        <>
          {/* Progress bar */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Graduation Progress</div>
            <div style={{ display: 'flex', gap: 24, marginBottom: 12 }}>
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
            </div>
            <div style={{ background: '#e9ecef', borderRadius: 6, height: 10, overflow: 'hidden' }}>
              <div style={{ width: `${progress}%`, height: '100%', background: progress === 100 ? 'var(--green)' : 'var(--blue)', transition: 'width .4s' }} />
            </div>
          </div>

          {/* Department Requirements */}
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

          {/* University Requirements */}
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
                      <span style={{ marginLeft: 8, fontSize: '.72rem', background: '#e8edf7', color: 'var(--blue)', padding: '1px 7px', borderRadius: 12 }}>
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
    </>
  )
}
