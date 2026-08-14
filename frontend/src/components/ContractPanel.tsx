import React, { useEffect, useState } from 'react';
import { ArrowLeft, Save, History, Upload, FileText, AlertTriangle, FileSearch, CheckCircle2, AlertCircle, ShieldAlert, Download } from 'lucide-react';
import { downloadAuthenticated } from '../download';
import ContractStructureEditor from './ContractStructureEditor';
import type { ContractNode } from './ContractStructureEditor';

interface Props {
  contractId: string;
  headers: Record<string, string>;
  onClose: () => void;
  onUpdated?: () => void;
}

interface ContractDetail {
  id: string;
  title: string;
  reference_number: string;
  counterparty: string;
  state: string;
  owner_id: string;
  organization_id: string;
}

interface Version { id: string; version_number: number; title: string; counterparty: string; content: string | null; structure?: ContractNode[] | null; is_active: boolean; created_at: string; }
interface DocumentItem { id: string; contract_id: string; doc_type: string; title: string; created_at: string; version_count?: number; }
interface WorkflowSummary { id: string; contract_id: string; status: string; current_step?: string; current_step_role?: string; steps: { name: string; status: string; assigned_role: string }[]; }
interface Feedback { id: string; version_id: string; reviewer_id: string; reviewer_role: string; kind: string; body: string; proposed_text?: string; status: string; created_at: string; }

const stateSt = (s: string) => {
  switch (s) {
    case 'APPROVED': case 'EXECUTED': case 'ACTIVE': return { bg: '#dcfce7', color: '#166534' };
    case 'REJECTED': case 'TERMINATED': return { bg: '#fee2e2', color: '#991b1b' };
    case 'SUBMITTED': case 'UNDER_REVIEW': return { bg: '#fef3c7', color: '#92400e' };
    default: return { bg: '#f1f5f9', color: '#475569' };
  }
};

const riskSt = (s: string) => {
  switch (s) {
    case 'CRITICAL': return { bg: '#fee2e2', color: '#991b1b' };
    case 'HIGH': return { bg: '#ffedd5', color: '#9a3412' };
    case 'MEDIUM': return { bg: '#fef3c7', color: '#92400e' };
    default: return { bg: '#dcfce7', color: '#166534' };
  }
};

const NEW_STATES = ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'EXECUTED', 'ACTIVE', 'TERMINATED', 'ARCHIVED'];
const LIFECYCLE_STATES = ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'EXECUTED', 'ACTIVE'];

export default function ContractPanel({ contractId, headers, onClose, onUpdated }: Props) {
  const [detail, setDetail] = useState<ContractDetail | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [workflow, setWorkflow] = useState<WorkflowSummary | null>(null);
  const [editing, setEditing] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const [title, setTitle] = useState('');
  const [ref, setRef] = useState('');
  const [counterparty, setCounterparty] = useState('');
  const [content, setContent] = useState('');
  const [structure, setStructure] = useState<ContractNode[]>([]);

  const [newState, setNewState] = useState('APPROVED');
  const [review, setReview] = useState<any>(null);
  const [clauses, setClauses] = useState<any>(null);
  const [reviewing, setReviewing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState('attachment');
  const [file, setFile] = useState<File | null>(null);
  const [reviewProvider, setReviewProvider] = useState('rules');
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [mergeContent, setMergeContent] = useState('');
  const [mergeTarget, setMergeTarget] = useState<Feedback | null>(null);
  const [exporting, setExporting] = useState('');

  const api = async (path: string, opts: RequestInit = {}) => {
    const res = await fetch(path, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
    const data = await res.json();
    if (!data.success) throw new Error(data.error?.message || 'Request failed');
    return data.data;
  };

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const d = await api(`/api/v1/contracts/${contractId}`);
      setDetail(d);
      const v = await api(`/api/v1/contracts/${contractId}/versions`);
      setVersions(v.items || []);
      try {
        const docs = await api(`/api/v1/documents/contract/${contractId}`);
        setDocuments(docs.items || []);
      } catch { setDocuments([]); }
      try {
        const running = await api(`/api/v1/workflows?status=RUNNING&limit=200`);
        setWorkflow((running.items || []).find((item: WorkflowSummary) => item.contract_id === contractId) || null);
      } catch { setWorkflow(null); }
      try {
        const reviewItems = await api(`/api/v1/contracts/${contractId}/feedback`);
        setFeedback(reviewItems.items || []);
      } catch { setFeedback([]); }
    } catch (e: any) { setError(e.message || 'Unable to load contract'); }
    finally { setLoading(false); }
  };

  const decideFeedback = async (item: Feedback, status: 'ACCEPTED' | 'REJECTED') => {
    setError(''); setMsg('');
    try {
      await api(`/api/v1/contracts/feedback/${item.id}/decision`, {
        method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
      });
      setMsg(`Feedback ${status.toLowerCase()}`);
      await load();
    } catch (e: any) { setError(e.message); }
  };

  const mergeFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mergeTarget) return;
    setError(''); setMsg('');
    try {
      await api(`/api/v1/contracts/${contractId}/feedback/${mergeTarget.id}/merge`, {
        method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ new_content: mergeContent }),
      });
      setMergeTarget(null); setMergeContent(''); setMsg('Accepted feedback merged into a new official version');
      await load();
      if (onUpdated) onUpdated();
    } catch (e: any) { setError(e.message); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [contractId]);

  const startEdit = () => {
    if (!detail) return;
    setTitle(detail.title);
    setRef(detail.reference_number);
    setCounterparty(detail.counterparty);
    const active = versions.find(v => v.is_active);
    setContent(active?.content || '');
    setStructure(active?.structure || (active?.content ? [{ id: `legacy-${Date.now()}`, title: 'متن قرارداد', body: active.content, children: [], notes: [] }] : []));
    setEditing(true);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setMsg('');
    try {
      const payload: any = { title, reference_number: ref, counterparty, structure };
      if (!structure.length && content) payload.content = content;
      await api(`/api/v1/contracts/${contractId}`, {
        method: 'PATCH',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setMsg('Contract updated (new immutable version created)');
      setEditing(false);
      await load();
      if (onUpdated) onUpdated();
    } catch (e: any) { setError(e.message); }
  };

  const transition = async () => {
    setError(''); setMsg('');
    try {
      await api(`/api/v1/contracts/${contractId}/transition`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_state: newState }),
      });
      setMsg(`State changed to ${newState}`);
      await load();
      if (onUpdated) onUpdated();
    } catch (e: any) { setError(e.message); }
  };

  const exportContract = async (format: 'docx' | 'pdf') => {
    setExporting(format); setError('');
    try {
      await downloadAuthenticated(`/api/v1/contracts/${contractId}/export?format=${format}`, headers, `${detail?.reference_number || 'contract'}.${format}`);
      setMsg(`${format.toUpperCase()} export downloaded`);
    } catch (e: any) { setError(e.message || 'Export failed'); }
    finally { setExporting(''); }
  };

  const runReview = async () => {
    setReviewing(true); setError('');
    try {
      const r = await api(`/api/v1/intelligence/review/${contractId}?provider=${encodeURIComponent(reviewProvider)}`);
      setReview(r);
    } catch (e: any) { setError(e.message); }
    finally { setReviewing(false); }
  };

  const runClauses = async () => {
    setAnalyzing(true); setError('');
    try {
      const c = await api(`/api/v1/intelligence/clauses/${contractId}`);
      setClauses(c);
    } catch (e: any) { setError(e.message); }
    finally { setAnalyzing(false); }
  };

  const uploadDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return setError('Choose a file');
    setUploading(true); setError(''); setMsg('');
    const fd = new FormData();
    fd.append('contract_id', contractId);
    fd.append('file', file);
    fd.append('doc_type', docType);
    try {
      const res = await fetch('/api/v1/documents/upload', { method: 'POST', headers: { ...headers }, body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error?.message || 'Upload failed');
      setMsg(`Uploaded ${file.name}`);
      setFile(null);
      const docs = await api(`/api/v1/documents/contract/${contractId}`);
      setDocuments(docs.items || []);
    } catch (e: any) { setError(e.message); }
    finally { setUploading(false); }
  };

  if (!detail) {
    return <div className="contract-workspace__state" style={emptyBox()}>
      {loading ? <><div className="contract-workspace__spinner" /> <strong>Loading contract workspace…</strong><span>Gathering versions, documents, and analysis tools.</span></> : <><AlertCircle size={28} color="#dc2626" /><strong>We couldn’t open this contract</strong><span>{error || 'The contract may have been removed or you may not have access.'}</span><button onClick={load} style={btn('primary')}>Try again</button></>}
    </div>;
  }

  const lifecycleIndex = LIFECYCLE_STATES.indexOf(detail.state);
  const lifecycleProgress = lifecycleIndex >= 0 ? ((lifecycleIndex + 1) / LIFECYCLE_STATES.length) * 100 : 0;
  const activeVersion = versions.find(v => v.is_active) || versions[versions.length - 1];

  return (
    <div className="contract-workspace" style={{ background: '#fff', borderRadius: '14px', border: '1px solid #e2e8f0', padding: '24px', marginBottom: '24px', boxShadow: '0 12px 30px rgba(15, 23, 42, .06)' }}>
      <div className="contract-workspace__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #f1f5f9', paddingBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onClose} style={btn('ghost')}><ArrowLeft size={16} /> Back</button>
          <div>
            <div style={{ fontWeight: 700, fontSize: '16px', color: '#0f172a' }}>{detail.title}</div>
            <div style={{ fontSize: '12px', color: '#64748b' }}>{detail.reference_number} · {detail.counterparty} · Owner {detail.owner_id.slice(0, 8)}</div>
          </div>
        </div>
        <span style={pill(detail.state)}>{detail.state}</span>
      </div>

      {error && <div style={banner('#fee2e2', '#991b1b')}><AlertCircle size={16} /> {error}</div>}
      {msg && <div style={banner('#dcfce7', '#166534')}><CheckCircle2 size={16} /> {msg}</div>}

      <div className="contract-workspace__lifecycle" aria-label={`Contract lifecycle: ${detail.state}`}>
        <div className="contract-workspace__lifecycle-line"><span style={{ width: `${lifecycleProgress}%` }} /></div>
        {LIFECYCLE_STATES.map((state, index) => <div key={state} className={`contract-workspace__lifecycle-step ${index <= lifecycleIndex ? 'is-complete' : ''} ${state === detail.state ? 'is-current' : ''}`}><span>{index <= lifecycleIndex ? '✓' : index + 1}</span><small>{state.replace('_', ' ')}</small></div>)}
      </div>

      <section style={{ marginBottom: '24px', border: '1px solid #c4b5fd', borderRadius: '10px', background: '#faf5ff', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <div><h3 style={{ margin: 0, fontSize: '16px', color: '#4c1d95' }}>Official contract content</h3><span style={{ fontSize: '12px', color: '#6b21a8' }}>{activeVersion ? `Version ${activeVersion.version_number} · immutable official version` : 'No content yet'}</span></div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <button onClick={startEdit} style={btn('primary')}><Save size={14} /> Edit / add content</button>
            <button onClick={() => exportContract('docx')} disabled={!!exporting} style={btn('outline')}>{exporting === 'docx' ? 'Exporting…' : 'Export Word'}</button>
            <button onClick={() => exportContract('pdf')} disabled={!!exporting} style={btn('outline')}>{exporting === 'pdf' ? 'Exporting…' : 'Export PDF'}</button>
          </div>
        </div>
        <pre style={{ margin: 0, maxHeight: '320px', overflow: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '13px', lineHeight: 1.55, color: '#334155', background: '#fff', border: '1px solid #e9d5ff', borderRadius: '7px', padding: '14px' }}>{activeVersion?.content || 'This contract has no document content yet. Click “Edit / add content” to create the first official version.'}</pre>
      </section>

      <div className="contract-workspace__overview" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        {/* Edit / metadata */}
        <div>
          <h3 style={{ fontSize: '15px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Save size={16} color="#7c3aed" /> Edit Contract
          </h3>
          {!editing ? (
            <div>
              <div style={kv()}><span>Title</span><strong>{detail.title}</strong></div>
              <div style={kv()}><span>Reference</span><strong>{detail.reference_number}</strong></div>
              <div style={kv()}><span>Counterparty</span><strong>{detail.counterparty}</strong></div>
              <div style={kv()}><span>State</span><strong>{detail.state}</strong></div>
              <div style={{ marginTop: '12px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button onClick={startEdit} style={btn('primary')}>Edit Metadata / Content</button>
                <select value={reviewProvider} onChange={e => setReviewProvider(e.target.value)} style={{ ...input(), width: 'auto', background: '#fff' }}>
                  <option value="rules">Rules reviewer</option>
                  <option value="llm">LLM reviewer</option>
                </select>
                <button onClick={runReview} disabled={reviewing} style={btn('primary')}>
                  <ShieldAlert size={14} /> {reviewing ? 'Reviewing…' : 'AI Review'}
                </button>
                <button onClick={runClauses} disabled={analyzing} style={btn('outline')}>
                  <FileSearch size={14} /> {analyzing ? 'Analyzing…' : 'Analyze Clauses'}
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={save} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={label()}>Title</label>
                <input value={title} onChange={e => setTitle(e.target.value)} required style={input()} />
              </div>
              <div>
                <label style={label()}>Reference Number</label>
                <input value={ref} onChange={e => setRef(e.target.value)} required style={input()} />
              </div>
              <div>
                <label style={label()}>Counterparty</label>
                <input value={counterparty} onChange={e => setCounterparty(e.target.value)} required style={input()} />
              </div>
              <ContractStructureEditor value={structure} onChange={setStructure} />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="submit" style={btn('primary')}>Save (new version)</button>
                <button type="button" onClick={() => setEditing(false)} style={btn('ghost')}>Cancel</button>
              </div>
            </form>
          )}

          {/* State transition */}
          <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <select value={newState} onChange={e => setNewState(e.target.value)} style={{ ...input(), width: 'auto', background: '#fff' }}>
              {NEW_STATES.map(s => <option key={s}>{s}</option>)}
            </select>
            <button onClick={transition} style={btn('outline')}>Set State</button>
          </div>

          <div className="contract-workspace__approval-summary">
            <div><div className="contract-workspace__eyebrow">Approval workflow</div><strong>{workflow ? workflow.current_step || 'In progress' : 'No active workflow'}</strong></div>
            {workflow ? <><span style={pill(workflow.status)}>{workflow.status}</span><span className="contract-workspace__approval-role">{workflow.current_step_role || 'Awaiting review'}</span></> : <span className="contract-workspace__approval-role">Start a workflow from the Contracts or Approval Inbox view.</span>}
          </div>
        </div>

        {/* Documents */}
        <div>
          <h3 style={{ fontSize: '15px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Upload size={16} color="#7c3aed" /> Documents ({documents.length})
          </h3>
          <form onSubmit={uploadDoc} style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '14px' }}>
            <div className="contract-workspace__upload" style={{ display: 'flex', gap: '8px' }}>
              <select value={docType} onChange={e => setDocType(e.target.value)} style={{ ...input(), width: '160px', background: '#fff' }}>
                <option value="attachment">Attachment</option>
                <option value="contract">Contract</option>
                <option value="amendment">Amendment</option>
              </select>
              <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} style={{ flex: 1, fontSize: '12px' }} />
              <button type="submit" disabled={uploading || !file} style={btn('primary')}>{uploading ? 'Uploading…' : 'Upload'}</button>
            </div>
          </form>
          {documents.length === 0 ? (
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>No documents uploaded for this contract.</div>
          ) : (
            documents.map(d => (
              <div key={d.id} className="contract-workspace__document" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', borderRadius: '6px', border: '1px solid #e2e8f0', marginBottom: '6px', background: '#f8fafc' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={14} color="#7c3aed" />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>{d.title}</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>{d.doc_type} · {d.version_count || 1} version(s)</div>
                  </div>
                </div>
                <span style={{ fontSize: '11px', color: '#64748b' }}>{new Date(d.created_at).toLocaleDateString()}</span>
                <button
                  onClick={() => downloadAuthenticated(`/api/v1/documents/${d.id}/download`, headers, d.title)}
                  style={btn('outline')}
                  title="Download latest version"
                >
                  <Download size={14} /> Download
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Versions + AI review + clauses */}
      <div className="contract-workspace__analysis" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px' }}>
        <div>
          <h3 style={{ fontSize: '15px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <History size={16} color="#7c3aed" /> Versions
          </h3>
          {versions.length === 0 ? (
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>No versions yet.</div>
          ) : (
            versions.map(v => (
              <div key={v.id} style={{ ...docBox(), display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px', color: '#0f172a' }}>v{v.version_number}{v.is_active ? ' (active)' : ''}</div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>{new Date(v.created_at).toLocaleString()}</div>
                </div>
                {v.content && <div style={{ fontSize: '11px', color: '#7c3aed', fontWeight: 600 }}>{v.content.length.toLocaleString()} chars</div>}
              </div>
            ))
          )}
        </div>

        <div>
          <h3 style={{ fontSize: '15px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} color="#d97706" /> AI Review
          </h3>
          {!review ? (
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>Run "AI Review" to analyze the active version's content.</div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <span style={pill(review.overall_risk_level)}>{review.overall_risk_level}</span>
                <span style={{ fontSize: '12px', color: '#64748b' }}>provider {review.provider} · v{review.version_number}</span>
              </div>
              {review.provider === 'llm' && (review.findings || []).length === 0 && (
                <div style={{ fontSize: '11px', color: '#92400e', background: '#fef3c7', padding: '6px 10px', borderRadius: '6px', marginBottom: '10px' }}>
                  LLM provided no findings — ensure <code>ECLMS_LLM_API_URL</code> / <code>ECLMS_LLM_API_KEY</code> are configured.
                </div>
              )}
              {(review.findings || []).length === 0 ? (
                <div style={{ fontSize: '12px', color: '#94a3b8' }}>No findings.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
                  {review.findings.map((f: any, i: number) => (
                    <div key={i} style={{ padding: '10px', borderRadius: '8px', border: '1px solid #e2e8f0', borderLeft: '4px solid ' + riskSt(f.severity).color, background: '#f8fafc' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, fontSize: '12px', color: '#0f172a' }}>{f.title}</span>
                        <span style={pill(f.severity)}>{f.severity}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>{f.message}</div>
                      {f.suggestion && <div style={{ fontSize: '11px', color: '#166534', marginTop: '4px' }}>→ {f.suggestion}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div>
          <h3 style={{ fontSize: '15px', margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileSearch size={16} color="#7c3aed" /> Clause Analysis
          </h3>
          {!clauses ? (
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>Run "Analyze Clauses" to parse typed clauses from the text.</div>
          ) : (
            <div>
              {(clauses.missing_recommended_types || []).length > 0 && (
                <div style={{ marginBottom: '10px', fontSize: '12px' }}>
                  <span style={{ fontWeight: 600, color: '#92400e' }}>Missing:</span>{' '}
                  {clauses.missing_recommended_types.map((m: string) => (
                    <span key={m} style={{ background: '#fef3c7', color: '#92400e', padding: '2px 8px', borderRadius: '10px', fontWeight: 600, marginRight: '4px', fontSize: '11px' }}>{m}</span>
                  ))}
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
                {(clauses.clauses || []).map((cl: any, i: number) => (
                  <div key={i} style={{ padding: '10px', borderRadius: '8px', border: '1px solid #e2e8f0', background: '#f8fafc' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, fontSize: '12px', color: '#0f172a' }}>{cl.title}</span>
                      <span style={pill(cl.risk_level)}>{cl.risk_level}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>{cl.analysis_notes}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: '24px', borderTop: '1px solid #e2e8f0', paddingTop: '18px' }}>
        <h3 style={{ fontSize: '15px', margin: '0 0 12px' }}>Review feedback and manager merge</h3>
        {feedback.length === 0 ? <div style={{ fontSize: '12px', color: '#94a3b8' }}>No legal or financial feedback has been submitted.</div> : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {feedback.map(item => <div key={item.id} style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px', background: item.status === 'OPEN' ? '#fff' : '#f8fafc' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}><strong>{item.reviewer_role} · {item.kind}</strong><span style={pill(item.status)}>{item.status}</span></div>
              <div style={{ fontSize: '12px', color: '#475569', margin: '6px 0' }}>{item.body}</div>
              {item.proposed_text && <pre style={{ whiteSpace: 'pre-wrap', fontSize: '11px', background: '#f1f5f9', padding: '8px', borderRadius: '5px' }}>{item.proposed_text}</pre>}
              {item.status === 'OPEN' && <div style={{ display: 'flex', gap: '6px' }}>
                {item.kind === 'SUGGESTION' && <button onClick={() => { setMergeTarget(item); setMergeContent(item.proposed_text || ''); }} style={btn('primary')}>Merge as new version</button>}
                <button onClick={() => decideFeedback(item, 'ACCEPTED')} style={btn('outline')}>Accept</button>
                <button onClick={() => decideFeedback(item, 'REJECTED')} style={btn('ghost')}>Reject</button>
              </div>}
            </div>)}
          </div>
        )}
        {mergeTarget && <form onSubmit={mergeFeedback} style={{ marginTop: '14px', padding: '12px', background: '#f5f3ff', borderRadius: '8px' }}>
          <strong style={{ fontSize: '13px' }}>Review the official version before publishing</strong>
          <textarea value={mergeContent} onChange={e => setMergeContent(e.target.value)} rows={8} required style={{ ...input(), margin: '10px 0', fontFamily: 'monospace', fontSize: '12px' }} />
          <div style={{ display: 'flex', gap: '8px' }}><button type="submit" style={btn('primary')}>Publish new official version</button><button type="button" onClick={() => setMergeTarget(null)} style={btn('ghost')}>Cancel</button></div>
        </form>}
      </div>
    </div>
  );
}

const btn = (kind: string, pad?: string): React.CSSProperties => {
  const base: React.CSSProperties = { border: 'none', padding: pad || '6px 12px', borderRadius: '6px', fontWeight: 600, fontSize: '13px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' };
  switch (kind) {
    case 'primary': return { ...base, background: '#7c3aed', color: '#fff' };
    case 'outline': return { ...base, background: '#fff', color: '#334155', border: '1px solid #cbd5e1' };
    case 'ghost': return { ...base, background: 'none', color: '#64748b' };
    default: return { ...base, background: '#fff', color: '#334155' };
  }
};
const pill = (s: string) => ({ padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700, ...stateSt(s) });
const input = (): React.CSSProperties => ({ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' });
const label = (): React.CSSProperties => ({ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' });
const banner = (bg: string, color: string): React.CSSProperties => ({ background: bg, color, padding: '10px', borderRadius: '6px', marginBottom: '16px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' });
const emptyBox = (): React.CSSProperties => ({ background: '#fff', padding: '40px', textAlign: 'center', borderRadius: '10px', border: '1px solid #e2e8f0', color: '#64748b' });
const kv = (): React.CSSProperties => ({ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f1f5f9', fontSize: '13px' });
const docBox = (): React.CSSProperties => ({ padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0', background: '#f8fafc', marginBottom: '6px' });
