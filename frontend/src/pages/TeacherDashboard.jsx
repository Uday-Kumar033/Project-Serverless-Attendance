import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../api/useApi.js'

const today = () => new Date().toLocaleDateString('en-CA') // YYYY-MM-DD in local time

export default function TeacherDashboard() {
  const { user, logout } = useAuth()
  const call = useApi()

  const [classes, setClasses] = useState([])
  const [classId, setClassId] = useState('')
  const [roster, setRoster] = useState([])
  const [date, setDate] = useState(today())
  const [marks, setMarks] = useState({}) // studentId -> 'present' | 'absent'
  const [newClass, setNewClass] = useState('')
  const [username, setUsername] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const fail = (e) => { setNotice(''); setError(e.message) }

  const loadClasses = useCallback(async () => {
    const { classes } = await call('/classes')
    setClasses(classes)
    return classes
  }, [call])

  useEffect(() => {
    loadClasses().then((list) => list[0] && setClassId(list[0].classId)).catch(fail)
  }, [loadClasses])

  const loadRoster = useCallback(async () => {
    if (!classId) return setRoster([])
    const { students } = await call(`/classes/${classId}/students`)
    setRoster(students)
  }, [call, classId])

  useEffect(() => { loadRoster().catch(fail) }, [loadRoster])

  // Pre-fill marks if attendance was already saved for this class and date.
  useEffect(() => {
    setMarks({})
    if (!classId || !date) return
    call(`/attendance?classId=${classId}&date=${date}`)
      .then(({ records }) => setMarks(Object.fromEntries(records.map((r) => [r.studentId, r.status]))))
      .catch(fail)
  }, [call, classId, date])

  async function createClass(e) {
    e.preventDefault()
    setError(''); setNotice('')
    try {
      const { class: created } = await call('/classes', { method: 'POST', body: { name: newClass } })
      setNewClass('')
      await loadClasses()
      setClassId(created.classId)
      setNotice(`Class "${created.name}" created. Add your students next.`)
    } catch (err) { fail(err) }
  }

  async function addStudent(e) {
    e.preventDefault()
    setError(''); setNotice('')
    try {
      const { student } = await call(`/classes/${classId}/students`, { method: 'POST', body: { username } })
      setUsername('')
      await Promise.all([loadRoster(), loadClasses()])
      setNotice(`${student.name} added to the class.`)
    } catch (err) { fail(err) }
  }

  async function save() {
    setError(''); setNotice(''); setSaving(true)
    try {
      const records = roster.map((s) => ({ studentId: s.userId, status: marks[s.userId] }))
      const res = await call('/attendance', { method: 'POST', body: { classId, date, records } })
      setNotice(res.message)
    } catch (err) { fail(err) }
    finally { setSaving(false) }
  }

  const markedCount = roster.filter((s) => marks[s.userId]).length
  const allMarked = roster.length > 0 && markedCount === roster.length
  const markAll = (status) => setMarks(Object.fromEntries(roster.map((s) => [s.userId, status])))

  return (
    <div className="shell">
      <header>
        <div>
          <h1>Class register</h1>
          <p className="muted">{user.name}</p>
        </div>
        <button className="ghost" onClick={logout}>Sign out</button>
      </header>

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}

      <section>
        <h2>Your classes</h2>
        <form className="inline" onSubmit={createClass}>
          <label>New class name
            <input value={newClass} onChange={(e) => setNewClass(e.target.value)} placeholder="Math 10A" required />
          </label>
          <button>Create class</button>
        </form>
        {classes.length === 0 && <p className="muted">You have no classes yet. Create your first one above.</p>}
        {classes.length > 0 && (
          <label>Class
            <select value={classId} onChange={(e) => setClassId(e.target.value)}>
              {classes.map((c) => (
                <option key={c.classId} value={c.classId}>{c.name} ({c.studentCount} students)</option>
              ))}
            </select>
          </label>
        )}
      </section>

      {classId && (
        <>
          <section>
            <h2>Add a student</h2>
            <form className="inline" onSubmit={addStudent}>
              <label>Student's username
                <input value={username} onChange={(e) => setUsername(e.target.value)} required />
              </label>
              <button>Add student</button>
            </form>
          </section>

          <section>
            <h2>Mark attendance</h2>
            <label className="date">Date
              <input type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} />
            </label>

            {roster.length === 0 ? (
              <p className="muted">No students in this class yet. Add students by username above.</p>
            ) : (
              <>
                <div className="toolbar">
                  <button type="button" className="ghost" onClick={() => markAll('present')}>Mark all present</button>
                  <span className="muted">{markedCount} of {roster.length} marked</span>
                </div>
                <table>
                  <thead>
                    <tr><th>Student</th><th>Username</th><th>Present</th><th>Absent</th></tr>
                  </thead>
                  <tbody>
                    {roster.map((s) => (
                      <tr key={s.userId}>
                        <td>{s.name}</td>
                        <td>{s.username}</td>
                        {['present', 'absent'].map((status) => (
                          <td key={status}>
                            <label className="choice">
                              <input
                                type="radio"
                                name={`mark-${s.userId}`}
                                checked={marks[s.userId] === status}
                                onChange={() => setMarks({ ...marks, [s.userId]: status })}
                                aria-label={`${s.name} ${status}`}
                              />
                            </label>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <button onClick={save} disabled={!allMarked || saving}>
                  {saving ? 'Saving…' : 'Save attendance'}
                </button>
                {!allMarked && <p className="muted">Mark every student to save.</p>}
              </>
            )}
          </section>
        </>
      )}
    </div>
  )
}
