import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Sidebar from './Sidebar';
import { useState, useEffect } from 'react';
import { api } from '../api';
import { Zap, LogOut } from 'lucide-react';

export default function Layout() {
  const { user, setUser, logout, loading } = useAuth();
  const [managers, setManagers] = useState([]);
  const [selectedManager, setSelectedManager] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (user && user.role === 'Employee' && !user.manager_id) {
      api.getManagers().then(setManagers).catch(() => {});
    }
  }, [user]);

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}><div className="spinner" /></div>;
  if (!user) return <Navigate to="/login" replace />;

  const handleSelectManager = async (e) => {
    e.preventDefault();
    if (!selectedManager) return;
    setSubmitting(true);
    setError('');
    try {
      const updatedUser = await api.selectManager(parseInt(selectedManager));
      setUser(updatedUser);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  // Lockout screen if Employee is released / has no manager
  if (user.role === 'Employee' && !user.manager_id) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-app)',
        padding: '20px'
      }}>
        <div className="card fade-up" style={{ maxWidth: '400px', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <div className="logo-mark" style={{ width: 28, height: 28 }}>
              <Zap size={14} color="white" />
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>ProcessPilot AI</span>
          </div>

          <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8, letterSpacing: '-0.02em' }}>
            Select Team Supervisor
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.5 }}>
            You have been released from your previous team. Please select your new Manager / HR Supervisor to activate your workspace.
          </p>

          {error && <div className="error-msg" style={{ marginBottom: 16 }}>{error}</div>}

          <form onSubmit={handleSelectManager}>
            <div className="form-group">
              <label className="form-label">Active Managers *</label>
              <select
                className="form-select"
                value={selectedManager}
                onChange={e => setSelectedManager(e.target.value)}
                required
              >
                <option value="" disabled hidden>Select your new manager...</option>
                {managers.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.full_name || m.email} ({m.email})
                  </option>
                ))}
              </select>
            </div>

            <button
              className="btn btn-primary w-full"
              type="submit"
              disabled={submitting || !selectedManager}
              style={{ justifyContent: 'center', width: '100%', padding: '10px 16px', marginTop: 10 }}
            >
              {submitting ? <><span className="spinner-sm" style={{ borderTopColor: 'white' }} /> Joining Team…</> : 'Join Team'}
            </button>
          </form>

          <div style={{ margin: '20px 0', height: 1, background: 'var(--border-subtle)' }} />

          <button
            className="btn btn-secondary w-full"
            onClick={logout}
            style={{ justifyContent: 'center', width: '100%', display: 'flex', gap: 8 }}
          >
            <LogOut size={14} /> Log out
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
