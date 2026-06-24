import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { useNavigate } from 'react-router-dom';
import { 
  Share2, Users, FileText, CheckSquare, Calendar, Zap, 
  HelpCircle, Compass, ShieldAlert, Cpu
} from 'lucide-react';

export default function Graph() {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNodes, setSelectedNodes] = useState([]);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [activeNodeId, setActiveNodeId] = useState(null);
  const [coords, setCoords] = useState({});
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const containerRef = useRef(null);
  const navigate = useNavigate();

  const loadGraph = () => {
    setLoading(true);
    api.getFullGraph()
      .then(data => {
        setGraphData(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadGraph();
  }, []);

  const updateCoords = () => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    
    setDimensions({
      width: container.scrollWidth,
      height: container.scrollHeight
    });
    
    const containerRect = container.getBoundingClientRect();
    const newCoords = {};
    const elements = container.querySelectorAll('[data-node-id]');
    elements.forEach(el => {
      const id = el.getAttribute('data-node-id');
      const rect = el.getBoundingClientRect();
      
      newCoords[id] = {
        x: rect.left - containerRect.left + container.scrollLeft + rect.width / 2,
        y: rect.top - containerRect.top + container.scrollTop + rect.height / 2,
        left: rect.left - containerRect.left + container.scrollLeft,
        top: rect.top - containerRect.top + container.scrollTop,
        width: rect.width,
        height: rect.height
      };
    });
    setCoords(newCoords);
  };

  useEffect(() => {
    if (graphData && !loading) {
      updateCoords();
      const timer = setTimeout(updateCoords, 150);
      window.addEventListener('resize', updateCoords);
      
      const container = containerRef.current;
      if (container) {
        container.addEventListener('scroll', updateCoords);
      }
      
      return () => {
        clearTimeout(timer);
        window.removeEventListener('resize', updateCoords);
        if (container) {
          container.removeEventListener('scroll', updateCoords);
        }
      };
    }
  }, [graphData, loading]);

  if (loading) return <div className="spinner" />;

  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];

  // Group nodes by category
  const columns = {
    departments: nodes.filter(n => n.type === 'Department'),
    users: nodes.filter(n => n.type === 'User'),
    content: nodes.filter(n => n.type === 'Document' || n.type === 'Meeting' || n.type === 'Technology'),
    tasks: nodes.filter(n => n.type === 'Task')
  };

  // Node Selection Handlers
  const handleNodeClick = (node, e) => {
    if (e.shiftKey) {
      // Toggle node in multi-selection
      if (selectedNodes.some(sn => sn.id === node.id)) {
        setSelectedNodes(prev => prev.filter(sn => sn.id !== node.id));
      } else {
        setSelectedNodes(prev => [...prev, node]);
      }
    } else {
      // Single selection
      setSelectedNodes([node]);
      setActiveNodeId(node.id);
    }
  };

  const clearSelection = () => {
    setSelectedNodes([]);
    setActiveNodeId(null);
  };

  const startScopedChat = () => {
    if (selectedNodes.length === 0) return;
    const scopedIds = selectedNodes.map(sn => sn.id);
    navigate('/chat', { state: { scopedNodeIds: scopedIds } });
  };

  // Check if edge connects hovered or selected node
  const isEdgeHighlighted = (edge) => {
    const isSelected = selectedNodes.some(sn => sn.id === edge.source || sn.id === edge.target);
    const isHovered = hoveredNode === edge.source || hoveredNode === edge.target;
    return isSelected || isHovered;
  };

  const getIcon = (type) => {
    switch (type) {
      case 'Department': return <Compass size={13} />;
      case 'User': return <Users size={13} />;
      case 'Document': return <FileText size={13} />;
      case 'Meeting': return <Calendar size={13} />;
      case 'Task': return <CheckSquare size={13} />;
      default: return <HelpCircle size={13} />;
    }
  };

  const activeNode = selectedNodes.length === 1 ? selectedNodes[0] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', position: 'relative' }}>
      <div className="page-header-row" style={{ flexShrink: 0 }}>
        <div className="page-header">
          <h1>Knowledge Graph</h1>
          <p>Bloomberg-style dependencies and context-scoped auditing</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {selectedNodes.length > 0 && (
            <button className="btn btn-primary" onClick={startScopedChat}>
              <Zap size={13} /> Chat with {selectedNodes.length} Node{selectedNodes.length > 1 ? 's' : ''} Context
            </button>
          )}
          {selectedNodes.length > 0 && (
            <button className="btn btn-ghost btn-sm" onClick={clearSelection}>
              Clear selection
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>
        {/* Graph Canvas Container */}
        <div 
          ref={containerRef}
          className="graph-canvas-container"
          style={{
            flex: 1,
            display: 'flex',
            gap: '80px',
            overflowX: 'auto',
            overflowY: 'auto',
            alignItems: 'flex-start',
            padding: '24px',
            position: 'relative',
            background: 'var(--bg-app)',
            border: '1px solid var(--border-default)'
          }}
        >
          {/* SVG Connector Layer */}
          <svg 
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: dimensions.width,
              height: dimensions.height,
              pointerEvents: 'none',
              zIndex: 1
            }}
          >
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-disabled)" />
              </marker>
              <marker id="arrow-highlighted" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-blue)" />
              </marker>
            </defs>
            {edges.map((edge, idx) => {
              const from = coords[edge.source];
              const to = coords[edge.target];
              if (!from || !to) return null;
              
              const highlighted = isEdgeHighlighted(edge);
              return (
                <g key={idx}>
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={highlighted ? 'var(--color-blue)' : 'var(--border-default)'}
                    strokeWidth={highlighted ? 2 : 1}
                    markerEnd={highlighted ? 'url(#arrow-highlighted)' : 'url(#arrow)'}
                    opacity={highlighted ? 1 : 0.4}
                    transition="all var(--transition)"
                  />
                  {highlighted && (
                    <text
                      x={(from.x + to.x) / 2}
                      y={(from.y + to.y) / 2 - 4}
                      fill="var(--color-blue)"
                      fontSize="9"
                      fontFamily="IBM Plex Mono"
                      fontWeight="600"
                      textAnchor="middle"
                      style={{ background: 'var(--bg-app)', padding: '2px' }}
                    >
                      {edge.relationship.toUpperCase()}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Column 1: Departments */}
          <div className="graph-column">
            <div className="graph-column-header">Departments</div>
            <div className="graph-column-body">
              {columns.departments.map(n => {
                const isSelected = selectedNodes.some(sn => sn.id === n.id);
                return (
                  <div
                    key={n.id}
                    data-node-id={n.id}
                    className={`graph-node ${isSelected ? 'selected' : ''}`}
                    onClick={(e) => handleNodeClick(n, e)}
                    onMouseEnter={() => setHoveredNode(n.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <div className="graph-node-title">
                      {getIcon(n.type)}
                      {n.name}
                    </div>
                    <div className="graph-node-meta">ID: {n.id}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Column 2: Users */}
          <div className="graph-column">
            <div className="graph-column-header">Team & Users</div>
            <div className="graph-column-body">
              {columns.users.map(n => {
                const isSelected = selectedNodes.some(sn => sn.id === n.id);
                return (
                  <div
                    key={n.id}
                    data-node-id={n.id}
                    className={`graph-node ${isSelected ? 'selected' : ''}`}
                    onClick={(e) => handleNodeClick(n, e)}
                    onMouseEnter={() => setHoveredNode(n.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <div className="graph-node-title">
                      {getIcon(n.type)}
                      {n.name}
                    </div>
                    <div className="graph-node-meta">{n.role}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Column 3: Documents & Meetings */}
          <div className="graph-column">
            <div className="graph-column-header">Documents & Knowledge</div>
            <div className="graph-column-body">
              {columns.content.map(n => {
                const isSelected = selectedNodes.some(sn => sn.id === n.id);
                return (
                  <div
                    key={n.id}
                    data-node-id={n.id}
                    className={`graph-node ${isSelected ? 'selected' : ''}`}
                    onClick={(e) => handleNodeClick(n, e)}
                    onMouseEnter={() => setHoveredNode(n.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <div className="graph-node-title">
                      {getIcon(n.type)}
                      {n.title || n.name}
                    </div>
                    <div className="graph-node-meta">{n.type} {n.file_type ? `(${n.file_type})` : ''}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Column 4: Tasks */}
          <div className="graph-column">
            <div className="graph-column-header">Operational Tasks</div>
            <div className="graph-column-body">
              {columns.tasks.map(n => {
                const isSelected = selectedNodes.some(sn => sn.id === n.id);
                return (
                  <div
                    key={n.id}
                    data-node-id={n.id}
                    className={`graph-node ${isSelected ? 'selected' : ''}`}
                    onClick={(e) => handleNodeClick(n, e)}
                    onMouseEnter={() => setHoveredNode(n.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <div className="graph-node-title">
                      {getIcon(n.type)}
                      {n.title}
                    </div>
                    <div className="graph-node-meta">Status: {n.status}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Bloomberg Detail Sidebar Drawer */}
        <div className={`graph-sidebar-drawer ${selectedNodes.length > 0 ? 'open' : ''}`}>
          <div className="drawer-header">
            <h3>Bloomberg Terminal Panel</h3>
            <span style={{ fontSize: 10, fontFamily: 'IBM Plex Mono', color: 'var(--color-gold)' }}>ACTIVE AUDIT MODE</span>
          </div>

          {activeNode ? (
            <div className="drawer-body">
              <div className="drawer-section">
                <span className="drawer-section-lbl">Entity Type</span>
                <div className="drawer-val-pill">{activeNode.type.toUpperCase()}</div>
              </div>
              <div className="drawer-section">
                <span className="drawer-section-lbl">Entity Name</span>
                <div className="drawer-val-text">{activeNode.title || activeNode.name}</div>
              </div>
              <div className="drawer-section">
                <span className="drawer-section-lbl">Identifier</span>
                <code style={{ fontSize: 11, fontFamily: 'IBM Plex Mono', color: 'var(--text-secondary)' }}>{activeNode.id}</code>
              </div>
              {activeNode.type === 'Document' && (
                <div className="drawer-section">
                  <span className="drawer-section-lbl">Format Type</span>
                  <div className="drawer-val-text">{activeNode.file_type?.toUpperCase()} file</div>
                </div>
              )}
              {activeNode.type === 'Task' && (
                <div className="drawer-section">
                  <span className="drawer-section-lbl">Status</span>
                  <div className="drawer-val-text">{activeNode.status}</div>
                </div>
              )}
            </div>
          ) : selectedNodes.length > 1 ? (
            <div className="drawer-body">
              <div className="drawer-section">
                <span className="drawer-section-lbl">Multi-Selection Status</span>
                <div className="drawer-val-text">{selectedNodes.length} nodes selected concurrently</div>
              </div>
              <div className="drawer-section">
                <span className="drawer-section-lbl">Target Selection scope</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6 }}>
                  {selectedNodes.map(sn => (
                    <div key={sn.id} className="drawer-selected-item">
                      {getIcon(sn.type)}
                      <span className="item-label">{sn.title || sn.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="drawer-body-empty">
              <ShieldAlert size={28} color="var(--text-disabled)" style={{ marginBottom: 12 }} />
              <div>No context active</div>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', marginTop: 4 }}>
                Click a node to view properties, or Shift-click to select multiple nodes for scoped analysis.
              </p>
            </div>
          )}

          {selectedNodes.length > 0 && (
            <div className="drawer-footer">
              <button className="btn btn-primary" style={{ width: '100%' }} onClick={startScopedChat}>
                <Zap size={14} /> Scope AI Chat Session
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
