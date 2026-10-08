import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../api/useApi.js'

export default function StudentDashboard() {
  const { user, logout } = useAuth()
  const call = useApi()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    call('/attendance/me').then(setData).catch((e) => setError(e.message))
  }, [call])

  return (
    <div className="shell">
      <header>
        <div>
          <h1>My attendance</h1>
          <p className="muted">{user.name}</p>
        </div>
        <button className="ghost" onClick={logout}>Sign out</button>
      </header>

      {error && <p className="error" role="alert">{error}</p>}
      {!data && !error && <p className="muted">Loading your attendance…</p>}

      {data && data.records.length === 0 && (
        <p className="muted">No attendance has been marked for you yet. It will show up here once a teacher marks it.</p>
      )}

      {data && data.records.length > 0 && (
        <>
          <section>
            <h2>By class</h2>
            <table>
              <thead>
                <tr><th>Class</th><th>Present</th><th>Absent</th><th>Attendance</th></tr>
              </thead>
              <tbody>
                {data.summary.map((c) => (
                  <tr key={c.classId}>
                    <td>{c.className}</td>
                    <td>{c.present}</td>
                    <td>{c.absent}</td>
                    <td>
                      <div className="meter" role="img" aria-label={`${c.percentage} percent`}>
                        <span className={c.low ? 'low' : ''} style={{ width: `${c.percentage}%` }} />
                      </div>
                      <strong className={c.low ? 'bad' : ''}>{c.percentage}%</strong>
                      {c.low && <span className="bad"> Below 75%</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2>Day by day</h2>
            <table>
              <thead>
                <tr><th>Date</th><th>Class</th><th>Status</th></tr>
              </thead>
              <tbody>
                {data.records.map((r) => (
                  <tr key={r.classId + r.date}>
                    <td>{r.date}</td>
                    <td>{r.className}</td>
                    <td className={r.status === 'present' ? 'good' : 'bad'}>
                      {r.status === 'present' ? 'Present' : 'Absent'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}
