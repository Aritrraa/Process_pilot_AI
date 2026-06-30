import { useState, useRef, useEffect } from 'react';
import DOMPurify from 'dompurify';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { useLocation } from 'react-router-dom';
import { Send, Zap, ChevronDown, ChevronRight, Cpu, FileText, AlertCircle, Trash2 } from 'lucide-react';

const suggestions = [
  "What is the incident response procedure for P1 outages?",
  "How do we deploy FastAPI to Kubernetes?",
  "Summarize the new employee onboarding checklist",
  "What is our data privacy policy for GDPR compliance?",
  "How to conduct a security audit?",
  "What is the leave and PTO policy?",
];

function renderMarkdown(text) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let listBuffer = [];

  const flushList = () => {
    if (listBuffer.length > 0) {
      elements.push(<ul key={`ul-${elements.length}`} style={{ margin: '6px 0 6px 18px' }}>{listBuffer}</ul>);
      listBuffer = [];
    }
  };

  lines.forEach((line, i) => {
    if (line.startsWith('### ')) { flushList(); elements.push(<h3 key={i} style={{ fontSize: 14, fontWeight: 600, margin: '10px 0 5px' }}>{line.slice(4)}</h3>); return; }
    if (line.startsWith('## ')) { flushList(); elements.push(<h2 key={i} style={{ fontSize: 15, fontWeight: 700, margin: '12px 0 5px' }}>{line.slice(3)}</h2>); return; }
    if (line.startsWith('# ')) { flushList(); elements.push(<h1 key={i} style={{ fontSize: 17, fontWeight: 700, margin: '12px 0 6px' }}>{line.slice(2)}</h1>); return; }
    if (line.startsWith('- ') || line.startsWith('* ')) {
      listBuffer.push(<li key={i} style={{ marginBottom: 2 }}>{renderInline(line.slice(2))}</li>);
      return;
    }
    if (/^\d+\.\s/.test(line)) {
      flushList();
      elements.push(<div key={i} style={{ paddingLeft: 18, marginBottom: 3 }}>{renderInline(line)}</div>);
      return;
    }
    if (line.startsWith('---') || line.startsWith('===')) { flushList(); elements.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid var(--border-subtle)', margin: '10px 0' }} />); return; }
    if (line.trim() === '') { flushList(); elements.push(<div key={i} style={{ height: 6 }} />); return; }
    flushList();
    elements.push(<p key={i} style={{ marginBottom: 4 }}>{renderInline(line)}</p>);
  });
  flushList();
  return elements;
}

function renderInline(text) {
  if (!text) return null;
  // Sanitize input to prevent XSS — strip all HTML tags
  const clean = DOMPurify.sanitize(text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
  const parts = clean.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('`') && part.endsWith('`')) return <code key={i} style={{ background: 'var(--bg-overlay)', padding: '1px 5px', borderRadius: 3, fontSize: '0.9em', fontFamily: 'monospace', color: 'var(--color-info)' }}>{part.slice(1, -1)}</code>;
    return part;
  });
}

export default function Chat() {
  const { user } = useAuth();
  const location = useLocation();
  const [activeScope, setActiveScope] = useState(location.state?.scopedNodeIds || null);
  const [messages, setMessages] = useState(() => {
    if (user?.id) {
      const stored = localStorage.getItem(`chat_history_${user.id}`);
      return stored ? JSON.parse(stored) : [];
    }
    return [];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState(null);
  const bottomRef = useRef();
  const inputRef = useRef();

  // Load chat history when user changes
  useEffect(() => {
    if (user?.id) {
      const stored = localStorage.getItem(`chat_history_${user.id}`);
      setMessages(stored ? JSON.parse(stored) : []);
    } else {
      setMessages([]);
    }
  }, [user?.id]);

  // Save chat history to localStorage when messages change
  useEffect(() => {
    if (user && messages.length > 0) {
      localStorage.setItem(`chat_history_${user.id}`, JSON.stringify(messages));
    } else if (user && messages.length === 0) {
      localStorage.removeItem(`chat_history_${user.id}`);
    }
  }, [messages, user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => {});
  }, []);

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setLoading(true);
    
    // Add an empty AI message placeholder
    setMessages(prev => [...prev, {
      role: 'ai',
      content: '',
      sources: [],
      incidents: [],
      steps: [],
      showSteps: false,
    }]);

    try {
      const token = localStorage.getItem('token');
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
      const res = await fetch(`${baseUrl}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: msg, scope: activeScope, stream: true })
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunkStr = decoder.decode(value, { stream: true });
        const lines = chunkStr.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'metadata') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].sources = data.sources || [];
                  newMsgs[newMsgs.length - 1].incidents = data.incidents || [];
                  newMsgs[newMsgs.length - 1].steps = data.steps || [];
                  return newMsgs;
                });
              } else if (data.type === 'chunk') {
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content += data.content;
                  return newMsgs;
                });
              } else if (data.type === 'done') {
                // Done
              }
            } catch (e) {
              console.warn("Error parsing chunk", dataStr);
            }
          }
        }
      }
    } catch (err) {
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1].content = `**Error:** ${err.message}. Please check that the backend server is running.`;
        newMsgs[newMsgs.length - 1].isError = true;
        return newMsgs;
      });
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const toggleSteps = (idx) => {
    setMessages(prev => prev.map((m, i) => i === idx ? { ...m, showSteps: !m.showSteps } : m));
  };

  const activeProvider = settings?.llm_provider || 'simulation';
  const providerLabels = { gemini: 'Gemini AI', groq: 'Groq Llama-3', openai: 'OpenAI GPT', simulation: 'Simulation' };

  return (
    <div className="chat-container">
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 30px 14px 30px', borderBottom: '1px solid var(--border-subtle)', marginBottom: 4 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>AI Copilot</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Multi-agent RAG pipeline · Source-cited answers</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className={`badge ${activeProvider === 'simulation' ? 'badge-neutral' : 'badge-green'}`}>
            <Cpu size={9} /> {providerLabels[activeProvider]}
          </span>
          {messages.length > 0 && (
            <button
              className="btn btn-ghost btn-xs"
              onClick={() => { setMessages([]); localStorage.removeItem(`chat_history_${user?.id}`); }}
              title="Clear chat history"
              style={{ color: 'var(--color-danger)', padding: '4px 8px' }}
            >
              <Trash2 size={12} /> Clear
            </button>
          )}
        </div>
      </div>

      {activeScope && activeScope.length > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: 'var(--accent-subtle)',
          border: '1px solid var(--color-blue)',
          margin: '10px 30px 12px 30px',
          borderRadius: '4px',
          fontSize: 12
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-blue)' }}>
            <Cpu size={12} />
            <span><strong>Active Context Scope:</strong> Scoped to {activeScope.length} node{activeScope.length > 1 ? 's' : ''} ({activeScope.join(', ')})</span>
          </div>
          <button
            className="btn btn-ghost btn-xs"
            onClick={() => setActiveScope(null)}
            style={{ padding: 0, textTransform: 'none', fontSize: 11, fontWeight: 700 }}
          >
            Clear Filter
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <img 
              src="/copilot_brain.png" 
              alt="AI Copilot" 
              style={{ 
                width: 130, 
                height: 130, 
                objectFit: 'contain', 
                marginBottom: 12, 
                filter: 'drop-shadow(0 4px 20px rgba(255, 130, 53, 0.25))' 
              }} 
              className="fade-up"
            />
            <h2>ProcessPilot AI Copilot</h2>
            <p>
              Ask anything about your organization's documents, SOPs, deployments, policies, and incidents.
              The multi-agent system will search, analyze, and synthesize answers with source citations.
            </p>
            <div className="suggestions">
              {suggestions.map((s, i) => (
                <button key={i} className="suggestion-chip" onClick={() => sendMessage(s)}>{s}</button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="msg-avatar">
                  {msg.role === 'ai' ? <Zap size={14} /> : msg.role[0].toUpperCase()}
                </div>
                <div className="msg-body">
                  <div className={`msg-bubble ${msg.isError ? 'alert-danger' : ''}`}>
                    {msg.isError && <AlertCircle size={14} style={{ marginRight: 6, display: 'inline' }} />}
                    {renderMarkdown(msg.content)}
                  </div>

                  {/* Sources */}
                  {msg.sources?.length > 0 && (
                    <div className="sources-row">
                      {msg.sources.map((s, i) => (
                        <span key={i} className="source-pill">
                          <FileText size={9} /> {s}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Agent steps */}
                  {msg.steps?.length > 0 && (
                    <>
                      <div className="agent-toggle" onClick={() => toggleSteps(idx)}>
                        {msg.showSteps ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                        Agent pipeline · {msg.steps.length} steps
                      </div>
                      {msg.showSteps && (
                        <div className="agent-steps-panel">
                          {msg.steps.map((step, si) => (
                            <div key={si} className="agent-step">
                              <span className="step-name">{step.agent}</span>
                              <span className="step-action">{step.action}</span>
                              <span className="step-result">{step.result}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message ai">
                <div className="msg-avatar"><Zap size={14} /></div>
                <div className="msg-body">
                  <div className="msg-bubble">
                    <div className="typing-dots"><span /><span /><span /></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <div className="chat-input-row">
          <div className="chat-input-wrap">
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Ask about your documents, SOPs, policies, incidents…"
              disabled={loading}
            />
            <button
              className="chat-send-btn"
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
            >
              <Send size={15} />
            </button>
          </div>
        </div>
        <div className="chat-hint">Press Enter to send · Shift+Enter for new line</div>
      </div>
    </div>
  );
}
