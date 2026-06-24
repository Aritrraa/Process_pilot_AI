import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, Navigate } from 'react-router-dom';
import { Compass, ArrowRight } from 'lucide-react';

const features = [
  'Multi-agent AI that searches, analyzes, and synthesizes knowledge',
  'RAG-powered document retrieval with source citations',
  'Meeting transcript analysis and action item extraction',
  'Knowledge graph for organization-wide insights',
];

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (role) => {
    const creds = {
      admin: { email: 'admin@processpilot.ai', password: 'admin123' },
      employee: { email: 'john@processpilot.ai', password: 'john123' },
      manager: { email: 'sarah@processpilot.ai', password: 'sarah123' },
    };
    setEmail(creds[role].email);
    setPassword(creds[role].password);
  };

  return (
    <div className="auth-page">
      {/* Left panel */}
      <div className="auth-left">
        <Link to="/" className="auth-left-logo" style={{ textDecoration: 'none' }}>
          <div className="logo-mark">
            <Compass size={18} color="white" />
          </div>
          <span>Process Pilot</span>
        </Link>
        <div className="auth-left-tagline">
          <h2>Enterprise Knowledge<br />at your fingertips</h2>
          <p>
            ProcessPilot is an AI-powered knowledge operating system that makes your
            organization's documents, SOPs, and institutional knowledge instantly accessible.
          </p>
          <div className="auth-features">
            {features.map((f, i) => (
              <div key={i} className="auth-feature">
                <div className="auth-feature-dot" />
                {f}
              </div>
            ))}
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          100% free tier stack · Open source ready
        </div>
      </div>

      {/* Right panel */}
      <div className="auth-right">
        <div className="auth-form-wrap">
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28, textDecoration: 'none' }}>
            <div className="logo-mark" style={{ width: 28, height: 28 }}>
              <Compass size={14} color="white" />
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Process Pilot</span>
          </Link>

          <div className="auth-title">Sign in</div>
          <div className="auth-subtitle">Welcome back. Enter your credentials to continue.</div>

          {error && <div className="error-msg">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email address</label>
              <input
                className="form-input"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                className="form-input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            <button
              className="btn btn-primary w-full"
              type="submit"
              disabled={loading}
              style={{ justifyContent: 'center', width: '100%', padding: '10px 16px' }}
            >
              {loading ? <><span className="spinner-sm" style={{ borderTopColor: 'white' }} /> Signing in…</> : <>Sign in <ArrowRight size={15} /></>}
            </button>
          </form>

          <div style={{ margin: '20px 0', display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ flex: 1, height: 1, background: 'var(--border-subtle)' }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Demo accounts</span>
            <div style={{ flex: 1, height: 1, background: 'var(--border-subtle)' }} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {[
              { role: 'admin', label: 'Admin', badge: 'badge-blue' },
              { role: 'manager', label: 'Manager', badge: 'badge-purple' },
              { role: 'employee', label: 'Employee', badge: 'badge-neutral' },
            ].map(d => (
              <button
                key={d.role}
                className="btn btn-secondary"
                style={{ justifyContent: 'center', fontSize: 12 }}
                onClick={() => fillDemo(d.role)}
                type="button"
              >
                {d.label}
              </button>
            ))}
          </div>

          <div className="auth-footer" style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
            <div>No account? <Link to="/register">Create one</Link></div>
            <div style={{ fontSize: 11 }}><Link to="/">← Return to starting page</Link></div>
          </div>
        </div>
      </div>
    </div>
  );
}
