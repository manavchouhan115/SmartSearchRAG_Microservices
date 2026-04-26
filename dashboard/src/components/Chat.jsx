import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, ShieldCheck } from 'lucide-react';

export default function Chat({ token }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hello! I am SmartSearch. I am ready to answer questions based on your specialized knowledge base.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setLoading(true);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question: userMsg, collection_name: 'docker_collection' })
      });

      if (!res.ok) throw new Error('Query failed');
      const data = await res.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: data.answer || "I'm sorry, I couldn't find enough information in the vector database to answer that.",
        confidence: data.confidence 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Error: Could not reach the agent backend.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '10px', display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1rem' }} ref={scrollRef}>
        {messages.map((msg, i) => (
          <div key={i} style={{ 
            display: 'flex', 
            gap: '12px',
            alignItems: 'flex-start',
            flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
          }}>
            <div style={{ 
              background: msg.role === 'user' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
              padding: '10px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              {msg.role === 'user' ? <User size={20} color="white" /> : <Bot size={20} color="var(--accent-primary)" />}
            </div>
            
            <div style={{ 
              background: msg.role === 'user' ? 'var(--accent-primary)' : 'rgba(15,23,42,0.6)',
              padding: '1rem',
              borderRadius: '16px',
              borderTopRightRadius: msg.role === 'user' ? '4px' : '16px',
              borderTopLeftRadius: msg.role === 'user' ? '16px' : '4px',
              maxWidth: '80%',
              border: msg.role === 'assistant' ? '1px solid var(--glass-border)' : 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
            }}>
              <p style={{ color: 'white', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{msg.text}</p>
              {msg.confidence && (
                <div style={{ 
                  display: 'flex', alignItems: 'center', gap: '6px', 
                  marginTop: '12px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.1)',
                  fontSize: '0.85rem', color: 'var(--text-secondary)'
                }}>
                  <ShieldCheck size={14} color="#10b981" />
                  Critic Confidence: {Math.round(msg.confidence * 100)}%
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '50%' }}>
              <Bot size={20} color="var(--accent-primary)" />
            </div>
            <div style={{ background: 'rgba(15,23,42,0.6)', padding: '1rem', borderRadius: '16px', borderTopLeftRadius: '4px' }}>
              <p style={{ color: 'var(--accent-primary)', animation: 'pulse 1.5s infinite', opacity: 0.7 }}>Agent is thinking...</p>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '10px' }}>
        <input 
          type="text" 
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask a question..."
          style={{ marginBottom: 0, flex: 1 }}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()} style={{ width: 'auto', padding: '0 1.5rem' }}>
          <Send size={18} />
        </button>
      </form>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes pulse { 50% { opacity: 1; } }
      `}} />
    </div>
  );
}
