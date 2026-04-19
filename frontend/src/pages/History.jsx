import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './History.css';

// Reusable Custom Dropdown Component
const CustomDropdown = ({ options, value, onChange, icon }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div className="custom-dropdown" ref={dropdownRef}>
      <div className="dropdown-header" onClick={() => setIsOpen(!isOpen)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {icon && <span className="material-symbols-outlined" style={{fontSize: '18px', color: 'var(--text-muted)'}}>{icon}</span>}
          <span>{selectedOption?.label}</span>
        </div>
        <span className={`material-symbols-outlined arrow ${isOpen ? 'open' : ''}`}>expand_more</span>
      </div>
      {isOpen && (
        <div className="dropdown-list">
          {options.map((option) => (
            <div
              key={option.value}
              className={`dropdown-item ${value === option.value ? 'selected' : ''}`}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
            >
              {option.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default function History() {
  const [history, setHistory] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const navigate = useNavigate();
  
  // Default retention is 1 day
  const [retention, setRetention] = useState(() => {
    return localStorage.getItem('veridoc_retention') || 'day';
  });

  // SINGLE UNIFIED DB LOADER
  const loadHistoryFromDB = (policy) => {
    try {
      const request = indexedDB.open('VeriDocHistoryDB', 1);
      request.onsuccess = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains('scans')) {
            setHistory([]);
            return;
        }
        
        const tx = db.transaction('scans', 'readonly');
        const store = tx.objectStore('scans');
        const getAllRequest = store.getAll();

        getAllRequest.onsuccess = () => {
          const dbData = getAllRequest.result || [];
          const sortedData = dbData.sort((a, b) => b.timestamp - a.timestamp);
          
          // Apply Retention Policy Filter
          if (policy === 'never') {
            setHistory([]);
            return;
          }

          const now = Date.now();
          const maxAge = policy === 'week' ? 7 * 86400000 : policy === 'month' ? 30 * 86400000 : 86400000;
          const validData = sortedData.filter(item => (now - item.timestamp) < maxAge);
          
          setHistory(validData);
        };
      };
    } catch (error) {
      console.error("Error loading from IndexedDB", error);
      setHistory([]);
    }
  };

  // Load on mount
  useEffect(() => {
    loadHistoryFromDB(retention);
  }, []);

  const handleRetentionChange = (newPolicy) => {
    setRetention(newPolicy);
    localStorage.setItem('veridoc_retention', newPolicy);
    loadHistoryFromDB(newPolicy);
  };

  const handleDelete = (id) => {
    const request = indexedDB.open('VeriDocHistoryDB', 1);
    request.onsuccess = (event) => {
      const db = event.target.result;
      const tx = db.transaction('scans', 'readwrite');
      const store = tx.objectStore('scans');
      store.delete(id); 
      tx.oncomplete = () => {
        setHistory(prev => prev.filter(item => item.id !== id));
      };
    };
  };

  const handleClearAll = () => {
    if (window.confirm("Are you sure you want to delete all scan history?")) {
      const request = indexedDB.open('VeriDocHistoryDB', 1);
      request.onsuccess = (event) => {
        const db = event.target.result;
        const tx = db.transaction('scans', 'readwrite');
        const store = tx.objectStore('scans');
        store.clear(); 
        tx.oncomplete = () => setHistory([]);
      };
    }
  };

  // THE FIX: Safe Navigation Handler (Prevents URL Memory Leaks & Crashes)
  const handleViewReport = (item) => {
    // Generate the URL *only* when the user clicks the button
    const url = item.rawFileBlob ? URL.createObjectURL(item.rawFileBlob) : item.fileData;
    
    navigate('/report', { 
      state: { 
        reportData: item.fullReport, 
        originalFileUrl: url, 
        fileType: item.mimeType || (item.type === 'pdf' ? 'application/pdf' : 'image/jpeg')
      } 
    });
  };

  const filteredHistory = history.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          item.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRisk = riskFilter === 'all' || item.risk.toLowerCase() === riskFilter;
    return matchesSearch && matchesRisk;
  });

  return (
    <div className="history-container">
      <header className="history-header">
        <div>
          <h1>Forensic History</h1>
          <p>Locally stored records of previous document scans.</p>
        </div>
        
        <div className="history-settings">
          <CustomDropdown 
            icon="update"
            options={[
              { value: 'never', label: 'Never Store' },
              { value: 'day', label: 'Keep 24 Hours' },
              { value: 'week', label: 'Keep 1 Week' },
              { value: 'month', label: 'Keep 1 Month' }
            ]}
            value={retention}
            onChange={handleRetentionChange}
          />
          <button className="btn-clear-all" onClick={handleClearAll}>
            <span className="material-symbols-outlined" style={{fontSize: '18px'}}>delete_sweep</span>
            Clear All
          </button>
        </div>
      </header>

      <section className="controls-row">
        <div className="search-wrapper">
          <span className="material-symbols-outlined icon">search</span>
          <input 
            type="text" 
            className="search-input" 
            placeholder="Search filename or scan ID..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div style={{ width: '220px' }}>
          <CustomDropdown 
            icon="filter_list"
            options={[
              { value: 'all', label: 'All Statuses' },
              { value: 'high', label: 'High Risk' },
              { value: 'low', label: 'Low Risk' }
            ]}
            value={riskFilter}
            onChange={setRiskFilter}
          />
        </div>
      </section>

      <section className="history-list">
        {filteredHistory.length === 0 ? (
          <div className="empty-state">
            <span className="material-symbols-outlined" style={{fontSize: '48px', color: 'var(--bg-card-border)'}}>history_toggle_off</span>
            <h3>No Scan History</h3>
            <p>Your previous scans will appear here based on your retention policy.</p>
          </div>
        ) : (
          filteredHistory.map((item) => (
            <article key={item.id} className="history-card slide-up">
              <div className="file-info-box">
                <div className="file-icon">
                  <span className="material-symbols-outlined" style={{ color: item.risk === 'High' ? 'var(--color-error)' : '#10b981' }}>
                    {item.type === 'pdf' ? 'picture_as_pdf' : 'image'}
                  </span>
                </div>
                <div className="file-details">
                  <h3>{item.name}</h3>
                  <div className="meta-sub">
                    <span className="id-badge">{item.id}</span>
                    <span>•</span>
                    <span>{item.date}</span>
                  </div>
                </div>
              </div>

              <div className="status-zone">
                <div style={{ textAlign: 'right' }}>
                  <span className={`risk-tag ${item.risk === 'High' ? 'risk-high' : 'risk-low'}`}>
                    <div className="status-dot" style={{ backgroundColor: 'currentColor' }}></div>
                    {item.risk} Risk ({item.score}%)
                  </span>
                </div>
                <div className="action-buttons">
                  {/* CHANGED: Used onClick instead of Link to prevent Render loop crashes! */}
                  <button 
                    onClick={() => handleViewReport(item)}
                    className="btn-view-report" 
                    title="View Full Report"
                  >
                    View
                  </button>
                  <button className="btn-delete-single" onClick={() => handleDelete(item.id)} title="Delete Scan">
                    <span className="material-symbols-outlined">delete</span>
                  </button>
                </div>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}