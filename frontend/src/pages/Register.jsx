import { useState, useEffect } from 'react';
import { api } from '../api';
import { Link, useNavigate } from 'react-router-dom';
import { Zap, ArrowRight } from 'lucide-react';

export default function Register() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('');
  const [deptId, setDeptId] = useState('');
  const [managerId, setManagerId] = useState('');
  const [departments, setDepartments] = useState([]);
  const [managers, setManagers] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.getDepartments().then(setDepartments).catch(() => {});
    api.getManagers().then(setManagers).catch(() => {});
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.register(
        email,
        password,
        fullName || null,
        role,
        deptId ? parseInt(deptId) : null,
        (role !== 'Admin' && managerId) ? parseInt(managerId) : null
      );
      navigate('/login');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Left panel */}
      <div className="auth-left">
        <div className="auth-left-logo">
          <div className="logo-mark">
            <Zap size={18} color="white" />
          </div>
          <span>ProcessPilot AI</span>
        </div>
        <div className="auth-left-tagline">
          <h2>Enterprise Knowledge<br />at your fingertips</h2>
          <p>
            ProcessPilot is an AI-powered knowledge operating system that makes your
            organization's documents, SOPs, and institutional knowledge instantly accessible.
          </p>
          <div className="auth-features">
            {[
              'Multi-agent AI that searches, analyzes, and synthesizes knowledge',
              'RAG-powered document retrieval with source citations',
              'Meeting transcript analysis and action item extraction',
              'Knowledge graph for organization-wide insights',
            ].map((f, i) => (
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
        <div className="auth-form-wrap" style={{ maxWidth: 400 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
            <div className="logo-mark" style={{ width: 28, height: 28 }}>
              <Zap size={14} color="white" />
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>ProcessPilot AI</span>
          </div>

          <div className="auth-title">Create account</div>
          <div className="auth-subtitle">Join your organization's knowledge engine.</div>

          {error && <div className="error-msg">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                className="form-input"
                type="text"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="John Doe"
                required
              />
            </div>
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
                placeholder="At least 6 characters"
                required
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Role *</label>
                <select className="form-select" value={role} onChange={e => setRole(e.target.value)} required>
                  <option value="" disabled hidden>Select Role</option>
                  <option value="Employee">Employee</option>
                  <option value="Manager">Manager</option>
                  <option value="Admin">Admin</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Department *</label>
                <select className="form-select" value={deptId} onChange={e => setDeptId(e.target.value)} required>
                  <option value="" disabled hidden>Select Dept</option>
                  {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
            </div>
            {role && role !== 'Admin' && (
              <div className="form-group">
                <label className="form-label">Manager / HR Supervisor *</label>
                <select className="form-select" value={managerId} onChange={e => setManagerId(e.target.value)} required>
                  <option value="" disabled hidden>Select Supervisor</option>
                  {managers.map(m => (
                    <option key={m.id} value={m.id}>
                      {m.full_name || m.email} ({m.email})
                    </option>
                  ))}
                </select>
              </div>
            )}
            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading}
              style={{ justifyContent: 'center', width: '100%', padding: '10px 16px' }}
            >
              {loading
                ? <><span className="spinner-sm" style={{ borderTopColor: 'white' }} /> Creating…</>
                : <>Create account <ArrowRight size={15} /></>
              }
            </button>
          </form>

          <div className="auth-footer">
            Have an account? <Link to="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
