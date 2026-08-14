import React, { useEffect, useState } from 'react';
import { Plus, RefreshCw, X, CheckCircle2, AlertCircle, Download, Search } from 'lucide-react';
import { downloadAuthenticated } from '../download';

interface Props {
  headers: Record<string, string>;
  contracts?: { id: string; title: string }[];
}

interface Commitment {
  id: string;
  contract_id: string;
  description: string;
  amount: number;
  currency: string;
  status: string;
  created_at?: string;
}

interface Payment {
  id: string;
  commitment_id: string;
  amount: number;
  due_date: string;
  status: string;
  paid_at?: string;
  created_at?: string;
}

const st = (s: string) => {
  switch (s) {
    case 'PAID': return { bg: '#dcfce7', color: '#166534' };
    case 'SCHEDULED': return { bg: '#dbeafe', color: '#1e40af' };
    case 'OVERDUE': return { bg: '#fee2e2', color: '#991b1b' };
    case 'CANCELLED': return { bg: '#f1f5f9', color: '#475569' };
    case 'OPEN': return { bg: '#dbeafe', color: '#1e40af' };
    default: return { bg: '#f1f5f9', color: '#475569' };
  }
};

export default function FinancesTab({ headers, contracts = [] }: Props) {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [payments, setPayments] = useState<Record<string, Payment[]>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [contractId, setContractId] = useState('');

  const [pAmount, setPAmount] = useState('');
  const [pDueDate, setPDueDate] = useState('');
  const [pTarget, setPTarget] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');

  const api = async (path: string, opts: RequestInit = {}) => {
    const res = await fetch(path, { ...opts, headers });
    const data = await res.json();
    if (!data.success) throw new Error(data.error?.message || 'Request failed');
    return data.data;
  };

  const load = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await api('/api/v1/finances/commitments');
      setCommitments(data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load commitments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const loadPayments = async (cid: string) => {
    try {
      const d = await api(`/api/v1/finances/commitments/${cid}/payments`);
      setPayments(prev => ({ ...prev, [cid]: d.items || [] }));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const toggle = (cid: string) => {
    const next = !expanded[cid];
    setExpanded(prev => ({ ...prev, [cid]: next }));
    if (next) loadPayments(cid);
  };

  const createCommitment = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setMsg('');
    if (!contractId) return setError('Select a contract');
    try {
      await api('/api/v1/finances/commitments', {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ contract_id: contractId, description, amount: Number(amount), currency }),
      });
      setDescription(''); setAmount(''); setContractId('');
      setMsg('Commitment created');
      load(true);
    } catch (e: any) { setError(e.message); }
  };

  const createPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pTarget) return;
    setError(''); setMsg('');
    try {
      await api(`/api/v1/finances/commitments/${pTarget}/payments`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: Number(pAmount), due_date: new Date(pDueDate).toISOString() }),
      });
      setPAmount(''); setPDueDate(''); setPTarget(null);
      setMsg('Payment scheduled');
      loadPayments(pTarget);
      load(true);
    } catch (e: any) { setError(e.message); }
  };

  const act = async (action: string, id: string, msgText: string) => {
    setError(''); setMsg('');
    try {
      await api(`/api/v1/finances/payments/${id}/${action}`, { method: 'POST' });
      setMsg(msgText);
      load(true);
      Object.keys(payments).forEach(cid => {
        if (payments[cid]?.some(p => p.id === id)) loadPayments(cid);
      });
    } catch (e: any) { setError(e.message); }
  };

  const sweep = async () => {
    setError(''); setMsg('');
    try {
      const d = await api('/api/v1/finances/sweep-overdue', { method: 'POST' });
      setMsg(`Marked ${d.overdue} overdue payment(s)`);
      load(true);
    } catch (e: any) { setError(e.message); }
  };

  const contractTitle = (id: string) => contracts.find(c => c.id === id)?.title || id.slice(0, 8);

  const visible = commitments.filter(c => {
    const q = filterText.toLowerCase();
    return !q || c.description.toLowerCase().includes(q) || c.status.toLowerCase().includes(q) || contractTitle(c.contract_id).toLowerCase().includes(q);
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', margin: 0 }}>Financial Commitments & Payments</h2>
          <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0' }}>Track commitments, payment schedules, and mark installments paid.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={sweep} style={btn('outline')}>Sweep Overdue</button>
          <button onClick={() => downloadAuthenticated('/api/v1/reporting/export.csv', headers, 'eclms-report.csv')} style={btn('outline')}><Download size={14} /> Export CSV</button>
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
            <div style={emptyBox()}>Loading commitments…</div>
          ) : visible.length === 0 ? (
            <div style={emptyBox()}>No commitments{filterText ? ' match your filter' : ''}. Create one using the form.</div>
          ) : (
            visible.map(c => (
              <div key={c.id} style={card()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => toggle(c.id)}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>{c.description}</div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>Contract: {contractTitle(c.contract_id)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a' }}>{c.currency} {Number(c.amount).toLocaleString()}</div>
                    <span style={pill(c.status)}>{c.status}</span>
                  </div>
                </div>

                {expanded[c.id] && (
                  <div style={{ marginTop: '16px', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <h4 style={{ margin: 0, fontSize: '13px', color: '#334155' }}>Payment Schedule</h4>
                      <button onClick={() => setPTarget(c.id)} style={btn('solid')}><Plus size={14} /> Add Payment</button>
                    </div>
                    {pTarget === c.id && (
                      <form onSubmit={createPayment} style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                        <input type="number" step="0.01" placeholder="Amount" value={pAmount} onChange={e => setPAmount(e.target.value)} required style={input()} />
                        <input type="date" value={pDueDate} onChange={e => setPDueDate(e.target.value)} required style={input()} />
                        <button type="submit" style={btn('primary')}>Add</button>
                        <button type="button" onClick={() => setPTarget(null)} style={btn('ghost')}><X size={14} /></button>
                      </form>
                    )}
                    {(payments[c.id] || []).length === 0 ? (
                      <div style={{ fontSize: '12px', color: '#94a3b8' }}>No payment installments for this commitment.</div>
                    ) : payments[c.id].map(p => (
                      <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', borderRadius: '6px', border: '1px solid #e2e8f0', marginBottom: '6px', background: '#f8fafc' }}>
                        <div>
                          <span style={{ fontWeight: 600, fontSize: '13px' }}>{c.currency} {Number(p.amount).toLocaleString()}</span>
                          <span style={{ color: '#64748b', fontSize: '12px', marginLeft: '8px' }}>due {new Date(p.due_date).toLocaleDateString()}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={pill(p.status)}>{p.status}</span>
                          {p.status === 'SCHEDULED' && (
                            <button onClick={() => act('pay', p.id, 'Payment marked paid')} style={btn('ok')}><CheckCircle2 size={14} /> Pay</button>
                          )}
                          {(p.status === 'SCHEDULED' || p.status === 'OVERDUE') && (
                            <button onClick={() => act('cancel', p.id, 'Payment cancelled')} style={btn('danger')}><X size={14} /> Cancel</button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div>
          <div style={{ ...card(), padding: '24px' }}>
            <h3 style={{ fontSize: '16px', margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} color="#7c3aed" /> New Commitment
            </h3>
            <form onSubmit={createCommitment} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={label()}>Contract</label>
                <select value={contractId} onChange={e => setContractId(e.target.value)} style={{ ...input(), background: '#fff' }}>
                  <option value="">— Select contract —</option>
                  {contracts.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
                </select>
              </div>
              <div>
                <label style={label()}>Description</label>
                <input type="text" value={description} onChange={e => setDescription(e.target.value)} required placeholder="e.g. Annual license fee" style={input()} />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <div style={{ flex: 2 }}>
                  <label style={label()}>Amount</label>
                  <input type="number" step="0.01" min="0.01" value={amount} onChange={e => setAmount(e.target.value)} required style={input()} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={label()}>Currency</label>
                  <select value={currency} onChange={e => setCurrency(e.target.value)} style={{ ...input(), background: '#fff' }}>
                    <option>USD</option><option>EUR</option><option>GBP</option>
                  </select>
                </div>
              </div>
              <button type="submit" style={btn('primary', '10px')}>Create Commitment</button>
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
    case 'solid': return { ...base, background: '#7c3aed', color: '#fff' };
    case 'outline': return { ...base, background: '#fff', color: '#334155', border: '1px solid #cbd5e1' };
    case 'ghost': return { ...base, background: 'none', color: '#64748b' };
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
