import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { Upload, Trash2, FileText, File, Database, RefreshCw, AlertCircle } from 'lucide-react';

const typeConfig = {
  pdf:  { badge: 'badge-red', label: 'PDF' },
  docx: { badge: 'badge-cyan', label: 'DOCX' },
  doc:  { badge: 'badge-cyan', label: 'DOC' },
  txt:  { badge: 'badge-neutral', label: 'TXT' },
  csv:  { badge: 'badge-green', label: 'CSV' },
};

export default function Documents() {
  const { user } = useAuth();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [deptFilter, setDeptFilter] = useState('');
  const [toast, setToast] = useState('');
  const fileRef = useRef();

  const load = () => api.getDocuments().then(setDocs).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => {
    load();
    api.getDepartments().then(setDepartments).catch(() => {});
  }, []);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadProgress(0);
    // Simulate progress
    const interval = setInterval(() => setUploadProgress(p => Math.min(p + 15, 85)), 400);
    try {
      await api.uploadDocument(file);
      clearInterval(interval);
      setUploadProgress(100);
      setTimeout(() => setUploadProgress(0), 800);
      showToast(`✓ "${file.name}" uploaded and indexed successfully`);
      load();
    } catch (err) {
      clearInterval(interval);
      setUploadProgress(0);
      showToast(`✗ Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  };

  const handleDelete = async (doc) => {
    if (!confirm(`Delete "${doc.title}" and remove all its indexed data? This cannot be undone.`)) return;
    try {
      await api.deleteDocument(doc.id);
      setDocs(prev => prev.filter(d => d.id !== doc.id));
      showToast(`Deleted "${doc.title}"`);
    } catch (err) {
      showToast(`✗ Delete failed: ${err.message}`);
    }
  };

  const filtered = deptFilter
    ? docs.filter(d => String(d.department_id) === deptFilter)
    : docs;

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header">
          <h1>Documents</h1>
          <p>Upload, manage, and search your organization's knowledge base</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {toast && (
        <div className={`alert ${toast.startsWith('✗') ? 'alert-danger' : 'alert-success'}`} style={{ marginBottom: 16 }}>
          {toast}
        </div>
      )}

      {/* Upload zone */}
      <div
        className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
        style={{ marginBottom: 20 }}
        onClick={() => !uploading && fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        <input
          type="file"
          ref={fileRef}
          onChange={e => handleFile(e.target.files?.[0])}
          accept=".pdf,.docx,.doc,.txt,.csv"
        />
        <div className="upload-icon">
          {uploading ? <div className="spinner-sm" /> : <Upload size={20} />}
        </div>
        <div className="upload-zone-text">
          {uploading
            ? 'Processing & indexing document…'
            : <><strong>Click to upload</strong> or drag and drop</>
          }
        </div>
        <div className="upload-zone-hint">PDF, DOCX, TXT, CSV — auto-extracted and vectorized</div>
        {uploadProgress > 0 && (
          <div className="upload-progress" style={{ marginTop: 12, width: '60%', margin: '12px auto 0' }}>
            <div className="upload-progress-fill" style={{ width: `${uploadProgress}%` }} />
          </div>
        )}
      </div>

      {/* Filter */}
      {departments.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Filter by department:</span>
          <select
            className="form-select"
            value={deptFilter}
            onChange={e => setDeptFilter(e.target.value)}
            style={{ width: 'auto', padding: '5px 28px 5px 10px', fontSize: 12 }}
          >
            <option value="">All departments</option>
            {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          {deptFilter && (
            <button className="btn btn-ghost btn-xs" onClick={() => setDeptFilter('')}>Clear</button>
          )}
        </div>
      )}

      {/* Document list */}
      {loading ? (
        <div className="spinner" />
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <FileText size={32} />
          <div style={{ marginTop: 8 }}>{deptFilter ? 'No documents in this department' : 'No documents uploaded yet'}</div>
          <div style={{ fontSize: 11, marginTop: 4 }}>Upload your first document to start building the knowledge base</div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Document</th>
                <th>Type</th>
                <th>Department</th>
                <th>Uploaded</th>
                <th style={{ width: 80 }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(doc => {
                const isOtherUserDoc = user?.role === 'Employee' && doc.uploaded_by !== user?.id;
                const cfg = typeConfig[doc.file_type?.toLowerCase()] || { badge: 'badge-neutral', label: doc.file_type?.toUpperCase() || 'FILE' };
                const dept = departments.find(d => d.id === doc.department_id);
                return (
                  <tr key={doc.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{ width: 32, height: 32, background: 'var(--bg-overlay)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <FileText size={15} color="var(--text-muted)" />
                        </div>
                        <div>
                          <div style={{ fontWeight: 500, fontSize: 13 }}>{doc.title}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                            <Database size={9} /> Indexed in vector DB
                          </div>
                        </div>
                      </div>
                    </td>
                    <td>
                      {isOtherUserDoc ? (
                        <span className="badge badge-neutral">—</span>
                      ) : (
                        <span className={`badge ${cfg.badge}`}>{cfg.label}</span>
                      )}
                    </td>
                    <td className="td-muted">
                      {isOtherUserDoc ? '—' : (dept?.name || '—')}
                    </td>
                    <td className="td-muted">
                      {isOtherUserDoc ? '—' : new Date(doc.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </td>
                    <td>
                      {!isOtherUserDoc && (
                        <button
                          className="btn btn-ghost btn-icon"
                          onClick={() => handleDelete(doc)}
                          title="Delete document"
                          style={{ color: 'var(--color-danger)' }}
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Stats bar */}
      {docs.length > 0 && (
        <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 16 }}>
          <span>{docs.length} document{docs.length !== 1 ? 's' : ''} total</span>
          <span>{filtered.length} shown</span>
        </div>
      )}
    </div>
  );
}
