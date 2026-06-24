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
  const [searchQuery, setSearchQuery] = useState('');

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
  const filteredTasks = safeTasks.filter(t => {
    if (!t) return false;
    const query = searchQuery.toLowerCase();
    const titleMatch = t.title ? t.title.toLowerCase().includes(query) : false;
    const descMatch = t.description ? t.description.toLowerCase().includes(query) : false;
    const assigneeMatch = t.assignee_name ? t.assignee_name.toLowerCase().includes(query) : false;
    return titleMatch || descMatch || assigneeMatch;
  });

  const grouped = {
    Pending: filteredTasks.filter(t => t.status === 'Pending'),
    In_Progress: filteredTasks.filter(t => t.status === 'In_Progress'),
    Completed: filteredTasks.filter(t => t.status === 'Completed'),
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

      {/* Search filter bar */}
      <div style={{ marginBottom: 20 }}>
        <input
          className="form-input"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search tasks by title, description, or assignee..."
          style={{ maxWidth: 400 }}
        />
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
        <div className="kanban-board">
          {Object.entries(grouped).map(([status, items]) => {
            const { label, color } = colHeaders[status];
            const cfg = STATUS[status];
            return (
              <div key={status} className="kanban-column">
                <div className="kanban-column-header">
                  <div className="kanban-column-title">
                    <div style={{ width: 8, height: 8, background: color, flexShrink: 0 }} />
                    <span>{label}</span>
                  </div>
                  <span className="kanban-column-count">{items.length}</span>
                </div>
                <div className="kanban-cards">
                  {items.length === 0 && (
                    <div style={{ padding: '24px 0', textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace' }}>No tasks here</div>
                  )}
                  {items.map(task => (
                    <div
                      key={task.id}
                      className="task-card"
                      onClick={() => cycleStatus(task)}
                      title={`Click to move to "${cfg.next.replace('_', ' ')}"`}
                    >
                      <div className="task-card-title">{task.title}</div>
                      {task.description && (
                        <div className="task-card-desc">{task.description}</div>
                      )}
                      {user && (user.role === 'Admin' || user.role === 'Manager') ? (
                        <div style={{ marginBottom: 10 }} onClick={e => e.stopPropagation()}>
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
                            style={{ padding: '4px 8px', fontSize: 11, height: 'auto', width: '100%', background: 'var(--color-paper)', borderColor: 'var(--color-graphite)' }}
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
                          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'IBM Plex Mono, monospace' }}>
                            <span style={{ width: 14, height: 14, background: 'var(--color-petrol)', color: 'white', display: 'flex', alignItems: 'center', justifycontent: 'center', fontSize: 8, fontWeight: 'bold', justifyContent: 'center' }}>
                              {task.assignee_name[0].toUpperCase()}
                            </span>
                            <span>Assigned to: {task.assignee_name}</span>
                          </div>
                        )
                      )}
                      <div className="task-card-meta">
                        <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 10 }}>
                          <Calendar size={9} style={{ display: 'inline', marginRight: 3, verticalAlign: -1 }} />
                          {new Date(task.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                        <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 700, fontFamily: 'Archivo, sans-serif' }}>
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
