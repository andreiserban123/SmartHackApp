import { Routes, Route, Link } from 'react-router-dom'
import Dashboard from './Dashboard/Dashboard'
import './App.css'

const Home = () => {
  return (
    <div className="home">
      <h1>Welcome to Homepage</h1>
      <Link to="/dashboard" className="dashboard-link">
        Go to Dashboard
      </Link>
    </div>
  )
}

function App() {
  return (
    <>
      <nav className="navigation">
        <Link to="/">Home</Link>
        <Link to="/dashboard"> Dashboard</Link>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </>
  )
}

export default App