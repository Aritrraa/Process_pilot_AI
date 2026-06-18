import { useState, useEffect } from 'react';
import { api } from '../api';
import { Plus, ChevronDown, ChevronRight, Calendar, Clock, Users, FileText, Link as LinkIcon } from 'lucide-react';

export default function Meetings() {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [transcript, setTranscript] = useState('');
  const [meetingLink, setMeetingLink] = useState('');
  const [inputMode, setInputMode] = useState('transcript');
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const load = () => api.getMeetings().then(setMeetings).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => {
    load();
  }, []);

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
      load();
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
            <div style={{ display: 'flex', gap: 0, marginBottom: 14, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border-color)', width: 'fit-content' }}>
              <button
                type="button"
                onClick={() => setInputMode('transcript')}
                style={{
                  padding: '7px 16px', fontSize: 12, fontWeight: 500, border: 'none', cursor: 'pointer',
                  background: inputMode === 'transcript' ? 'var(--accent)' : 'var(--bg-overlay)',
                  color: inputMode === 'transcript' ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.2s'
                }}
              >
                <FileText size={12} style={{ marginRight: 5, verticalAlign: -2 }} />
                Paste Transcript
              </button>
              <button
                type="button"
                onClick={() => setInputMode('link')}
                style={{
                  padding: '7px 16px', fontSize: 12, fontWeight: 500, border: 'none', cursor: 'pointer',
                  background: inputMode === 'link' ? 'var(--accent)' : 'var(--bg-overlay)',
                  color: inputMode === 'link' ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.2s'
                }}
              >
                <LinkIcon size={12} style={{ marginRight: 5, verticalAlign: -2 }} />
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
                  <div style={{ width: 36, height: 36, background: 'var(--bg-elevated)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Users size={16} color="var(--text-muted)" />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="meeting-card-title">{m.title}</div>
                    <div className="meeting-card-meta" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
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
                  <div style={{ marginTop: 4 }}>{m.summary}</div>
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
    </div>
  );
}
