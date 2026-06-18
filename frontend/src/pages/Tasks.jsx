import { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { Plus, CheckCircle2, Clock, CircleDot, Trash2, Calendar } from 'lucide-react';

const STATUS = {
  Pending: { badge: 'badge-neutral', icon: Clock, next: 'In_Progress', nextLabel: 'Start' },
  In_Progress: { badge: 'badge-blue', icon: CircleDot, next: 'Completed', nextLabel: 'Complete' },
  Completed: { badge: 'badge-green', icon: CheckCircle2, next: 'Pending', nextLabel: 'Reopen' },
};

export default function Tasks() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [assignedTo, setAssignedTo] = useState('');
  const [team, setTeam] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const load = () => api.getTasks().then(setTasks).catch(() => {}).finally(() => setLoading(false));
  
  useEffect(() => {
    load();
    if (user && (user.role === 'Admin' || user.role === 'Manager')) {
      api.getTeam().then(setTeam).catch(() => {});
    }
  }, [user]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await api.createTask(title, desc, assignedTo ? parseInt(assignedTo) : null);
      setTitle(''); setDesc(''); setAssignedTo(''); setShowForm(false);
      load();
    } catch (err) { alert(err.message); }
    finally { setSubmitting(false); }
  };

  const cycleStatus = async (task) => {
    const next = STATUS[task.status]?.next || 'Pending';
    try {
      await api.updateTask(task.id, next);
      setTasks(prev => prev.map(t => t.id === task.id ? { ...t, status: next } : t));
    } catch (err) { alert(err.message); }
  };

  const safeTasks = Array.isArray(tasks) ? tasks : [];
  const grouped = {
    Pending: safeTasks.filter(t => t && t.status === 'Pending'),
    In_Progress: safeTasks.filter(t => t && t.status === 'In_Progress'),
    Completed: safeTasks.filter(t => t && t.status === 'Completed'),
  };

  const colHeaders = {
    Pending: { label: 'To Do', color: 'var(--text-muted)' },
    In_Progress: { label: 'In Progress', color: 'var(--accent)' },
    Completed: { label: 'Done', color: 'var(--color-success)' },
  };

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header">
          <h1>Tasks</h1>
          <p>Track action items from meetings, documents, and AI analysis</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <Plus size={14} /> New Task
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <div className="card-title">Create Task</div>
            <button className="btn btn-ghost btn-xs" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label className="form-label">Title *</label>
              <input
                className="form-input"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Update Kubernetes deployment manifest"
                required
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Description <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(optional)</span></label>
              <textarea
                className="form-textarea"
                value={desc}
                onChange={e => setDesc(e.target.value)}
                placeholder="Additional context, acceptance criteria, links…"
                style={{ minHeight: 80 }}
              />
            </div>
            {(user?.role === 'Admin' || user?.role === 'Manager') && (
              <div className="form-group" style={{ marginTop: 14 }}>
                <label className="form-label">Assign To</label>
                <select className="form-select" value={assignedTo} onChange={e => setAssignedTo(e.target.value)}>
                  <option value="">Assign to Self</option>
                  {team.map(member => (
                    <option key={member.id} value={member.id}>
                      {member.full_name || member.email} ({member.role})
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div style={{ marginTop: 14 }}>
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting ? <><span className="spinner-sm" style={{ borderTopColor: 'white' }} /> Creating…</> : 'Create Task'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Summary */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        {Object.entries(grouped).map(([status, items]) => (
          <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
            <span className={`badge ${STATUS[status].badge}`}>{items.length}</span>
            {colHeaders[status].label}
          </div>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
          Click a task to advance its status →
        </div>
      </div>

      {loading ? <div className="spinner" /> : (
        <div className="kanban-grid">
          {Object.entries(grouped).map(([status, items]) => {
            const { label, color } = colHeaders[status];
            const cfg = STATUS[status];
            return (
              <div key={status} className="kanban-col">
                <div className="kanban-col-header">
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
                  <span>{label}</span>
                  <span className={`badge ${cfg.badge} kanban-count`}>{items.length}</span>
                </div>
                <div className="kanban-body">
                  {items.length === 0 && (
                    <div className="kanban-empty">No tasks here</div>
                  )}
                  {items.map(task => (
                    <div
                      key={task.id}
                      className="kanban-card"
                      onClick={() => cycleStatus(task)}
                      title={`Click to move to "${cfg.next.replace('_', ' ')}"`}
                    >
                      <div className="kanban-card-title">{task.title}</div>
                      {task.description && (
                        <div className="kanban-card-desc">{task.description}</div>
                      )}
                      {user && (user.role === 'Admin' || user.role === 'Manager') ? (
                        <div style={{ marginBottom: 6 }} onClick={e => e.stopPropagation()}>
                          <select
                            value={task.assigned_to || ''}
                            onChange={async (e) => {
                              const newAssignee = e.target.value ? parseInt(e.target.value) : null;
                              try {
                                await api.updateTask(task.id, null, newAssignee);
                                load();
                              } catch (err) { alert(err.message); }
                            }}
                            className="form-select"
                            style={{ padding: '2px 4px', fontSize: 10, height: 'auto', width: '100%', background: 'var(--bg-overlay)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
                          >
                            <option value="">Unassigned</option>
                            {team.map(member => (
                              <option key={member.id} value={member.id}>
                                Assignee: {member.full_name || member.email} ({member.role})
                              </option>
                            ))}
                          </select>
                        </div>
                      ) : (
                        task.assignee_name && (
                          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                            <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#2563eb', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 7, fontWeight: 'bold' }}>
                              {task.assignee_name[0].toUpperCase()}
                            </span>
                            <span>Assigned to: {task.assignee_name}</span>
                          </div>
                        )
                      )}
                      <div className="kanban-card-footer">
                        <span className="kanban-card-date">
                          <Calendar size={9} style={{ display: 'inline', marginRight: 3 }} />
                          {new Date(task.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                        <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 500 }}>
                          → {cfg.nextLabel}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
