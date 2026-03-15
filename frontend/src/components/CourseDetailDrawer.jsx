import { useEffect } from 'react'

/**
 * Slide-in drawer showing full course details.
 *
 * Props:
 *   course   – course object (required)
 *   onClose  – called when the drawer should close
 *   actions  – optional JSX rendered in the footer (e.g. "Add to Plan" button)
 */
export default function CourseDetailDrawer({ course, onClose, actions }) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Prevent body scroll while drawer is open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const prereqs  = course.prerequisites  ?? []
  const coreqs   = course.corequisites   ?? []
  const terms    = course.terms_offered  ?? []
  const hasDesc  = course.description && course.description.trim().length > 0

  return (
    <>
      {/* Backdrop */}
      <div className="drawer-overlay" onClick={onClose} />

      {/* Panel */}
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`${course.course_number} details`}>

        {/* ── Header ── */}
        <div className="drawer-header">
          <button className="drawer-close" onClick={onClose} aria-label="Close">✕</button>
          <div className="drawer-course-num">{course.course_number}</div>
          <div className="drawer-course-title">{course.title}</div>
        </div>

        {/* ── Body ── */}
        <div className="drawer-body">

          {/* Badges row */}
          <div className="drawer-badges">
            <span className="meta-tag meta-credits">{course.credits} credit{course.credits !== 1 ? 's' : ''}</span>
            <span className="meta-tag meta-dept">{course.department}</span>
            {terms.map((t) => (
              <span key={t} className="chip chip-term">{t}</span>
            ))}
          </div>

          {/* Description */}
          <div className="drawer-section">
            <div className="drawer-section-title">Description</div>
            {hasDesc ? (
              <p className="drawer-desc">{course.description}</p>
            ) : (
              <p className="drawer-desc" style={{ color: 'var(--muted)', fontStyle: 'italic' }}>
                No description available.
              </p>
            )}
          </div>

          {/* Prerequisites */}
          {prereqs.length > 0 && (
            <div className="drawer-section">
              <div className="drawer-section-title">Prerequisites</div>
              <div className="drawer-chips">
                {prereqs.map((p) => (
                  <span key={p} className="chip chip-prereq">{p}</span>
                ))}
              </div>
            </div>
          )}

          {/* Corequisites */}
          {coreqs.length > 0 && (
            <div className="drawer-section">
              <div className="drawer-section-title">Corequisites</div>
              <div className="drawer-chips">
                {coreqs.map((c) => (
                  <span key={c} className="chip chip-coreq">{c}</span>
                ))}
              </div>
            </div>
          )}

          {/* Quick-reference table */}
          <div className="drawer-section">
            <div className="drawer-section-title">Details</div>
            <table style={{ fontSize: '.88rem', borderCollapse: 'collapse', width: '100%' }}>
              <tbody>
                {[
                  ['Department',   course.department],
                  ['Credits',      course.credits],
                  ['Terms Offered', terms.length > 0 ? terms.join(', ') : '—'],
                  ['Prerequisites', prereqs.length > 0 ? prereqs.join(', ') : 'None'],
                  ['Corequisites',  coreqs.length > 0 ? coreqs.join(', ') : 'None'],
                ].map(([label, value]) => (
                  <tr key={label} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '7px 0', fontWeight: 600, color: 'var(--muted)', width: 140, verticalAlign: 'top' }}>{label}</td>
                    <td style={{ padding: '7px 0 7px 12px', verticalAlign: 'top' }}>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>

        {/* ── Footer ── */}
        {actions && (
          <div className="drawer-footer">{actions}</div>
        )}

      </aside>
    </>
  )
}
