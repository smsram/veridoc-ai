import { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import './MainLayout.css';

export default function MainLayout() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  // Auto-close mobile menu on page change
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location]);

  const navLinks = [
    { name: 'Dashboard', path: '/' },
    { name: 'Scanner', path: '/scan' },
    { name: 'Reports', path: '/report' }, // Added the Report option
    { name: 'History', path: '/history' },
  ];

  return (
    <div className="app-container">
      
      {/* 1. Fixed Top Navigation */}
      <nav className="navbar">
        <div className="nav-content">
          <Link to="/" className="brand">
            <span className="material-symbols-outlined icon">policy</span>
            <span>VeriDoc AI</span>
          </Link>

          <div className="nav-links">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                to={link.path}
                className={`nav-link ${location.pathname === link.path ? 'active' : ''}`}
              >
                {link.name}
              </Link>
            ))}
          </div>

          <Link to="/scan" className="nav-btn desktop-only">
            <span className="material-symbols-outlined">document_scanner</span>
            <span>Start Verification</span>
          </Link>

          <button 
            className="menu-toggle" 
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle navigation"
          >
            <span className="material-symbols-outlined">
              {isMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </nav>

      {/* 2. Mobile Slide-down Menu */}
      <div className={`mobile-menu ${isMenuOpen ? 'open' : ''}`}>
        <div className="mobile-menu-content">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              to={link.path}
              className={`mobile-nav-link ${location.pathname === link.path ? 'active' : ''}`}
            >
              {link.name}
            </Link>
          ))}
          <Link to="/scan" className="mobile-scan-btn">
            <span className="material-symbols-outlined">document_scanner</span>
            <span>Start Verification</span>
          </Link>
        </div>
      </div>

      {/* 3. Scrollable Page Content */}
      <div className="main-content">
        <Outlet />
      </div>

    </div>
  );
}