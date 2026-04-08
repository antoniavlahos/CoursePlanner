import { useState } from 'react'
import { useAuth } from '../App.jsx'
import { updateMe } from '../api.js'

export default function AccountSettings() {
  const { auth, setAuth } = useAuth()

  // ── Account form state ──────────────────────────────────────────────────────
  const [firstName, setFirstName]     = useState(auth?.user?.first_name ?? '')
  const [lastName,  setLastName]       = useState(auth?.user?.last_name  ?? '')
  const [accountSaving,  setAccountSaving]  = useState(false)
  const [accountError,   setAccountError]   = useState('')
  const [accountSuccess, setAccountSuccess] = useState(false)

  async function handleSaveAccount(e) {
    e.preventDefault()
    if (!firstName.trim() || !lastName.trim()) {
      setAccountError('First name and last name are required.')
      return
    }
    setAccountSaving(true)
    setAccountError('')
    setAccountSuccess(false)
    try {
      const updated = await updateMe(firstName.trim(), lastName.trim())
      setAuth((prev) => ({ ...prev, user: { ...prev.user, ...updated } }))
      setAccountSuccess(true)
      setTimeout(() => setAccountSuccess(false), 3000)
    } catch (err) {
      setAccountError(err.message)
    } finally {
      setAccountSaving(false)
    }
  }

  return (
    <>
      <h1 className="page-title">Account Settings</h1>

      {/* Account Information */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Account Information</div>
        <form onSubmit={handleSaveAccount}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label>First name</label>
              <input
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Jane"
                required
              />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Last name</label>
              <input
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Doe"
                required
              />
            </div>
          </div>
          <div className="form-group" style={{ margin: 0, marginBottom: 12 }}>
            <label>Email</label>
            <input value={auth?.user?.email ?? ''} disabled style={{ opacity: .6, cursor: 'not-allowed' }} />
          </div>
          {accountError   && <div className="error-msg" style={{ marginBottom: 8 }}>{accountError}</div>}
          {accountSuccess && (
            <div style={{ color: '#16a34a', fontSize: '.84rem', marginBottom: 8, fontWeight: 600 }}>
              ✓ Account updated successfully
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn btn-primary" disabled={accountSaving}>
              {accountSaving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}
