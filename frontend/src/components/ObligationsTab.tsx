import React, { useEffect, useState } from 'react';
import { Plus, RefreshCw, X, CheckCircle2, AlertCircle, Download, Search } from 'lucide-react';
import { downloadAuthenticated } from '../download';

interface Props {
  headers: Record<string, string>;
  contracts?: { id: string; title: string }[];
}

interface Obligation {
  id: string;
  contract_id: string;
  description: string;
  due_date: string;
  status: string;
  completed_at?: string;
  created_at?: string;
}

const st = (s: string) => {
  switch (s) {
    case 'OPEN': return { bg: '#dbeafe', color: '#1e40af' };
    case 'OVERDUE': return { bg: '#fee2e2', color: '#991b1b' };
    case 'COMPLETED': return { bg: '#dcfce7', color: '#166534' };
    case 'CANCELLED': return { bg: '#f1f5f9', color: '#475569' };
    default: return { bg: '#f1f5f9', color: '#475569' };
  }
};

export default function ObligationsTab({ headers, contracts = [] }: Props) {
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [filterText, setFilterText] = useState('');

  const [contractId, setContractId] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState('');

  const api = async (path: string, opts: RequestInit = {}) => {
    const res = await fetch(path, { ...opts, headers });
    const data = await res.json();
    if (!data.success) throw new Error(data.error?.message || 'Request failed');
    return data.data;
  };

  const load = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const q = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
      const data = await api(`/api/v1/obligations${q}`);
      setObligations(data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load obligations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [statusFilter]);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setMsg('');
    if (!contractId) return setError('Select a contract');
    try {
      await api('/api/v1/obligations', {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ contract_id: contractId, description, due_date: new Date(dueDate).toISOString() }),
      });
      setDescription(''); setDueDate(''); setContractId('');
      setMsg('Obligation created');
      load(true);
    } catch (e: any) { setError(e.message); }
  };

  const act = async (action: string, id: string, msgText: string) => {
    setError(''); setMsg('');
    try {
      await api(`/api/v1/obligations/${id}/${action}`, { method: 'POST' });
      setMsg(msgText);
      load(true);
    } catch (e: any) { setError(e.message); }
  };

  const sweep = async () => {
    setError(''); setMsg('');
    try {
      const d = await api('/api/v1/obligations/sweep-overdue', { method: 'POST' });
      setMsg(`Marked ${d.overdue} overdue obligation(s)`);
      load(true);
    } catch (e: any) { setError(e.message); }
  };

  const contractTitle = (id: string) => contracts.find(c => c.id === id)?.title || id.slice(0, 8);

  const visible = obligations.filter(o => {
    const q = filterText.toLowerCase();
    const matchesStatus = !statusFilter || o.status === statusFilter;
    return matchesStatus && (!q || o.description.toLowerCase().includes(q) || o.status.toLowerCase().includes(q) || contractTitle(o.contract_id).toLowerCase().includes(q));
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', margin: 0 }}>Contractual Obligations</h2>
          <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0' }}>Track deliverable obligations per contract and their completion.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', background: '#fff' }}>
            <option value="">All statuses</option>
            <option>OPEN</option><option>OVERDUE</option><option>COMPLETED</option><option>CANCELLED</option>
          </select>
          <button onClick={() => downloadAuthenticated('/api/v1/reporting/export.csv', headers, 'eclms-report.csv')} style={btn('outline')}><Download size={14} /> Export CSV</button>
          <button onClick={sweep} style={btn('outline')}>Sweep Overdue</button>
          <button onClick={() => load()} style={btn('outline')}><RefreshCw size={14} /> Refresh</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '16px' }}>
        <Search size={14} color="#64748b" />
        <input
          type="text"
          placeholder="Filter by description, status, or contract…"
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
          style={{ ...input(), maxWidth: '360px' }}
        />
      </div>

      {error && <div style={banner('#fee2e2', '#991b1b')}><AlertCircle size={16} /> {error}</div>}
      {msg && <div style={banner('#dcfce7', '#166534')}><CheckCircle2 size={16} /> {msg}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '32px' }}>
        <div>
          {loading ? (
            <div style={emptyBox()}>Loading obligations…</div>
          ) : visible.length === 0 ? (
            <div style={emptyBox()}>No obligations match your filters. Create one using the form.</div>
          ) : (
            visible.map(o => {
              const overdue = o.status === 'OVERDUE';
              return (
                <div key={o.id} style={{ ...card(), borderLeft: `4px solid ${overdue ? '#dc2626' : '#7c3aed'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600, color: '#0f172a' }}>{o.description}</div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>
                        Contract: {contractTitle(o.contract_id)} · Due {new Date(o.due_date).toLocaleDateString()}
                        {o.completed_at ? ` · Completed ${new Date(o.completed_at).toLocaleDateString()}` : ''}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={pill(o.status)}>{o.status}</span>
                      {(o.status === 'OPEN' || o.status === 'OVERDUE') && (
                        <button onClick={() => act('complete', o.id, 'Obligation completed')} style={btn('ok')}><CheckCircle2 size={14} /> Complete</button>
                      )}
                      {o.status !== 'COMPLETED' && (
                        <button onClick={() => act('cancel', o.id, 'Obligation cancelled')} style={btn('danger')}><X size={14} /> Cancel</button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div>
          <div style={{ ...card(), padding: '24px' }}>
            <h3 style={{ fontSize: '16px', margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} color="#7c3aed" /> New Obligation
            </h3>
            <form onSubmit={create} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={label()}>Contract</label>
                <select value={contractId} onChange={e => setContractId(e.target.value)} style={{ ...input(), background: '#fff' }}>
                  <option value="">— Select contract —</option>
                  {contracts.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
                </select>
              </div>
              <div>
                <label style={label()}>Description</label>
                <textarea value={description} onChange={e => setDescription(e.target.value)} required placeholder="e.g. Deliver signing documentation" rows={3} style={{ ...input(), resize: 'vertical' }} />
              </div>
              <div>
                <label style={label()}>Due Date</label>
                <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} required style={input()} />
              </div>
              <button type="submit" style={btn('primary', '10px')}>Create Obligation</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

const btn = (kind: string, pad?: string): React.CSSProperties => {
  const base: React.CSSProperties = { border: 'none', padding: pad || '6px 12px', borderRadius: '6px', fontWeight: 600, fontSize: '13px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' };
  switch (kind) {
    case 'primary': return { ...base, background: '#7c3aed', color: '#fff' };
    case 'outline': return { ...base, background: '#fff', color: '#334155', border: '1px solid #cbd5e1' };
    case 'ok': return { ...base, background: '#16a34a', color: '#fff' };
    case 'danger': return { ...base, background: '#f1f5f9', color: '#dc2626', border: '1px solid #cbd5e1' };
    default: return { ...base, background: '#fff', color: '#334155' };
  }
};
const pill = (s: string) => ({ padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700, ...st(s) });
const input = (): React.CSSProperties => ({ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', boxSizing: 'border-box' });
const label = (): React.CSSProperties => ({ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' });
const banner = (bg: string, color: string): React.CSSProperties => ({ background: bg, color, padding: '10px', borderRadius: '6px', marginBottom: '16px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' });
const emptyBox = (): React.CSSProperties => ({ background: '#fff', padding: '40px', textAlign: 'center', borderRadius: '10px', border: '1px solid #e2e8f0', color: '#64748b' });
const card = (): React.CSSProperties => ({ background: '#fff', padding: '16px 18px', borderRadius: '10px', border: '1px solid #e2e8f0', marginBottom: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' });