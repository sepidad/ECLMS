import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock3, FileText, Filter, GitBranch, MessageSquare, RefreshCw, ShieldAlert, XCircle } from 'lucide-react';

interface Props {
  headers: Record<string, string>;
  user: { id: string; roles?: string[] } | null;
  contracts: { id: string; title: string; reference_number: string; counterparty: string; state: string }[];
  onOpenContract: (contractId: string) => void;
}

interface WorkflowStep {
  name: string;
  assigned_role: string;
  status: string;
  delegated_to?: string;
  escalated_at?: string;
  started_at?: string;
  timeout_hours?: number;
  escalation_role?: string;
  comment?: string;
}

interface Workflow {
  id: string;
  contract_id: string;
  status: string;
  definition_id: string;
  current_step?: string;
  current_step_role?: string;
  steps: WorkflowStep[];
}

const panel: React.CSSProperties = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '20px' };
const control: React.CSSProperties = { border: '1px solid #cbd5e1', borderRadius: '7px', padding: '8px 10px', fontSize: '12px', background: '#fff' };

const statusStyle = (status: string) => {
  if (status === 'ESCALATED') return { background: '#fee2e2', color: '#991b1b' };
  if (status === 'DELEGATED') return { background: '#ede9fe', color: '#6d28d9' };
  if (status === 'APPROVED') return { background: '#dcfce7', color: '#166534' };
  if (status === 'REJECTED') return { background: '#fee2e2', color: '#991b1b' };
  return { background: '#e0e7ff', color: '#3730a3' };
};

const dueText = (step: WorkflowStep) => {
  if (!step.started_at || !step.timeout_hours) return 'No SLA configured';
  const deadline = new Date(step.started_at).getTime() + step.timeout_hours * 60 * 60 * 1000;
  const hours = Math.round((deadline - Date.now()) / (60 * 60 * 1000));
  if (hours < 0) return `${Math.abs(hours)}h overdue`;
  if (hours < 24) return `${hours}h remaining`;
  return `${Math.ceil(hours / 24)}d remaining`;
};

export default function ApprovalInbox({ headers, user, contracts, onOpenContract }: Props) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [filter, setFilter] = useState('action');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [comment, setComment] = useState<Record<string, string>>({});
  const [deciding, setDeciding] = useState<string | null>(null);
  const roles = user?.roles || [];

  const api = async (path: string, options: RequestInit = {}) => {
    const response = await fetch(path, { ...options, headers });
    const data = await response.json();
    if (!data.success) throw new Error(data.error?.message || 'Request failed');
    return data.data;
  };

  const load = async () => {
    setLoading(true); setError('');
    try {
      const data = await api('/api/v1/workflows?status=RUNNING&limit=200');
      setWorkflows(data.items || []);
    } catch (e: any) { setError(e.message || 'Unable to load approval inbox'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const contractById = useMemo(() => new Map(contracts.map(contract => [contract.id, contract])), [contracts]);
  const rows = workflows.map(workflow => {
    const step = workflow.steps.find(item => item.name === workflow.current_step) || workflow.steps.find(item => ['PENDING', 'ESCALATED', 'DELEGATED'].includes(item.status));
    const canAct = Boolean(step && (roles.includes(step.assigned_role) || (step.status === 'ESCALATED' && step.escalation_role && roles.includes(step.escalation_role)) || (step.status === 'DELEGATED' && step.delegated_to === user?.id)));
    return { workflow, step, contract: contractById.get(workflow.contract_id), canAct };
  });
  const visibleRows = rows.filter(row => {
    if (filter === 'action') return row.canAct;
    if (filter === 'escalated') return row.step?.status === 'ESCALATED';
    if (filter === 'mine') return row.canAct && row.step?.assigned_role && roles.includes(row.step.assigned_role);
    return true;
  });
  const actionable = rows.filter(row => row.canAct).length;
  const escalated = rows.filter(row => row.step?.status === 'ESCALATED').length;
  const summary = [
    { label: 'Needs your decision', value: actionable, Icon: CheckCircle2, color: '#4f46e5' },
    { label: 'Escalated', value: escalated, Icon: ShieldAlert, color: '#dc2626' },
    { label: 'In progress', value: workflows.length, Icon: GitBranch, color: '#0891b2' },
  ];

  const decide = async (workflow: Workflow, step: WorkflowStep, decision: 'APPROVE' | 'REJECT') => {
    setDeciding(workflow.id); setError('');
    try {
      await api(`/api/v1/workflows/${workflow.id}/transition`, { method: 'POST', body: JSON.stringify({ decision, step_name: step.name, comment: comment[workflow.id] || undefined }) });
      setComment(prev => ({ ...prev, [workflow.id]: '' }));
      await load();
    } catch (e: any) { setError(e.message || 'Decision failed'); }
    finally { setDeciding(null); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', gap: '16px' }}>
        <div><h2 style={{ fontSize: '20px', margin: 0 }}>Approval Inbox</h2><p style={{ fontSize: '13px', color: '#64748b', margin: '5px 0 0' }}>Your daily queue of contract decisions, escalations, and SLA-sensitive work.</p></div>
        <button onClick={load} style={{ ...control, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '7px', fontWeight: 700, color: '#475569' }}><RefreshCw size={14} /> Refresh</button>
      </div>

      {error && <div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}><AlertCircle size={16} />{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '12px', marginBottom: '18px' }}>
        {summary.map(({ label, value, Icon, color }) => <div key={label} style={{ ...panel, borderTop: `3px solid ${color}` }}><div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '12px', fontWeight: 700 }}>{label}<Icon size={17} color={color} /></div><strong style={{ display: 'block', fontSize: '28px', marginTop: '10px' }}>{value}</strong></div>)}
      </div>

      <div style={{ ...panel, padding: '12px 14px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}><Filter size={15} color="#64748b" /><span style={{ fontSize: '12px', color: '#64748b', fontWeight: 700 }}>Show</span>{[['action', 'Needs my action'], ['mine', 'My role'], ['escalated', 'Escalated'], ['all', 'All running']].map(([value, label]) => <button key={value} onClick={() => setFilter(value)} style={{ ...control, cursor: 'pointer', background: filter === value ? '#ede9fe' : '#fff', color: filter === value ? '#6d28d9' : '#475569', borderColor: filter === value ? '#c4b5fd' : '#cbd5e1', fontWeight: filter === value ? 700 : 500 }}>{label}</button>)}</div>

      {loading && workflows.length === 0 ? <div style={{ ...panel, textAlign: 'center', color: '#64748b', padding: '44px' }}>Loading approval queue…</div> : visibleRows.length === 0 ? <div style={{ ...panel, textAlign: 'center', padding: '50px 20px' }}><CheckCircle2 size={34} color="#16a34a" /><h3 style={{ margin: '12px 0 5px', fontSize: '16px' }}>You’re all caught up</h3><p style={{ margin: 0, color: '#64748b', fontSize: '13px' }}>{filter === 'action' ? 'No running approvals currently need your decision.' : 'No workflows match this filter.'}</p></div> : <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {visibleRows.map(({ workflow, step, contract, canAct }) => { if (!step) return null; const status = step.status || 'PENDING'; return <article key={workflow.id} style={{ ...panel, padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 18px', display: 'flex', justifyContent: 'space-between', gap: '14px', alignItems: 'flex-start', borderBottom: '1px solid #f1f5f9' }}>
            <div style={{ display: 'flex', gap: '12px', minWidth: 0 }}><div style={{ width: '36px', height: '36px', borderRadius: '9px', background: status === 'ESCALATED' ? '#fee2e2' : '#ede9fe', color: status === 'ESCALATED' ? '#dc2626' : '#7c3aed', display: 'grid', placeItems: 'center', flexShrink: 0 }}><GitBranch size={18} /></div><div style={{ minWidth: 0 }}><button onClick={() => contract && onOpenContract(contract.id)} style={{ border: 0, background: 'none', padding: 0, cursor: contract ? 'pointer' : 'default', textAlign: 'left', color: '#0f172a', fontWeight: 800, fontSize: '15px' }}>{contract?.title || `Contract ${workflow.contract_id.slice(0, 8)}`}</button><div style={{ color: '#64748b', fontSize: '11px', marginTop: '4px' }}>{contract?.reference_number || workflow.contract_id} · {contract?.counterparty || 'Unknown counterparty'}</div></div></div>
            <span style={{ ...statusStyle(status), borderRadius: '12px', padding: '4px 9px', fontSize: '10px', fontWeight: 800, whiteSpace: 'nowrap' }}>{status}</span>
          </div>
          <div style={{ padding: '14px 18px', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: '18px', alignItems: 'center' }}>
            <div><div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 700 }}>Current approval step</div><div style={{ display: 'flex', alignItems: 'center', gap: '9px', marginTop: '6px' }}><strong style={{ fontSize: '15px', color: '#334155' }}>{step.name}</strong><span style={{ fontSize: '11px', color: '#64748b' }}>assigned to {step.assigned_role}</span></div><div style={{ display: 'flex', gap: '14px', marginTop: '9px', fontSize: '11px', color: '#64748b', flexWrap: 'wrap' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><Clock3 size={13} /> {dueText(step)}</span>{step.escalation_role && <span><ShieldAlert size={13} style={{ verticalAlign: '-2px' }} /> Escalates to {step.escalation_role}</span>}{step.delegated_to && <span>Delegated to {step.delegated_to.slice(0, 8)}</span>}</div></div><div style={{ textAlign: 'right' }}><div style={{ fontSize: '11px', color: '#64748b' }}>Progress</div><strong style={{ fontSize: '14px', color: '#334155' }}>{workflow.steps.filter(item => ['APPROVED', 'SKIPPED'].includes(item.status)).length} / {workflow.steps.length}</strong></div>
          </div>
          {canAct && <div style={{ background: '#fafafa', borderTop: '1px solid #f1f5f9', padding: '12px 18px', display: 'flex', gap: '9px', alignItems: 'center' }}><MessageSquare size={15} color="#94a3b8" /><input value={comment[workflow.id] || ''} onChange={event => setComment(prev => ({ ...prev, [workflow.id]: event.target.value }))} placeholder="Add a decision note (optional)" style={{ ...control, flex: 1, minWidth: 120 }} /><button disabled={deciding === workflow.id} onClick={() => decide(workflow, step, 'REJECT')} style={{ ...control, cursor: 'pointer', color: '#b91c1c', borderColor: '#fecaca', fontWeight: 700, opacity: deciding === workflow.id ? .6 : 1 }}><XCircle size={14} /> Reject</button><button disabled={deciding === workflow.id} onClick={() => decide(workflow, step, 'APPROVE')} style={{ ...control, cursor: 'pointer', color: '#166534', background: '#dcfce7', borderColor: '#86efac', fontWeight: 700, opacity: deciding === workflow.id ? .6 : 1 }}><CheckCircle2 size={14} /> Approve</button></div>}
          {!canAct && <div style={{ padding: '10px 18px', borderTop: '1px solid #f1f5f9', color: '#94a3b8', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}><FileText size={13} /> Waiting for {step.assigned_role} to decide</div>}
        </article>; })}
      </div>}
    </div>
  );
}
