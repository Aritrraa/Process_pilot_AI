import { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { BarChart3, TrendingUp, Search, Users, FileText, MessageSquare, CheckSquare, RefreshCw } from 'lucide-react';

export default function Analytics() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [managers, setManagers] = useState([]);
  const [expandedMembers, setExpandedMembers] = useState({});

  const toggleExpandMember = (memberId) => {
    setExpandedMembers(prev => ({
      ...prev,
      [memberId]: !prev[memberId]
    }));
  };

  const load = () => {
    setLoading(true);
    api.getAnalytics().then(setData).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    if (user && (user.role === 'Manager' || user.role === 'Admin')) {
      api.getManagers().then(setManagers).catch(() => {});
    }
  }, [user]);

  const handleTransfer = async (employeeId, managerId) => {
    const action = managerId ? 'transfer' : 'release';
    if (!confirm(`Are you sure you want to ${action} this employee?`)) return;
    try {
      await api.transferEmployee(employeeId, managerId);
      // Silent reload of analytics dashboard data
      api.getAnalytics().then(setData).catch(() => {});
    } catch (err) {
      alert(`Failed to ${action} employee: ${err.message}`);
    }
  };

  if (loading) return <div className="spinner" />;
  if (!data) return <div className="empty-state">Failed to load analytics data</div>;

  const barColors = ['#ff6b00', '#ff8524', '#ffa35c', '#ffd1b3', '#9fa6b2', '#626875'];
  const docTypes = Object.entries(data.docs_by_type || {});
  const maxDoc = Math.max(...docTypes.map(([, v]) => v), 1);

  const taskStatus = data.task_status || {};
  const totalTasks = (taskStatus.Completed || 0) + (taskStatus.Pending || 0) + (taskStatus.In_Progress || 0);

  const isManager = data.team_details?.role === 'Manager';
  const isAdmin = data.team_details?.role === 'Admin';

  const statCards = [
    { label: 'Total Documents', value: data.stats?.total_documents || 0, icon: FileText, color: 'blue' },
    { label: 'AI Queries', value: data.stats?.total_searches || 0, icon: MessageSquare, color: 'cyan' },
    { label: 'Doc Health', value: `${data.documentation_health || 0}%`, icon: TrendingUp, color: 'green' },
    { label: 'Total Tasks', value: data.stats?.total_tasks || 0, icon: CheckSquare, color: 'amber' },
  ];

  if (isAdmin) {
    statCards.push({
      label: 'Total Teams',
      value: data.team_details?.total_teams || 0,
      icon: Users,
      color: 'purple'
    });
    statCards.push({
      label: 'Team Members',
      value: data.team_details?.total_team_members || 0,
      icon: Users,
      color: 'pink'
    });
  } else if (isManager || data.team_details?.role === 'Employee') {
    statCards.push({
      label: 'Team Members',
      value: data.team_details?.team_size || 0,
      icon: Users,
      color: 'purple'
    });
  } else {
    statCards.push({
      label: 'Team Members',
      value: data.stats?.total_users || 0,
      icon: Users,
      color: 'purple'
    });
  }

  const taskItems = [
    { label: 'Completed', value: taskStatus.Completed || 0, color: 'var(--color-success)' },
    { label: 'In Progress', value: taskStatus.In_Progress || 0, color: 'var(--accent)' },
    { label: 'Pending', value: taskStatus.Pending || 0, color: 'var(--text-muted)' },
  ];

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header">
          <h1>Analytics</h1>
          <p>Knowledge base metrics, search trends, and organizational activity</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="stats-grid" style={{ gridTemplateColumns: `repeat(${statCards.length}, 1fr)` }}>
        {statCards.map(s => (
          <div key={s.label} className="stat-card">
            <div className={`stat-card-icon ${s.color}`}>
              <s.icon size={16} />
            </div>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value" style={{ fontSize: 24 }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        {/* Doc types */}
        <div className="card">
          <div className="card-header">
            <div className="card-title"><BarChart3 size={15} /> Documents by Type</div>
          </div>
          {docTypes.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 0' }}>No documents</div>
          ) : (
            <div className="analytics-bars">
              {docTypes.map(([type, count], i) => (
                <div key={type} className="analytics-bar-item">
                  <div className="analytics-bar-val">{count}</div>
                  <div
                    className="analytics-bar-fill"
                    style={{ height: `${(count / maxDoc) * 100}%`, background: barColors[i % barColors.length] }}
                  />
                  <div className="analytics-bar-label">{type.toUpperCase()}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Task status */}
        <div className="card">
          <div className="card-header">
            <div className="card-title"><TrendingUp size={15} /> Task Distribution</div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{totalTasks} total</span>
          </div>
          {totalTasks === 0 ? (
            <div className="empty-state" style={{ padding: '24px 0' }}>No tasks created</div>
          ) : (
            <div className="progress-row">
              {taskItems.map(item => (
                <div key={item.label} className="progress-item">
                  <div className="progress-label-row">
                    <span>{item.label}</span>
                    <span>{item.value} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({totalTasks > 0 ? Math.round(item.value / totalTasks * 100) : 0}%)</span></span>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{ width: `${totalTasks > 0 ? (item.value / totalTasks) * 100 : 0}%`, background: item.color }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Team workload graph/breakdown */}
      {data.team_workload && data.team_workload.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <div className="card-title"><Users size={15} /> Team Task Workload & Progress</div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 20px' }}>
            {data.team_workload.map(member => {
              const total = member.pending + member.in_progress + member.completed;
              const completedPct = total > 0 ? (member.completed / total) * 100 : 0;
              const inProgressPct = total > 0 ? (member.in_progress / total) * 100 : 0;
              const pendingPct = total > 0 ? (member.pending / total) * 100 : 0;

              const isExpanded = !!expandedMembers[member.user_id];
              const memberTasks = member.tasks || [];
              const pendingList = memberTasks.filter(t => t.status === 'Pending');
              const inProgressList = memberTasks.filter(t => t.status === 'In_Progress');
              const completedList = memberTasks.filter(t => t.status === 'Completed');

              return (
                <div key={member.user_id} className="analytics-member-row" style={{ display: 'flex', flexDirection: 'column', gap: 6, borderBottom: '1px solid rgba(156, 163, 175, 0.08)', paddingBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 500 }}>
                    <span>{member.name} ({member.email})</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>
                      {total} tasks ({member.completed} Done, {member.in_progress} In Progress, {member.pending} Left)
                    </span>
                  </div>
                  {total > 0 ? (
                    <div style={{ display: 'flex', height: 16, borderRadius: 4, overflow: 'hidden', background: 'var(--bg-overlay)' }}>
                      {member.completed > 0 && (
                        <div
                          style={{ width: `${completedPct}%`, background: 'var(--color-success)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 9, fontWeight: 'bold' }}
                          title={`Completed: ${member.completed}`}
                        >
                          {member.completed}
                        </div>
                      )}
                      {member.in_progress > 0 && (
                        <div
                          style={{ width: `${inProgressPct}%`, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 9, fontWeight: 'bold' }}
                          title={`In Progress: ${member.in_progress}`}
                        >
                          {member.in_progress}
                        </div>
                      )}
                      {member.pending > 0 && (
                        <div
                          style={{ width: `${pendingPct}%`, background: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 9, fontWeight: 'bold' }}
                          title={`Pending: ${member.pending}`}
                        >
                          {member.pending}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ height: 16, borderRadius: 4, background: 'var(--bg-overlay)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: 'var(--text-muted)' }}>
                      No tasks assigned
                    </div>
                  )}
                  {total > 0 && (
                    <button 
                      className="btn btn-ghost btn-xs" 
                      onClick={() => toggleExpandMember(member.user_id)}
                      style={{ alignSelf: 'flex-start', marginTop: 4, padding: '2px 8px', fontSize: 11, color: 'var(--accent)', borderColor: 'rgba(255, 130, 53, 0.15)' }}
                    >
                      {isExpanded ? 'Hide Detailed Tasks' : 'Show Detailed Tasks'}
                    </button>
                  )}

                  {isExpanded && memberTasks.length > 0 && (
                    <div style={{ marginTop: 8, padding: 12, background: 'rgba(0, 0, 0, 0.2)', borderRadius: 6, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                      <div className="grid-3" style={{ gap: 12 }}>
                        {/* Column 1: Pending */}
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: 6, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 2, display: 'flex', justifyContent: 'space-between' }}>
                            <span>TO DO</span>
                            <span>{pendingList.length}</span>
                          </div>
                          {pendingList.length === 0 ? (
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>No pending tasks</div>
                          ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              {pendingList.map(t => (
                                <div key={t.id} style={{ fontSize: 11, padding: '6px 8px', background: 'var(--bg-card)', borderRadius: 4, borderLeft: '3px solid var(--text-muted)' }} title={t.description}>
                                  {t.title}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Column 2: In Progress */}
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 'bold', color: 'var(--accent)', marginBottom: 6, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 2, display: 'flex', justifyContent: 'space-between' }}>
                            <span>IN PROGRESS</span>
                            <span>{inProgressList.length}</span>
                          </div>
                          {inProgressList.length === 0 ? (
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>No tasks in progress</div>
                          ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              {inProgressList.map(t => (
                                <div key={t.id} style={{ fontSize: 11, padding: '6px 8px', background: 'var(--bg-card)', borderRadius: 4, borderLeft: '3px solid var(--accent)' }} title={t.description}>
                                  {t.title}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Column 3: Completed */}
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 'bold', color: 'var(--color-success)', marginBottom: 6, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 2, display: 'flex', justifyContent: 'space-between' }}>
                            <span>COMPLETED</span>
                            <span>{completedList.length}</span>
                          </div>
                          {completedList.length === 0 ? (
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>No completed tasks</div>
                          ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              {completedList.map(t => (
                                <div key={t.id} style={{ fontSize: 11, padding: '6px 8px', background: 'var(--bg-card)', borderRadius: 4, borderLeft: '3px solid var(--color-success)' }} title={t.description}>
                                  {t.title}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            
            {/* Legend */}
            <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--color-success)' }} />
                <span>Completed (Done)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--accent)' }} />
                <span>In Progress</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--text-muted)' }} />
                <span>Pending (Left)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* My Team Section (Manager View) */}
      {isManager && data.team_details?.team_members && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <div className="card-title">
              <Users size={15} /> My Team Directory
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {data.team_details.team_size} members including you
            </span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Department</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.team_details.team_members.map(member => (
                  <tr key={member.id} style={member.is_manager ? { background: 'rgba(124, 58, 237, 0.05)' } : {}}>
                    <td style={{ fontWeight: 500 }}>
                      {member.name} {member.is_manager && <span style={{ fontSize: 10, color: 'var(--accent)', marginLeft: 6, padding: '2px 6px', background: 'rgba(124, 58, 237, 0.15)', borderRadius: 4 }}>You / Manager</span>}
                    </td>
                    <td>{member.email}</td>
                    <td>
                      <span 
                        style={
                          member.is_manager 
                            ? { background: 'rgba(124, 58, 237, 0.15)', color: '#a78bfa', border: '1px solid rgba(124, 58, 237, 0.2)', padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 500 }
                            : { background: 'rgba(59, 130, 246, 0.15)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 500 }
                        }
                      >
                        {member.role}
                      </span>
                    </td>
                    <td>
                      <span style={{ background: 'rgba(156, 163, 175, 0.08)', color: '#9ca3af', border: '1px solid rgba(156, 163, 175, 0.15)', padding: '2px 8px', borderRadius: 12, fontSize: 11 }}>
                        {member.department}
                      </span>
                    </td>
                    <td>
                      {member.is_manager ? '—' : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <button
                            className="btn btn-secondary btn-xs"
                            style={{ color: 'var(--color-danger)', borderColor: 'rgba(244, 63, 94, 0.2)' }}
                            onClick={() => handleTransfer(member.id, null)}
                          >
                            Release
                          </button>
                          <select
                            className="form-select"
                            style={{ width: 'auto', padding: '2px 24px 2px 8px', fontSize: 11, height: 'auto' }}
                            onChange={(e) => {
                              if (e.target.value) {
                                handleTransfer(member.id, parseInt(e.target.value));
                                e.target.value = ''; // reset selection
                              }
                            }}
                            defaultValue=""
                          >
                            <option value="" disabled>Transfer to...</option>
                            {managers
                              .filter(m => m.id !== user?.id)
                              .map(m => (
                                <option key={m.id} value={m.id}>
                                  {m.full_name || m.email}
                                </option>
                              ))}
                          </select>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Teams Directory Section (Admin View) */}
      {isAdmin && data.team_details?.teams && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <div className="card-title">
              <Users size={15} /> Teams Directory
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {data.team_details.total_teams} active teams with {data.team_details.total_team_members} members
            </span>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
            {data.team_details.teams.map((team, idx) => (
              <div 
                key={idx} 
                className="card" 
                style={{ 
                  background: 'rgba(255, 255, 255, 0.02)', 
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  boxShadow: 'none',
                  margin: 0
                }}
              >
                <div 
                  style={{ 
                    padding: '12px 16px', 
                    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    background: 'rgba(255, 255, 255, 0.01)'
                  }}
                >
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>
                      Team {team.manager_name}
                    </h3>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
                      Manager: {team.manager_email} • Department: {team.department}
                    </p>
                  </div>
                  <span 
                    style={{ 
                      background: 'rgba(124, 58, 237, 0.15)', 
                      color: '#a78bfa', 
                      border: '1px solid rgba(124, 58, 237, 0.3)', 
                      padding: '2px 10px', 
                      borderRadius: 12, 
                      fontSize: 11, 
                      fontWeight: 600 
                    }}
                  >
                    {team.team_size} members
                  </span>
                </div>
                <div className="table-wrap" style={{ margin: 0 }}>
                  <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <th style={{ padding: '8px 16px', fontSize: 11 }}>Member Name</th>
                        <th style={{ padding: '8px 16px', fontSize: 11 }}>Email</th>
                        <th style={{ padding: '8px 16px', fontSize: 11 }}>Role</th>
                        <th style={{ padding: '8px 16px', fontSize: 11 }}>Department</th>
                      </tr>
                    </thead>
                    <tbody>
                      {team.members.map(member => (
                        <tr 
                          key={member.id} 
                          style={{ 
                            borderBottom: '1px solid rgba(255, 255, 255, 0.02)',
                            background: member.is_manager ? 'rgba(124, 58, 237, 0.02)' : 'transparent'
                          }}
                        >
                          <td style={{ padding: '10px 16px', fontWeight: 500, fontSize: 12 }}>
                            {member.name} {member.is_manager && <span style={{ fontSize: 9, color: 'var(--accent)', marginLeft: 6, padding: '1px 4px', background: 'rgba(124, 58, 237, 0.15)', borderRadius: 3 }}>Manager / Lead</span>}
                          </td>
                          <td style={{ padding: '10px 16px', fontSize: 12 }}>{member.email}</td>
                          <td style={{ padding: '10px 16px' }}>
                            <span 
                              style={
                                member.is_manager 
                                  ? { background: 'rgba(124, 58, 237, 0.15)', color: '#a78bfa', border: '1px solid rgba(124, 58, 237, 0.2)', padding: '1px 6px', borderRadius: 8, fontSize: 10, fontWeight: 500 }
                                  : { background: 'rgba(59, 130, 246, 0.15)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '1px 6px', borderRadius: 8, fontSize: 10, fontWeight: 500 }
                              }
                            >
                              {member.role}
                            </span>
                          </td>
                          <td style={{ padding: '10px 16px' }}>
                            <span style={{ background: 'rgba(156, 163, 175, 0.08)', color: '#9ca3af', border: '1px solid rgba(156, 163, 175, 0.15)', padding: '1px 6px', borderRadius: 8, fontSize: 10 }}>
                              {member.department}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Department table */}
      {(data.department_activity || []).length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <div className="card-title"><Users size={15} /> Department Activity</div>
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
                {data.department_activity.map((d, i) => {
                  const pct = Math.min(100, d.documents * 15);
                  return (
                    <tr key={i}>
                      <td style={{ fontWeight: 500 }}>{d.name}</td>
                      <td>{d.users}</td>
                      <td>{d.documents}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ flex: 1, height: 4, background: 'var(--bg-overlay)', borderRadius: 2, overflow: 'hidden', maxWidth: 80 }}>
                            <div style={{ height: '100%', width: `${pct}%`, background: 'var(--accent)', borderRadius: 2 }} />
                          </div>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{pct}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent searches */}
      {(data.latest_searches || []).length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="card-title"><Search size={15} /> Recent AI Queries</div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Last {data.latest_searches.length}</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Query</th>
                  <th>User</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {data.latest_searches.map((s, i) => (
                  <tr key={i}>
                    <td style={{ maxWidth: 340 }}>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>"{s.query}"</div>
                    </td>
                    <td className="td-muted">{s.user}</td>
                    <td className="td-muted" style={{ fontSize: 11 }}>{s.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
