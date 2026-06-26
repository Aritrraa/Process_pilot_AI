import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, FileText, MessageSquare, Users, CheckSquare,
  BarChart3, Settings, LogOut, Compass, Menu, X, ChevronRight, Share2
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/chat', icon: MessageSquare, label: 'AI Copilot' },
  { to: '/graph', icon: Share2, label: 'Knowledge Graph' },
  { to: '/meetings', icon: Users, label: 'Meetings' },
  { to: '/tasks', icon: CheckSquare, label: 'Tasks' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const roleColors = {
    Admin: 'badge-blue',
    Manager: 'badge-purple',
    Employee: 'badge-neutral',
  };

  return (
    <>
      {/* Mobile Top Header Bar */}
      <div className="mobile-header-bar">
        <button className="mobile-menu-btn" onClick={() => setOpen(!open)} aria-label="Toggle navigation">
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
        <div className="mobile-brand-title">
          <Compass size={14} className="mobile-brand-logo" />
          <span>Process Pilot</span>
        </div>
        <div style={{ width: 34 }} /> {/* Balance spacer to align title center */}
      </div>

      <aside className={`sidebar ${open ? 'open' : ''}`}>
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="logo-mark">
            <Compass size={18} color="white" />
          </div>
          <div className="brand-text">
            <div className="brand-name">Process Pilot</div>
            <div className="brand-sub">Enterprise Copilot</div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <div className="nav-section-label">Workspace</div>
          {navItems.slice(0, 4).map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/dashboard'}
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setOpen(false)}
            >
              <item.icon className="nav-icon" size={16} />
              {item.label}
            </NavLink>
          ))}

          <div className="nav-section-label">Manage</div>
          {navItems.slice(4, 7).map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setOpen(false)}
            >
              <item.icon className="nav-icon" size={16} />
              {item.label}
            </NavLink>
          ))}

          <div className="nav-section-label">System</div>
          <NavLink
            to="/settings"
            className={({ isActive }) => isActive ? 'active' : ''}
            onClick={() => setOpen(false)}
          >
            <Settings className="nav-icon" size={16} />
            Settings
          </NavLink>
        </nav>

        {/* Footer / User */}
        <div className="sidebar-footer">
          {user && (
            <div className="sidebar-user" onClick={logout} title="Click to logout">
              <div className="user-avatar">{user.email[0].toUpperCase()}</div>
              <div className="user-info">
                <div className="user-email">{user.email}</div>
                <div className="user-role-badge">
                  <span className={`badge ${roleColors[user.role] || 'badge-neutral'}`} style={{ fontSize: 10, padding: '1px 6px' }}>
                    {user.role}
                  </span>
                </div>
              </div>
              <LogOut size={14} color="var(--text-muted)" />
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
