import { Link } from 'react-router-dom';
import './Dashboard.css';

export default function Dashboard() {
  return (
    <main className="dashboard-wrapper">
      <div className="ambient-light"></div>

      <div className="hero-section">
        <div className="status-pill">
          <span className="material-symbols-outlined">auto_awesome</span>
          <span>System Operational • V2.4</span>
        </div>

        <div>
          <h1 className="hero-title">
            AI-Powered Document<br />Forgery Detection
          </h1>
          <p className="hero-subtitle">
            Deploy advanced machine learning models to identify anomalies, manipulation, and synthetic generation across all digital documents.
          </p>
        </div>

        {/* Use the specific class defined in Dashboard.css */}
        <Link to="/scan" className="btn-hero">
          <span className="material-symbols-outlined">radar</span>
          <span>Start Verification</span>
        </Link>

        <div className="stats-container">
          <div className="stat-item">
            <span className="material-symbols-outlined icon">check_circle</span>
            <span>99.8% Accuracy</span>
          </div>
          <div className="stat-item">
            <span className="material-symbols-outlined icon">speed</span>
            <span>&lt; 2s Processing</span>
          </div>
          <div className="stat-item">
            <span className="material-symbols-outlined icon">lock</span>
            <span>End-to-End Encryption</span>
          </div>
        </div>
      </div>
    </main>
  );
}