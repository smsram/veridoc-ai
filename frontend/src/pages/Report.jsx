import React, { useState } from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import './Report.css';

export default function Report() {
  const location = useLocation();
  const [viewMode, setViewMode] = useState('original'); // 'original', 'heatmap', or 'recovered'

  if (!location.state || !location.state.reportData) {
    return <Navigate to="/scan" />;
  }

  const { reportData, originalFileUrl, fileType } = location.state;
  const report = reportData.xai_report;
  const isHighRisk = report.overall_probability > 50;

  // --- DOWNLOAD FUNCTIONALITIES ---
  
  // 1. Export PDF (Prints the report)
  const handleExportPDF = () => {
    window.print();
  };

  // 2. View/Download Raw JSON Data
  const handleViewRawData = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(reportData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `forensic_raw_${reportData.file_analyzed}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  // 3. Download the currently viewed file (Original, Heatmap, or Recovered)
  const handleDownloadCurrentView = () => {
    const link = document.createElement('a');
    if (viewMode === 'heatmap') {
      link.href = reportData.heatmap_image;
      link.download = `heatmap_${reportData.file_analyzed}.jpg`;
    } else if (viewMode === 'recovered') {
      link.href = reportData.recovered_pdf;
      link.download = `recovered_original_${reportData.file_analyzed}`;
    } else {
      link.href = originalFileUrl;
      link.download = `submitted_${reportData.file_analyzed}`;
    }
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="report-container">
      
      {/* Header Section */}
      <header className="report-header">
        <div>
          <div className="breadcrumb">
            <span className="material-symbols-outlined" style={{fontSize: '18px'}}>folder</span>
            <span>Reports</span>
            <span className="material-symbols-outlined" style={{fontSize: '18px'}}>chevron_right</span>
            <span className="active">{reportData.file_analyzed}</span>
          </div>
          <h1 className="report-title">Explainability Report</h1>
        </div>
        
        <div className="header-actions">
          <button className="btn-text" onClick={handleExportPDF}>
            <span className="material-symbols-outlined" style={{fontSize: '18px', verticalAlign: 'middle', marginRight: '6px'}}>picture_as_pdf</span>
            Export PDF
          </button>
          <button className="btn-secondary" onClick={handleViewRawData}>
            <span className="material-symbols-outlined" style={{fontSize: '18px', verticalAlign: 'middle', marginRight: '6px'}}>code</span>
            Raw Data
          </button>
        </div>
      </header>

      <div className="report-grid">
        
        {/* LEFT: Visual Analysis */}
        <div className="visual-card">
          <div className="visual-toolbar">
            <h2>Document Viewer</h2>
            
            {/* View Toggles - Using clean CSS classes now */}
            <div className="toggle-container">
              <button 
                onClick={() => setViewMode('original')}
                className={`view-toggle-btn ${viewMode === 'original' ? 'active' : ''}`}
              >
                Submitted
              </button>
              
              <button 
                onClick={() => setViewMode('heatmap')}
                className={`view-toggle-btn ${viewMode === 'heatmap' ? 'active' : ''}`}
              >
                AI Heatmap
              </button>

              {/* Recovery Button */}
              {reportData.recovered_pdf && (
                <button 
                  onClick={() => setViewMode('recovered')}
                  className={`view-toggle-btn recovery-btn ${viewMode === 'recovered' ? 'active' : ''}`}
                >
                  <span className="material-symbols-outlined">history</span>
                  View Recovered
                </button>
              )}
            </div>
          </div>
          
          <div className="document-viewer">
            {/* Download icon overlaid on the document viewer */}
            <button className="viewer-download-btn" onClick={handleDownloadCurrentView} title="Download Current File">
              <span className="material-symbols-outlined">download</span>
            </button>

            {/* Render Views with smooth fade-in animation keys */}
            {viewMode === 'original' && (
              fileType === 'application/pdf' ? (
                <iframe key="orig-pdf" className="fade-in-fast" src={`${originalFileUrl}#toolbar=0`} title="Document Preview" />
              ) : (
                <img key="orig-img" className="fade-in-fast doc-img" src={originalFileUrl} alt="Original Document" />
              )
            )}

            {viewMode === 'heatmap' && (
              <img key="heat-img" className="fade-in-fast doc-img" src={reportData.heatmap_image} alt="ELA Heatmap" />
            )}

            {viewMode === 'recovered' && reportData.recovered_pdf && (
              <iframe key="rec-pdf" className="fade-in-fast" src={`${reportData.recovered_pdf}#toolbar=0`} title="Recovered Original" />
            )}
          </div>
        </div>

        {/* RIGHT: Explainability Panel */}
        <div className="explain-panel">
          
          <div className="alert-card" style={{ borderColor: isHighRisk ? 'rgba(255, 180, 171, 0.4)' : 'rgba(16, 185, 129, 0.4)' }}>
            <div className="alert-glow" style={{ backgroundColor: isHighRisk ? 'var(--color-error)' : '#10b981' }}></div>
            <div className="alert-icon" style={{ color: isHighRisk ? 'var(--color-error)' : '#10b981', backgroundColor: isHighRisk ? 'var(--color-error-glow)' : 'rgba(16,185,129,0.1)' }}>
              <span className="material-symbols-outlined" style={{fontSize: '32px'}}>
                {isHighRisk ? 'warning' : 'verified_user'}
              </span>
            </div>
            <div className="alert-content">
              <h2 style={{color: isHighRisk ? 'var(--color-error)' : '#10b981'}}>
                {report.overall_probability}% Probability of Forgery
              </h2>
              <p>{report.executive_summary}</p>
            </div>
          </div>

          <div className="anomalies-card">
            <h3 className="card-title">
              <span className="material-symbols-outlined" style={{color: 'var(--text-muted)'}}>list_alt</span>
              Detected Anomalies
            </h3>
            
            {report.detailed_anomalies && report.detailed_anomalies.length > 0 ? (
              report.detailed_anomalies.map((anomaly, idx) => (
                <div key={idx} className="anomaly-item">
                  <div className={`dot ${anomaly.severity === 'Critical' ? 'critical' : 'warning'}`}></div>
                  <div className="anomaly-content">
                    <h4>{anomaly.title}</h4>
                    <p>{anomaly.description}</p>
                    <div className="tags">
                      <span className="tag">Severity: {anomaly.severity || 'Medium'}</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p style={{color: 'var(--text-muted)'}}>No significant anomalies detected. The document appears structurally sound.</p>
            )}
          </div>

          <div className="metadata-card">
            <h4 className="metadata-title">Scan Metadata</h4>
            <div className="metadata-grid">
              <span className="meta-label">Scanner Engine</span>
              <span className="meta-value">VD-Core v5.0</span>
              
              <span className="meta-label">PDF Revisions</span>
              <span className="meta-value">{reportData.metadata?.revisions_detected || 0}</span>
              
              <span className="meta-label">Language Target</span>
              <span className="meta-value">{reportData.metadata?.language_detected?.toUpperCase() || 'EN'}</span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}