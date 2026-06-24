import { useState, useEffect } from 'react';
import { api } from '../api';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FileText, Users, CheckSquare, MessageSquare, Upload, Zap, TrendingUp, Clock, ArrowRight } from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    api.getAnalytics().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner" />;

  const stats = data?.stats || {};
  const health = data?.documentation_health || 0;
  const circumference = 2 * Math.PI * 40;
  const dashOffset = circumference - (health / 100) * circumference;

  const statCards = [
    { label: 'Documents', value: stats.total_documents || 0, icon: FileText, color: 'blue', desc: 'Indexed in vector DB' },
    { label: 'Team Members', value: stats.total_users || 0, icon: Users, color: 'purple', desc: 'Active accounts' },
    { label: 'Tasks', value: stats.total_tasks || 0, icon: CheckSquare, color: 'amber', desc: 'Action items tracked' },
    { label: 'AI Queries', value: stats.total_searches || 0, icon: MessageSquare, color: 'cyan', desc: 'Knowledge searches' },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Command Center</h1>
        <p>
          {user?.email ? (
            <>
              <strong>{user.email.split('@')[0].charAt(0).toUpperCase() + user.email.split('@')[0].slice(1)}</strong>, here's your organization's knowledge intelligence.
            </>
          ) : (
            "Here's your organization's knowledge intelligence."
          )}
        </p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        {statCards.map(s => (
          <div key={s.label} className="stat-card">
            <div className={`stat-card-icon ${s.color}`}>
              <s.icon size={18} />
            </div>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{s.desc}</div>
          </div>
        ))}
      </div>

      {/* Main row */}
      <div className="grid-2" style={{ marginBottom: 16 }}>
        {/* Documentation health */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <TrendingUp size={15} />
              Documentation Health
            </div>
            <span className={`badge ${health >= 70 ? 'badge-green' : health >= 40 ? 'badge-amber' : 'badge-red'}`}>
              {health >= 70 ? 'Good' : health >= 40 ? 'Fair' : 'Needs Work'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <div className="health-ring">
              <svg width="100" height="100" viewBox="0 0 100 100">
                <circle className="circle-bg" cx="50" cy="50" r="40" fill="none" />
                <circle
                  className="circle-fill"
                  cx="50" cy="50" r="40"
                  fill="none"
                  strokeDasharray={circumference}
                  strokeDashoffset={dashOffset}
                  style={{ stroke: health >= 70 ? 'var(--color-success)' : health >= 40 ? 'var(--color-warning)' : 'var(--color-danger)' }}
                />
              </svg>
              <div className="health-pct">{health}%</div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Based on AI query coverage vs documentation gaps. Upload more documents to improve your score.
              </div>
              <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} onClick={() => navigate('/documents')}>
                <Upload size={13} /> Upload docs
              </button>
            </div>
            <img 
              src="/earth_globe.png" 
              alt="Documentation Health" 
              style={{ 
                width: 80, 
                height: 80, 
                objectFit: 'contain', 
                opacity: 0.9,
                filter: 'drop-shadow(0 4px 15px rgba(255, 130, 53, 0.2))'
              }}
              className="health-card-globe"
            />
          </div>
        </div>

        {/* Recent AI Searches */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Zap size={15} />
              Recent AI Queries
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/analytics')} style={{ fontSize: 11 }}>
              View all <ArrowRight size={11} />
            </button>
          </div>
          {(data?.latest_searches || []).length === 0 ? (
            <div className="empty-state">
              <MessageSquare size={28} />
              <div>No queries yet — try the AI Copilot!</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {(data?.latest_searches || []).slice(0, 5).map((s, i) => (
                <div key={i} style={{ padding: '8px 0', borderBottom: i < 4 ? '1px solid var(--border-subtle)' : 'none' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-primary)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    "{s.query}"
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                    <Clock size={10} />
                    {s.user} · {s.timestamp}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Dept summary */}
      {(data?.department_activity || []).length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <div className="card-title"><Users size={15} /> Department Overview</div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Members</th>
                  <th>Documents</th>
                  <th>Coverage</th>
                </tr>
              </thead>
              <tbody>
                {data.department_activity.map((d, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{d.name}</td>
                    <td>{d.users}</td>
                    <td>{d.documents}</td>
                    <td>
                      <div style={{ width: 80, height: 4, background: 'var(--bg-overlay)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(100, d.documents * 20)}%`, background: 'var(--accent)', borderRadius: 2 }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div style={{ marginTop: 32 }}>
        <h3 style={{ fontSize: 14, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16, fontFamily: 'Libre Baskerville, serif', fontWeight: 700 }}>Quick Operations</h3>
        <div className="dashboard-actions-grid">
          <div className="action-tile-card" onClick={() => navigate('/documents')}>
            <div className="action-tile-icon blue">
              <Upload size={18} />
            </div>
            <div>
              <div className="action-tile-title">Upload Document</div>
              <div className="action-tile-desc">Add PDFs, DOCX, CSVs, or text files to the repository.</div>
            </div>
            <div className="action-tile-footer">
              <span>Go to files</span> <ArrowRight size={12} />
            </div>
          </div>

          <div className="action-tile-card" onClick={() => navigate('/chat')}>
            <div className="action-tile-icon purple">
              <Zap size={18} />
            </div>
            <div>
              <div className="action-tile-title">AI Copilot</div>
              <div className="action-tile-desc">Query knowledge bases, audit tasks, and interact with the AI assistant.</div>
            </div>
            <div className="action-tile-footer">
              <span>Start session</span> <ArrowRight size={12} />
            </div>
          </div>

          <div className="action-tile-card" onClick={() => navigate('/meetings')}>
            <div className="action-tile-icon green">
              <Users size={18} />
            </div>
            <div>
              <div className="action-tile-title">New Meeting</div>
              <div className="action-tile-desc">Process transcripts to extract key summaries and action items.</div>
            </div>
            <div className="action-tile-footer">
              <span>Analyze meeting</span> <ArrowRight size={12} />
            </div>
          </div>

          <div className="action-tile-card" onClick={() => navigate('/tasks')}>
            <div className="action-tile-icon amber">
              <CheckSquare size={18} />
            </div>
            <div>
              <div className="action-tile-title">Create Task</div>
              <div className="action-tile-desc">Delegate tasks, track statuses, and check outstanding workloads.</div>
            </div>
            <div className="action-tile-footer">
              <span>Manage tasks</span> <ArrowRight size={12} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}
