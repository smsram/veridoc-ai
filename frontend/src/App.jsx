import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Scanner from './pages/Scanner';
import Report from './pages/Report';
import History from './pages/History'; // <-- Import the real History component

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) mainContent.scrollTop = 0;
  }, [pathname]);
  return null;
}

function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="scan" element={<Scanner />} />
          <Route path="report" element={<Report />} />
          <Route path="history" element={<History />} /> {/* <-- Updated route */}
          <Route path="*" element={<Dashboard />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;