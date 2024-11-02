import './Dashboard.css'

function Dashboard() {
  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Dashboard Overview</h1>
        <div className="header-actions">
          <button className="dashboard-button">+ New Report</button>
        </div>
      </header>
      
      <div className="statistics-grid">
        <div className="stat-card">
          <h4>Total Users</h4>
          <div className="stat-number">1,234</div>
          <p>+12% from last month</p>
        </div>
        <div className="stat-card">
          <h4>Active Users</h4>
          <div className="stat-number">789</div>
          <p>+5% from last month</p>
        </div>
        <div className="stat-card">
          <h4>Revenue</h4>
          <div className="stat-number">$45,678</div>
          <p>+8% from last month</p>
        </div>
        <div className="stat-card">
          <h4>Conversion Rate</h4>
          <div className="stat-number">2.4%</div>
          <p>+0.5% from last month</p>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Recent Activity</h3>
          <div className="card-content">
            <ul>
              <li>User login <span>2 minutes ago</span></li>
              <li>New post created <span>5 minutes ago</span></li>
              <li>Profile updated <span>10 minutes ago</span></li>
              <li>Settings changed <span>15 minutes ago</span></li>
            </ul>
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Performance Metrics</h3>
          <div className="card-content">
            <p>Page Load Time: 1.2s</p>
            <p>Server Response: 0.8s</p>
            <p>Database Queries: 145/s</p>
            <p>Error Rate: 0.02%</p>
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Quick Actions</h3>
          <div className="card-content">
            <button className="dashboard-button">Generate Report</button>
            <button className="dashboard-button">Update Profile</button>
            <button className="dashboard-button">View Analytics</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard