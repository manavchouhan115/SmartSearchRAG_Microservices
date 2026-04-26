import { useState } from 'react';
import Login from './components/Login';
import Ingest from './components/Ingest';
import Chat from './components/Chat';
import { LogOut } from 'lucide-react';

function App() {
  const [token, setToken] = useState(sessionStorage.getItem('token'));

  if (!token) return <Login setToken={setToken} />;

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <header style={{ 
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
        marginBottom: '2rem', padding: '0 1rem' 
      }}>
        <h1>SmartSearch Dashboard</h1>
        <button 
          onClick={() => { sessionStorage.removeItem('token'); setToken(null); }}
          style={{ width: 'auto', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', padding: '0.5rem 1rem' }}
        >
          <LogOut size={18} /> Logout
        </button>
      </header>
      
      <div className="layout">
        <Ingest token={token} />
        <Chat token={token} />
      </div>
    </div>
  );
}

export default App;
