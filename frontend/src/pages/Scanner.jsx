import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Scanner.css';

// --- NEW: Vanilla IndexedDB Helper (No NPM packages needed) ---
const saveToIndexedDB = (historyItem) => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('VeriDocHistoryDB', 1);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('scans')) {
        db.createObjectStore('scans', { keyPath: 'id' });
      }
    };

    request.onsuccess = (event) => {
      const db = event.target.result;
      const tx = db.transaction('scans', 'readwrite');
      const store = tx.objectStore('scans');
      
      // Save the item (which now contains the raw File blob, not a Base64 string!)
      store.put(historyItem);

      tx.oncomplete = () => resolve();
      tx.onerror = (e) => reject(e);
    };

    request.onerror = (e) => reject(e);
  });
};
// --------------------------------------------------------------

export default function Scanner() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState("en");
  const [useAI, setUseAI] = useState(false); 
  const [activeStep, setActiveStep] = useState(0); 
  const navigate = useNavigate();

  useEffect(() => {
    let interval;
    if (loading) {
      interval = setInterval(() => {
        setActiveStep((prev) => (prev < 2 ? prev + 1 : prev)); 
      }, useAI ? 1500 : 800); 
    }
    return () => clearInterval(interval);
  }, [loading, useAI]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setActiveStep(0); 
    }
  };

  const handleUpload = async () => {
    if (!file) return alert("Please select a document first!");

    setLoading(true);
    setActiveStep(1); 
    
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    formData.append("use_ai", useAI.toString()); 

    try {
      const response = await fetch("https://smsram-veridoc-backend.hf.space/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Backend analysis failed");

      const data = await response.json();
      
      setLoading(false);
      setActiveStep(3); 
      
      // Temporary URL for instant loading on the next page
      const fileUrl = URL.createObjectURL(file);
      const actualFileType = file.type || (file.name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'image/jpeg');

      // --- NEW: FAST INDEXED-DB STORAGE ---
      try {
        const newHistoryItem = {
          id: `VD-${Math.floor(1000 + Math.random() * 9000)}`,
          name: file.name,
          date: new Date().toLocaleString(),
          timestamp: Date.now(),
          risk: data.xai_report.overall_probability > 50 ? 'High' : 'Low',
          score: data.xai_report.overall_probability,
          type: actualFileType.includes('pdf') ? 'pdf' : 'image',
          mimeType: actualFileType,
          fullReport: data,       
          rawFileBlob: file // WE SAVE THE RAW FILE directly! Extremely fast.
        };

        // Save asynchronously in the background
        await saveToIndexedDB(newHistoryItem);

      } catch (storageError) {
        console.error("IndexedDB Save Failed:", storageError);
      }
      // ------------------------------------

      // I lowered the wait time from 2000ms to 800ms. 
      // It still shows the checkmark, but moves much faster!
      setTimeout(() => {
        navigate('/report', { 
          state: { 
            reportData: data, 
            originalFileUrl: fileUrl, 
            fileType: actualFileType
          } 
        });
      }, 800); 

    } catch (error) {
      console.error("Upload Error:", error);
      alert("Analysis timed out or failed. Please try again.");
      setLoading(false);
      setActiveStep(0); 
    }
  };

  const getProgressHeight = () => {
    if (activeStep === 0) return '0%';
    if (activeStep === 1) return '50%'; 
    if (activeStep >= 2) return '100%'; 
    return '0%';
  };

  return (
    <div className="scanner-container">
      <header className="scanner-header">
        <h1>Document Scanner</h1>
        <p className="hero-subtitle" style={{textAlign: 'left', margin: '0'}}>
          Upload files for deep forensic analysis, PDF structural recovery, and pixel-level scrutiny.
        </p>
      </header>

      <div className="scanner-grid">
        {/* Left Column: Upload */}
        <div className="upload-section">
          
          <div className="form-group">
            <label className="form-label">Document Language</label>
            <select 
              className="custom-select"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={loading || activeStep === 3}
            >
              <option value="en">English (Default)</option>
              <option value="te">Telugu</option>
              <option value="hi">Hindi</option>
            </select>
          </div>

          {/* NEW: Deep AI Toggle */}
          <div className={`form-group toggle-group ${loading ? 'disabled' : ''}`}>
            <label className="form-label" style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: 0, cursor: loading ? 'default' : 'pointer'}}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-main)' }}>Enable Deep AI Scan (Gemini)</span>
              <div 
                className={`toggle-switch ${useAI ? 'on' : 'off'}`}
                onClick={() => !loading && activeStep !== 3 && setUseAI(!useAI)}
              >
                <div className="toggle-knob"></div>
              </div>
            </label>
            <p style={{fontSize: '0.75rem', color: 'var(--text-muted)', margin: '4px 0 0 0'}}>
              Uses multimodal LLMs for semantic context. Takes slightly longer.
            </p>
          </div>

          <div 
            className={`dropzone ${loading ? 'processing' : ''}`} 
            onClick={() => !loading && activeStep !== 3 && document.getElementById('fileInput').click()}
            style={{ cursor: (loading || activeStep === 3) ? 'default' : 'pointer' }}
          >
            <input 
              type="file" 
              id="fileInput" 
              hidden 
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileChange} 
            />
            <div className="upload-icon-circle">
              <span className={`material-symbols-outlined ${loading ? 'animate-pulse' : ''}`} style={{fontSize: '32px'}}>
                {activeStep >= 3 ? 'task_alt' : (loading ? 'hourglass_empty' : 'upload_file')}
              </span>
            </div>
            <h3 style={{fontFamily: 'var(--font-heading)', marginBottom: '8px'}}>
              {file ? file.name : "Drag & Drop Documents"}
            </h3>
            
            <p style={{fontSize: '0.875rem', color: activeStep >= 3 ? '#10b981' : 'var(--text-muted)', textAlign: 'center', marginBottom: '24px', fontWeight: activeStep >= 3 ? 'bold' : 'normal'}}>
              {loading ? "Forensic engines active. Do not close this page..." : (activeStep >= 3 ? "Analysis Complete! Generating Report..." : "Support for high-resolution PDF, JPG, PNG.")}
            </p>
            
            {!loading && activeStep !== 3 && (
              <button 
                className="nav-btn" 
                style={{backgroundColor: file ? 'var(--primary)' : 'var(--bg-card-border)'}}
                onClick={(e) => {
                  e.stopPropagation();
                  file ? handleUpload() : document.getElementById('fileInput').click();
                }}
              >
                {file ? "Start Forensic Scan" : "Browse Files"}
              </button>
            )}
          </div>
        </div>

        {/* Right Column: Animated Tracker */}
        <div className="tracker-section">
          <h3 className="tracker-title">Forensic Pipeline</h3>
          <div className="timeline">
            
            {/* THE FIX: Line runs directly through the icons */}
            <div className="timeline-line"></div>
            <div 
              className="timeline-line-active" 
              style={{
                height: getProgressHeight(), 
                transition: 'height 0.8s ease-in-out'
              }}
            ></div>

            {/* Step 1 */}
            <div className={`step ${activeStep >= 1 ? 'active' : 'pending'}`}>
              <div className="step-circle" style={{ backgroundColor: activeStep >= 1 ? '#3b82f6' : '', borderColor: activeStep >= 1 ? '#3b82f6' : '' }}>
                <span className="material-symbols-outlined step-icon" style={{fontSize: '18px', color: activeStep >= 1 ? '#fff' : ''}}>data_object</span>
              </div>
              <div className="step-content">
                <h4 className={activeStep >= 1 ? "text-primary" : ""}>Structural & Metadata Check</h4>
                <p>Scanning EXIF tags and parsing PDF `%%EOF` markers for incremental updates.</p>
              </div>
            </div>

            {/* Step 2 */}
            <div className={`step ${activeStep >= 2 ? 'active' : 'pending'}`}>
              <div className="step-circle" style={{ backgroundColor: activeStep >= 2 ? '#3b82f6' : '', borderColor: activeStep >= 2 ? '#3b82f6' : '' }}>
                <span className="material-symbols-outlined step-icon" style={{fontSize: '18px', color: activeStep >= 2 ? '#fff' : ''}}>image_search</span>
              </div>
              <div className="step-content">
                <h4 className={activeStep >= 2 ? "text-primary" : ""}>Pixel Variance & OCR</h4>
                <p>Calculating ELA Spike Ratios to detect digital ink and spliced layers.</p>
              </div>
            </div>

            {/* Step 3 */}
            <div className={`step ${activeStep >= 3 ? 'active' : 'pending'}`}>
              <div className="step-circle" style={{ backgroundColor: activeStep >= 3 ? '#10b981' : '', borderColor: activeStep >= 3 ? '#10b981' : '' }}>
                <span className="material-symbols-outlined step-icon" style={{fontSize: '18px', color: activeStep >= 3 ? '#fff' : ''}}>
                  {activeStep >= 3 ? 'check' : 'summarize'}
                </span>
              </div>
              <div className="step-content">
                <h4 className={activeStep >= 3 ? "text-emerald-500" : ""}>
                  {useAI && activeStep < 3 ? "Generating Gemini XAI Report" : "Compiling Forensic Dossier"}
                </h4>
                <p>Generating unified explainability report and risk score.</p>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}