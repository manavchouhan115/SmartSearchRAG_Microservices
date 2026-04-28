import { useState, useEffect } from 'react';
import Login from './components/Login';
import Ingest from './components/Ingest';
import Chat from './components/Chat';
import AgentTrace from './components/AgentTrace';
import { LogOut, Activity } from 'lucide-react';

function App() {
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [traceState, setTraceState] = useState('idle');
  const [metrics, setMetrics] = useState({});

  useEffect(() => {
    const handleAuthExpired = () => setToken(null);
    window.addEventListener('auth_expired', handleAuthExpired);
    return () => window.removeEventListener('auth_expired', handleAuthExpired);
  }, []);

  if (!token) return <Login setToken={setToken} />;

  return (
    <div style={{ width: '100%', maxWidth: '1400px', margin: '0 auto', height: '100%', padding: '2rem 1rem' }}>
      <header style={{ 
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
        marginBottom: '2.5rem' 
      }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.8rem', textShadow: '0 0 20px rgba(6, 182, 212, 0.5)' }}>
           <Activity color="var(--accent-neon)" size={28} /> AI Telemetry Command Center
        </h1>
        <button 
          onClick={() => { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); setToken(null); }}
          style={{ width: 'auto', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', padding: '0.5rem 1rem', border: '1px solid rgba(239, 68, 68, 0.3)' }}
        >
          <LogOut size={18} /> Disengage
        </button>
      </header>
      
      <div className="telemetry-layout">
        <div className="left-pane">
          <Ingest token={token} />
          <Chat token={token} setTraceState={setTraceState} setMetrics={setMetrics} />
        </div>
        <AgentTrace traceState={traceState} metrics={metrics} />
      </div>
    </div>
  );
}

export default App;
