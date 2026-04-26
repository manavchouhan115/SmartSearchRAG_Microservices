import { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { fetchWithAuth } from '../api';

export default function Ingest({ token }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, complete, error
  const [message, setMessage] = useState('');
  const fileInputRef = useRef(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setStatus('uploading');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection_name', 'docker_collection');

    try {
      const res = await fetchWithAuth('/api/ingest', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) throw new Error('Upload failed. Must be PDF.');
      const data = await res.json();
      pollStatus(data.job_id);
    } catch (err) {
      setStatus('error');
      setMessage(err.message);
    }
  };

  const pollStatus = async (jobId) => {
    setStatus('processing');
    const interval = setInterval(async () => {
      try {
        const res = await fetchWithAuth(`/api/status/${jobId}`);
        const data = await res.json();
        
        if (data.status === 'completed') {
          clearInterval(interval);
          setStatus('complete');
          const count = data.result?.inserted_count;
          setMessage(`Successfully indexed ${count || '?'} knowledge chunks!`);
          setFile(null);
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setStatus('error');
          setMessage(data.error || 'Ingestion failed on backend.');
        }
      } catch (err) {
        clearInterval(interval);
        setStatus('error');
        setMessage('Network error during polling.');
      }
    }, 2000);
  };

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ marginBottom: '1.5rem', fontWeight: 600 }}>Knowledge Base</h2>
      <div 
        style={{
          flex: 1,
          border: '2px dashed var(--glass-border)',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(15,23,42,0.3)',
          cursor: 'pointer',
          padding: '2rem',
          textAlign: 'center',
          transition: 'all 0.3s ease'
        }}
        onClick={() => fileInputRef.current?.click()}
        className={status === 'processing' ? 'processing' : ''}
      >
        <input 
          type="file" 
          accept=".pdf" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={(e) => setFile(e.target.files[0])}
        />
        
        {status === 'idle' && (
          <>
            <UploadCloud size={48} color="var(--accent-primary)" style={{ marginBottom: '1rem' }} />
            {file ? <p style={{ color: 'white', fontWeight: 500 }}>{file.name}</p> : <p>Click to browse PDFs</p>}
          </>
        )}
        
        {status === 'uploading' && <div className="spin-icon"><Loader2 size={48} color="var(--text-secondary)" /></div>}
        {status === 'processing' && (
          <>
            <div className="spin-icon"><Loader2 size={48} color="var(--accent-primary)" /></div>
            <p style={{ marginTop: '1rem', color: 'var(--accent-primary)' }}>Vectorizing & Indexing...</p>
          </>
        )}
        
        {status === 'complete' && (
          <>
            <CheckCircle size={48} color="#10b981" style={{ marginBottom: '1rem' }} />
            <p style={{ color: '#10b981' }}>{message}</p>
          </>
        )}

        {status === 'error' && (
          <>
            <AlertCircle size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
            <p style={{ color: '#ef4444' }}>{message}</p>
          </>
        )}
      </div>

      {file && status === 'idle' && (
        <button style={{ marginTop: '1rem' }} onClick={handleUpload}>
          Process Document
        </button>
      )}

      {status === 'complete' && (
        <button style={{ marginTop: '1rem', background: 'rgba(255,255,255,0.1)' }} onClick={() => setStatus('idle')}>
          Upload Another
        </button>
      )}

      <style dangerouslySetInnerHTML={{__html: `
        .spin-icon { animation: spin 1.5s linear infinite; display: inline-block; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}} />
    </div>
  );
}
