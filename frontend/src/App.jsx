import { useState } from "react";
import axios from "axios";
import "./App.css";

const API = "http://localhost:5000/api";

function App() {
  const [user, setUser] = useState(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [attendance, setAttendance] = useState([]);
  const [message, setMessage] = useState("");

  const login = async (e) => {
    e.preventDefault();

    try {
      const response = await axios.post(`${API}/login`, {
        email,
        password,
      });

      setUser(response.data.user);

      loadAttendance(response.data.user.userId);

    } catch (error) {
      setMessage(
        error.response?.data?.message || "Login failed"
      );
    }
  };

  const loadAttendance = async (userId) => {
    try {
      const response = await axios.get(
        `${API}/attendance/${userId}`
      );

      setAttendance(response.data.attendance);

    } catch (error) {
      console.error(error);
    }
  };

  const checkIn = async () => {
    try {
      const response = await axios.post(
        `${API}/attendance/checkin`,
        {
          userId: user.userId,
        }
      );

      setMessage(response.data.message);

      loadAttendance(user.userId);

    } catch (error) {
      setMessage(
        error.response?.data?.message || "Check-in failed"
      );
    }
  };

  const checkOut = async () => {
    try {
      const response = await axios.post(
        `${API}/attendance/checkout`,
        {
          userId: user.userId,
        }
      );

      setMessage(response.data.message);

      loadAttendance(user.userId);

    } catch (error) {
      setMessage(
        error.response?.data?.message || "Check-out failed"
      );
    }
  };

  const logout = () => {
    setUser(null);
    setAttendance([]);
    setMessage("");
  };

  if (!user) {
    return (
      <div className="login-container">

        <form className="login-card" onSubmit={login}>

          <h1>Attendance System</h1>

          <p>Serverless Attendance Platform</p>

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit">
            Login
          </button>

          {message && (
            <div className="message">
              {message}
            </div>
          )}

        </form>

      </div>
    );
  }

  return (
    <div className="dashboard">

      <header>

        <div>
          <h1>Attendance Dashboard</h1>

          <p>
            Welcome, <strong>{user.name}</strong>
          </p>
        </div>

        <button
          className="logout"
          onClick={logout}
        >
          Logout
        </button>

      </header>

      <main>

        <section className="profile-card">

          <h2>Today's Attendance</h2>

          <div className="actions">

            <button onClick={checkIn}>
              Check In
            </button>

            <button onClick={checkOut}>
              Check Out
            </button>

          </div>

          {message && (
            <div className="message">
              {message}
            </div>
          )}

        </section>


        <section className="history">

          <h2>Attendance History</h2>

          {attendance.length === 0 ? (

            <p>No attendance records found.</p>

          ) : (

            <table>

              <thead>

                <tr>
                  <th>Date</th>
                  <th>Check In</th>
                  <th>Check Out</th>
                  <th>Status</th>
                </tr>

              </thead>

              <tbody>

                {attendance.map((record, index) => (

                  <tr key={index}>

                    <td>{record.date}</td>

                    <td>{record.checkIn}</td>

                    <td>
                      {record.checkOut || "-"}
                    </td>

                    <td>
                      {record.status}
                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          )}

        </section>

      </main>

    </div>
  );
}

export default App;
