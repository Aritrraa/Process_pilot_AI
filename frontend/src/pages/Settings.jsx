import { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { Save, Eye, EyeOff, Key, User, CheckCircle2, ExternalLink, Info } from 'lucide-react';

const PROVIDERS = [
  {
    id: 'simulation',
    name: 'Simulation',
    desc: 'Offline mock mode',
    badge: 'badge-neutral',
    info: 'Runs locally, no API key required. Generates structured mock responses to demonstrate the system.',
    link: null,
  },
  {
    id: 'gemini',
    name: 'Gemini',
    desc: 'Google AI (free tier)',
    badge: 'badge-blue',
    info: 'Google Gemini 1.5 Flash. Generous free tier — 1,500 requests/day.',
    link: 'https://ai.google.dev',
    linkText: 'ai.google.dev',
  },
  {
    id: 'groq',
    name: 'Groq',
    desc: 'Llama-3 (fastest)',
    badge: 'badge-purple',
    info: 'Blazing fast inference. Llama-3.1 70B. Free tier available.',
    link: 'https://console.groq.com',
    linkText: 'console.groq.com',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    desc: 'GPT-4o-mini',
    badge: 'badge-green',
    info: 'OpenAI GPT-4o-mini. Pay-per-use. Most capable for complex reasoning.',
    link: 'https://platform.openai.com',
    linkText: 'platform.openai.com',
  },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const [geminiKey, setGeminiKey] = useState('');
  const [groqKey, setGroqKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [llmProvider, setLlmProvider] = useState('simulation');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [showKeys, setShowKeys] = useState({ gemini: false, groq: false, openai: false });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings()
      .then(s => {
        setGeminiKey(s.gemini_api_key || '');
        setGroqKey(s.groq_api_key || '');
        setOpenaiKey(s.openai_api_key || '');
        setLlmProvider(s.llm_provider || 'simulation');
        setSystemPrompt(s.system_prompt || '');
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.updateSettings(geminiKey, groqKey, openaiKey, llmProvider, systemPrompt);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const toggleKey = (provider) => setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }));

  const activeProvider = PROVIDERS.find(p => p.id === llmProvider);

  if (loading) return <div className="spinner" />;

  const keyFields = [
    { id: 'gemini', label: 'Gemini API Key', value: geminiKey, onChange: setGeminiKey, show: showKeys.gemini },
    { id: 'groq', label: 'Groq API Key', value: groqKey, onChange: setGroqKey, show: showKeys.groq },
    { id: 'openai', label: 'OpenAI API Key', value: openaiKey, onChange: setOpenaiKey, show: showKeys.openai },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Configure your AI provider and system preferences</p>
      </div>

      <div className="settings-grid">
        {/* Left: AI Config */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Provider selection */}
          <div className="card">
            <div className="card-header">
              <div className="card-title"><Key size={15} /> AI Provider</div>
              <span className={`badge ${activeProvider?.badge}`}>
                {activeProvider?.name} active
              </span>
            </div>

            <div className="provider-selector">
              {PROVIDERS.map(p => (
                <div
                  key={p.id}
                  className={`provider-option ${llmProvider === p.id ? 'selected' : ''}`}
                  onClick={() => setLlmProvider(p.id)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <div className="provider-option-name">{p.name}</div>
                    {llmProvider === p.id && <CheckCircle2 size={13} color="var(--accent)" />}
                  </div>
                  <div className="provider-option-desc">{p.desc}</div>
                </div>
              ))}
            </div>

            {activeProvider && (
              <div className="alert alert-info" style={{ fontSize: 12 }}>
                <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
                <div>
                  {activeProvider.info}
                  {activeProvider.link && (
                    <> Get your key at <a href={activeProvider.link} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-info)', display: 'inline-flex', alignItems: 'center', gap: 3 }}>{activeProvider.linkText} <ExternalLink size={10} /></a></>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* API Keys */}
          <div className="card">
            <div className="card-header">
              <div className="card-title"><Key size={15} /> API Keys</div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Stored securely in your database</span>
            </div>
            {keyFields.map(kf => (
              <div key={kf.id} className="form-group">
                <label className="form-label">
                  {kf.label}
                  {llmProvider === kf.id && <span style={{ marginLeft: 6, color: 'var(--accent)', fontSize: 10 }}>● Active</span>}
                </label>
                <div className="password-wrapper">
                  <input
                    className="form-input"
                    type={kf.show ? 'text' : 'password'}
                    value={kf.value}
                    onChange={e => kf.onChange(e.target.value)}
                    placeholder={`Enter your ${kf.label}`}
                  />
                  <button className="toggle-pw" onClick={() => toggleKey(kf.id)} type="button">
                    {kf.show ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* System prompt */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Custom System Prompt</div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Optional</span>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <textarea
                className="form-textarea"
                value={systemPrompt}
                onChange={e => setSystemPrompt(e.target.value)}
                placeholder="Customize how the AI Copilot behaves. E.g. 'You are ProcessPilot, an enterprise assistant specialized in our internal policies and engineering procedures. Always cite the source document.'"
                style={{ minHeight: 120 }}
              />
              <div className="form-hint">Leave blank to use the default system prompt.</div>
            </div>
          </div>

          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
            style={{ alignSelf: 'flex-start' }}
          >
            {saving
              ? <><span className="spinner-sm" style={{ borderTopColor: 'white' }} /> Saving…</>
              : saved
                ? <><CheckCircle2 size={14} /> Saved!</>
                : <><Save size={14} /> Save Settings</>
            }
          </button>
        </div>

        {/* Right: Profile */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <div className="card-title"><User size={15} /> Account</div>
            </div>
            <div className="profile-section">
              <div className="profile-field">
                <div className="profile-field-label">Email</div>
                <div className="profile-field-value">{user?.email}</div>
              </div>
              <div className="profile-field">
                <div className="profile-field-label">Role</div>
                <div style={{ marginTop: 4 }}>
                  <span className={`badge ${user?.role === 'Admin' ? 'badge-blue' : user?.role === 'Manager' ? 'badge-purple' : 'badge-neutral'}`}>
                    {user?.role}
                  </span>
                </div>
              </div>
              <div className="profile-field">
                <div className="profile-field-label">Member Since</div>
                <div className="profile-field-value">
                  {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A'}
                </div>
              </div>
            </div>
          </div>

          {/* System info */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">System Info</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12 }}>
              {[
                { label: 'Backend', value: 'FastAPI + SQLite' },
                { label: 'Vector DB', value: 'ChromaDB (local)' },
                { label: 'Embeddings', value: 'sentence-transformers' },
                { label: 'Agent Framework', value: 'Multi-agent RAG' },
                { label: 'Knowledge Graph', value: 'NetworkX' },
              ].map(item => (
                <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{item.label}</span>
                  <span className="chip">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
