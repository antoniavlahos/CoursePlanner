import { useState, useEffect } from 'react'
import { usePlan } from '../App.jsx'
import { getAiStatus, getAiRecommendations, getPlanCourses, addCourseToPlan } from '../api.js'

export default function AiPlanner() {
  const { currentPlanId, currentPlan } = usePlan()
  const [aiAvailable, setAiAvailable] = useState(null)
  const [interests, setInterests] = useState('')
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [addedIds, setAddedIds] = useState(new Set())

  useEffect(() => {
    getAiStatus()
      .then((s) => setAiAvailable(s.available))
      .catch(() => setAiAvailable(false))
  }, [])

  async function handleRecommend() {
    if (!currentPlanId) { setError('No plan selected.'); return }
    setLoading(true)
    setError('')
    setRecommendations([])
    try {
      const pcs = await getPlanCourses(currentPlanId)
      const completed = pcs.filter((pc) => pc.status === 'completed').map((pc) => pc.course.course_number)
      const recs = await getAiRecommendations({
        interests,
        completed_courses: completed,
        department: currentPlan?.department ?? 'CS',
      })
      if (recs.length === 0) setError('No recommendations returned. Check that Ollama is running with a model loaded.')
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

  return (
    <>
      <h1 className="page-title">AI Course Planner</h1>

      {aiAvailable === false && (
        <div style={{ background: '#fde8e8', color: 'var(--red)', padding: '12px 16px', borderRadius: 8, marginBottom: 16 }}>
          <strong>⚠️ Ollama not detected.</strong> Start Ollama and load a model to use AI recommendations.
          <div style={{ fontSize: '.8rem', marginTop: 4 }}>Install: <code>brew install ollama</code> → <code>ollama serve</code> → <code>ollama pull llama3.2</code></div>
        </div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Get Course Recommendations</div>
        <div className="form-group">
          <label>Your interests and career goals</label>
          <textarea
            rows={4}
            value={interests}
            onChange={(e) => setInterests(e.target.value)}
            placeholder="e.g. I'm interested in machine learning and data science, want to work on AI applications…"
            style={{ resize: 'vertical' }}
          />
        </div>
        {error && <div className="error-msg">{error}</div>}
        <button
          className="btn btn-primary"
          onClick={handleRecommend}
          disabled={loading || aiAvailable === false}
        >
          {loading ? '⏳ Getting recommendations…' : '🤖 Get Recommendations'}
        </button>
      </div>

      {recommendations.length > 0 && (
        <div className="card">
          <div className="card-title">Recommended Courses</div>
          {recommendations.map(({ course, reason }) => (
            <div key={course.id} style={{ borderBottom: '1px solid var(--border)', padding: '12px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div className="mono" style={{ marginBottom: 2 }}>{course.course_number}</div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{course.title}</div>
                <div style={{ fontSize: '.8rem', color: 'var(--muted)' }}>{reason}</div>
                <div style={{ marginTop: 4, display: 'flex', gap: 6 }}>
                  <span className="meta-tag meta-credits">{course.credits} cr</span>
                  <span className="meta-tag meta-dept">{course.department}</span>
                </div>
              </div>
              <button
                className="btn btn-success btn-sm"
                disabled={addedIds.has(course.id)}
                onClick={() => handleAdd(course)}
              >
                {addedIds.has(course.id) ? '✓ Added' : 'Add to Plan'}
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
