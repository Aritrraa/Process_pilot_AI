import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import DOMPurify from 'dompurify';
import { api } from '../api';
import { Plus, ChevronDown, ChevronRight, ChevronLeft, Calendar, Clock, Users, FileText, Link as LinkIcon } from 'lucide-react';

function renderInline(text) {
  if (!text) return null;
  // Sanitize to prevent XSS
  const clean = DOMPurify.sanitize(text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
  const parts = clean.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('`') && part.endsWith('`')) return <code key={i} style={{ background: 'var(--bg-overlay)', padding: '1px 5px', borderRadius: 3, fontSize: '0.9em', fontFamily: 'monospace', color: 'var(--color-info)' }}>{part.slice(1, -1)}</code>;
    return part;
  });
}

function renderMarkdown(text) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let listBuffer = [];

  const flushList = () => {
    if (listBuffer.length > 0) {
      elements.push(<ul key={`ul-${elements.length}`} style={{ margin: '6px 0 6px 18px', listStyleType: 'disc' }}>{listBuffer}</ul>);
      listBuffer = [];
    }
  };

  lines.forEach((line, i) => {
    if (line.startsWith('### ')) { flushList(); elements.push(<h3 key={i} style={{ fontSize: 13, fontWeight: 600, margin: '8px 0 4px' }}>{line.slice(4)}</h3>); return; }
    if (line.startsWith('## ')) { flushList(); elements.push(<h2 key={i} style={{ fontSize: 14, fontWeight: 700, margin: '10px 0 4px' }}>{line.slice(3)}</h2>); return; }
    if (line.startsWith('# ')) { flushList(); elements.push(<h1 key={i} style={{ fontSize: 15, fontWeight: 700, margin: '10px 0 5px' }}>{line.slice(2)}</h1>); return; }
    if (line.startsWith('- ') || line.startsWith('* ')) {
      listBuffer.push(<li key={i} style={{ marginBottom: 2 }}>{renderInline(line.slice(2))}</li>);
      return;
    }
    if (/^\d+\.\s/.test(line)) {
      flushList();
      elements.push(<div key={i} style={{ paddingLeft: 18, marginBottom: 3 }}>{renderInline(line)}</div>);
      return;
    }
    if (line.startsWith('---') || line.startsWith('===')) { flushList(); elements.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid var(--border-subtle)', margin: '8px 0' }} />); return; }
    if (line.trim() === '') { flushList(); elements.push(<div key={i} style={{ height: 6 }} />); return; }
    flushList();
    elements.push(<p key={i} style={{ marginBottom: 4 }}>{renderInline(line)}</p>);
  });
  flushList();
  return elements;
}

export default function Meetings() {
  const PAGE_SIZE = 20;
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [transcript, setTranscript] = useState('');
  const [meetingLink, setMeetingLink] = useState('');
  const [inputMode, setInputMode] = useState('transcript');
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const { data: meetings = [], isLoading: loading } = useQuery({
    queryKey: ['meetings', page],
    queryFn: () => api.getMeetings(page * PAGE_SIZE, PAGE_SIZE),
    keepPreviousData: true,
  });

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    if (inputMode === 'transcript' && !transcript.trim()) return alert('Please paste a transcript.');
    if (inputMode === 'link' && !meetingLink.trim()) return alert('Please enter a meeting link.');
    setCreating(true);
    try {
      await api.createMeeting(
        title,
        inputMode === 'transcript' ? transcript : '',
        inputMode === 'link' ? meetingLink : null
      );
      setTitle(''); setTranscript(''); setMeetingLink(''); setShowForm(false);
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    } catch (err) {
      alert(err.message);
    } finally {
      setCreating(false);
    }
  };

  const SAMPLE_TRANSCRIPT = `CTO: Good morning team. Let's kick off our Q3 planning. First, let's discuss the infrastructure migration.

Engineering Lead: We've completed 60% of the AWS migration. The main blocker is the database migration plan.

DevOps: I need sign-off on the disaster recovery runbook before we proceed. Also requesting budget approval for the new monitoring tools.

CTO: Approved. Sarah, can you finalize the DR plan by end of week?

Sarah (DevOps): Yes, I'll have it ready by Friday.

CTO: Good. Next topic - the new hire onboarding process. HR, what's the status?

HR Manager: We have three new engineers starting next Monday. Onboarding docs are ready, but we need to update the access provisioning SOP.

CTO: Let's make that a priority. Who owns that?

Engineering Lead: I'll take it. I'll update the access provisioning SOP by Wednesday.

CTO: Perfect. Action items summary: Sarah - DR plan by Friday. Engineering Lead - access SOP by Wednesday. Finance - prepare Q3 budget report.`;

  return (
    <div>
      <div className="page-header-row">
        <div className="page-header">
          <h1>Meeting Intelligence</h1>
          <p>AI-powered transcript analysis, summaries, and action item extraction</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <Plus size={14} /> New Meeting
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <div className="card-title">Add Meeting Transcript</div>
            <button className="btn btn-ghost btn-xs" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label className="form-label">Meeting Title *</label>
              <input
                className="form-input"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Q3 Infrastructure Planning Call"
                required
              />
            </div>
            {/* Input mode tabs */}
            <div style={{ display: 'flex', gap: 0, marginBottom: 14, border: '2px solid var(--color-graphite)', width: 'fit-content' }}>
              <button
                type="button"
                onClick={() => setInputMode('transcript')}
                style={{
                  padding: '8px 18px', fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer',
                  fontFamily: 'Archivo, sans-serif', textTransform: 'uppercase',
                  background: inputMode === 'transcript' ? 'var(--color-petrol)' : 'var(--color-paper)',
                  color: inputMode === 'transcript' ? 'var(--color-paper)' : 'var(--color-graphite)',
                  borderRight: '2px solid var(--color-graphite)',
                  transition: 'all var(--transition)'
                }}
              >
                <FileText size={12} style={{ marginRight: 6, verticalAlign: -2 }} />
                Paste Transcript
              </button>
              <button
                type="button"
                onClick={() => setInputMode('link')}
                style={{
                  padding: '8px 18px', fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer',
                  fontFamily: 'Archivo, sans-serif', textTransform: 'uppercase',
                  background: inputMode === 'link' ? 'var(--color-petrol)' : 'var(--color-paper)',
                  color: inputMode === 'link' ? 'var(--color-paper)' : 'var(--color-graphite)',
                  transition: 'all var(--transition)'
                }}
              >
                <LinkIcon size={12} style={{ marginRight: 6, verticalAlign: -2 }} />
                Meeting Link
              </button>
            </div>

            {inputMode === 'transcript' ? (
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">
                  Transcript / Notes *
                  <button
                    type="button"
                    className="btn btn-ghost btn-xs"
                    style={{ marginLeft: 8 }}
                    onClick={() => setTranscript(SAMPLE_TRANSCRIPT)}
                  >
                    Load sample
                  </button>
                </label>
                <textarea
                  className="form-textarea"
                  value={transcript}
                  onChange={e => setTranscript(e.target.value)}
                  placeholder="Paste meeting transcript here. The AI will extract a summary and action items automatically."
                  style={{ minHeight: 200, fontFamily: 'monospace', fontSize: 12 }}
                />
              </div>
            ) : (
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Meeting Recording / Link *</label>
                <input
                  className="form-input"
                  value={meetingLink}
                  onChange={e => setMeetingLink(e.target.value)}
                  placeholder="e.g. https://meet.google.com/abc-defg-hij or Zoom/Teams link"
                />
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.5 }}>
                  <LinkIcon size={10} style={{ verticalAlign: -1, marginRight: 4 }} />
                  Supports Google Meet, Zoom, Microsoft Teams, and other meeting platform links.
                  The AI will automatically transcribe and analyze the meeting audio.
                </div>
              </div>
            )}
            <div style={{ marginTop: 14 }}>
              <button className="btn btn-primary" type="submit" disabled={creating}>
                {creating
                  ? <><span className="spinner-sm" style={{ borderTopColor: 'white' }} /> {inputMode === 'link' ? 'Transcribing & Analyzing…' : 'Analyzing with AI…'}</>
                  : inputMode === 'link' ? 'Transcribe & Analyze' : 'Analyze Meeting'
                }
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="spinner" /> : (() => {
        const safeMeetings = Array.isArray(meetings) ? meetings : [];
        return safeMeetings.length === 0 ? (
          <div className="empty-state">
            <Users size={32} />
            <div style={{ marginTop: 8 }}>No meetings recorded yet</div>
            <div style={{ fontSize: 11, marginTop: 4 }}>Add a meeting transcript to get AI-generated summaries and action items</div>
            <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} onClick={() => setShowForm(true)}>
              <Plus size={12} /> Add first meeting
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {safeMeetings.map(m => (
            <div
              key={m.id}
              className={`meeting-card ${expanded === m.id ? 'expanded' : ''}`}
              onClick={() => setExpanded(expanded === m.id ? null : m.id)}
            >
              <div className="meeting-card-header">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, flex: 1 }}>
                  <div style={{ width: 36, height: 36, background: 'var(--bg-hover)', border: '1px solid var(--color-graphite)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Users size={16} color="var(--color-petrol)" />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="meeting-card-title">{m.title}</div>
                    <div className="meeting-card-meta" style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                        <Calendar size={10} />
                        {new Date(m.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                        <FileText size={10} />
                        {m.transcript?.split(' ').length || 0} words
                      </span>
                      {m.meeting_link && (
                        <span
                          style={{ display: 'flex', alignItems: 'center', gap: 3, cursor: 'pointer', color: 'var(--accent)' }}
                          onClick={(e) => { e.stopPropagation(); window.open(m.meeting_link, '_blank'); }}
                          title={m.meeting_link}
                        >
                          <LinkIcon size={10} />
                          Meeting Link
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                {expanded === m.id ? <ChevronDown size={16} color="var(--text-muted)" /> : <ChevronRight size={16} color="var(--text-muted)" />}
              </div>

              {m.summary && (
                <div className="meeting-summary">
                  <strong style={{ color: 'var(--text-primary)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>AI Summary</strong>
                  <div style={{ marginTop: 4 }}>{renderMarkdown(m.summary)}</div>
                </div>
              )}

              {expanded === m.id && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>
                    Full Transcript
                  </div>
                  <div className="meeting-transcript">{m.transcript}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      );
    })()}
    {/* Pagination */}
    <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
        Page {page + 1}
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        <button className="btn btn-ghost btn-sm" disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>
          <ChevronLeft size={14} /> Previous
        </button>
        <button className="btn btn-ghost btn-sm" disabled={meetings.length < PAGE_SIZE} onClick={() => setPage(p => p + 1)}>
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
    </div>
  );
}
