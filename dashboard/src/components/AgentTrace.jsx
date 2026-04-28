import React from 'react';
import { BrainCircuit, Database, Cpu, SearchCheck, CheckCircle2 } from 'lucide-react';

export default function AgentTrace({ traceState, metrics }) {
  const steps = [
    { id: 'analysing', label: 'Query Analyser Core', icon: <BrainCircuit size={20} /> },
    { id: 'retrieving', label: 'ChromaDB Vector Retrieval', icon: <Database size={20} /> },
    { id: 'synthesising', label: 'Groq Llama-3 Synthesiser', icon: <Cpu size={20} /> },
    { id: 'evaluating', label: 'Algorithmic Critic', icon: <SearchCheck size={20} /> },
  ];

  const getStatus = (stepId, index) => {
    const states = ['idle', 'analysing', 'retrieving', 'synthesising', 'evaluating', 'completed'];
    const currentIndex = states.indexOf(traceState);
    const stepIndex = states.indexOf(stepId);
    
    if (currentIndex > stepIndex) return 'completed';
    if (currentIndex === stepIndex) return 'active';
    return 'idle';
  };

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h3 style={{ marginBottom: '2.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--text-primary)' }}>
        <BrainCircuit size={24} color="var(--accent-neon)" /> LangGraph Telemetry
      </h3>
      
      <div className="trace-container" style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
        {steps.map((step, index) => {
          const status = getStatus(step.id, index);
          return (
            <React.Fragment key={step.id}>
              <div className={`agent-node ${status}`}>
                <div style={{ 
                  color: status === 'active' ? 'var(--accent-neon)' : status === 'completed' ? '#10b981' : 'var(--text-secondary)'
                }}>
                  {step.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: status !== 'idle' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                    {step.label}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    {status === 'active' ? 'Processing...' : status === 'completed' ? 'Executed' : 'Standby'}
                  </div>
                </div>
                {status === 'completed' && <CheckCircle2 size={18} color="#10b981" />}
              </div>
              
              {index < steps.length - 1 && (
                <div className={`flow-line ${getStatus(steps[index + 1].id, index + 1) !== 'idle' ? 'active' : ''}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {(metrics.confidence || metrics.chunks) && (
        <div style={{ marginTop: 'auto', borderTop: '1px solid var(--glass-border)', paddingTop: '1.5rem' }}>
          <h4 style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1.5px' }}>Execution Metrics</h4>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {metrics.confidence && (
              <div className="metric-pill">
                Critic Confidence: {metrics.confidence * 100}%
              </div>
            )}
            {metrics.chunks && (
              <div className="metric-pill" style={{ color: 'var(--accent-primary)', borderColor: 'rgba(14, 165, 233, 0.3)', background: 'rgba(14, 165, 233, 0.1)' }}>
                {metrics.chunks} Vectors Fetched
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
