import { ArrowRight, Bell, CheckCircle2, ClipboardCheck, FileText, GitBranch, ShieldAlert, TrendingUp, Wallet, Zap } from 'lucide-react';

interface Props {
  reporting: any;
  riskOverview: any;
  alerts: any[];
  notifications: any[];
  contracts: any[];
  onNavigate: (tab: string) => void;
  onOpenContract: (contractId: string) => void;
}

const card: React.CSSProperties = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '18px' };
const button: React.CSSProperties = { border: 'none', borderRadius: '7px', padding: '9px 12px', fontWeight: 700, fontSize: '12px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '7px' };

const severityStyle = (severity: string) => {
  if (severity === 'CRITICAL') return { background: '#fee2e2', color: '#991b1b' };
  if (severity === 'HIGH') return { background: '#ffedd5', color: '#9a3412' };
  return { background: '#fef3c7', color: '#92400e' };
};

const titleCase = (value: string) => value.toLowerCase().replace(/(^|_)./g, match => match.toUpperCase()).replaceAll('_', ' ');

export default function DashboardTab({ reporting, riskOverview, alerts, notifications, contracts, onNavigate, onOpenContract }: Props) {
  const contractReport = reporting?.contracts || {};
  const workflowReport = reporting?.workflows || {};
  const obligationReport = reporting?.obligations || {};
  const financeReport = reporting?.finances || {};
  const unread = notifications.filter(item => !item.is_read).length;
  const criticalAlerts = alerts.filter(item => item.severity === 'CRITICAL').length;
  const highRisk = riskOverview?.high_or_critical_risk_contracts || 0;
  const activeContracts = contractReport.active || contractReport.by_state?.ACTIVE || 0;
  const pendingWorkflows = workflowReport.by_status?.RUNNING || workflowReport.running || 0;
  const overdueObligations = obligationReport.overdue_count || obligationReport.by_status?.OVERDUE || 0;
  const overduePayments = financeReport.overdue_payments || 0;
  const displayAlerts = alerts.slice(0, 6);
  const recentNotifications = notifications.slice(0, 5);
  const stateEntries = Object.entries(contractReport.by_state || {}) as [string, number][];
  const maxStateCount = Math.max(1, ...stateEntries.map(([, value]) => value));
  const paid = financeReport.paid || 0;
  const exposure = financeReport.active_exposure || 0;
  const totalValue = financeReport.total_value || paid + exposure || 1;
  const trends = (reporting?.trends || []) as Array<{ month: string; contracts_created: number; payments_scheduled: number; payments_paid: number; obligations_due: number }>;
  const maxTrendValue = Math.max(1, ...trends.map(item => Math.max(item.contracts_created, item.obligations_due)));

  return (
    <div>
      <section className="dashboard-hero" style={{ background: 'linear-gradient(135deg, #312e81 0%, #7c3aed 58%, #a855f7 100%)', borderRadius: '16px', padding: '28px 30px', color: '#fff', marginBottom: '22px', display: 'flex', justifyContent: 'space-between', gap: '24px', alignItems: 'center', boxShadow: '0 12px 28px rgba(91, 33, 182, .18)' }}>
        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', opacity: .8, marginBottom: '8px' }}>Enterprise command center</div>
          <h2 style={{ fontSize: '26px', lineHeight: 1.15, margin: 0, maxWidth: '630px', color: '#fff' }}>Know what needs attention across your contract portfolio.</h2>
          <p style={{ color: '#ede9fe', margin: '10px 0 0', fontSize: '14px', maxWidth: '610px' }}>One place for approvals, obligations, financial exposure, risk signals, and recent activity.</p>
          <div style={{ display: 'flex', gap: '9px', marginTop: '18px', flexWrap: 'wrap' }}>
            <button onClick={() => onNavigate('contracts')} style={{ ...button, background: '#fff', color: '#5b21b6' }}><FileText size={14} /> Open contracts</button>
            <button onClick={() => onNavigate('approvals')} style={{ ...button, background: 'rgba(255,255,255,.14)', color: '#fff', border: '1px solid rgba(255,255,255,.3)' }}><GitBranch size={14} /> Review approvals</button>
          </div>
        </div>
        <div className="dashboard-hero__risk" style={{ minWidth: '145px', height: '145px', borderRadius: '50%', background: `conic-gradient(#c4b5fd ${Math.min(100, Math.max(8, 100 - (highRisk * 12)))}%, rgba(255,255,255,.18) 0)`, display: 'grid', placeItems: 'center' }}>
          <div style={{ width: '108px', height: '108px', borderRadius: '50%', background: '#4c1d95', display: 'grid', placeItems: 'center', textAlign: 'center' }}><div><strong style={{ display: 'block', fontSize: '28px' }}>{highRisk}</strong><span style={{ fontSize: '11px', color: '#ddd6fe' }}>high-risk contracts</span></div></div>
        </div>
      </section>

      <div className="dashboard-stat-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '13px', marginBottom: '20px' }}>
        {[
          { label: 'Total contracts', value: contractReport.total_contracts ?? contracts.length, icon: FileText, color: '#4f46e5', action: 'contracts' },
          { label: 'Approvals in progress', value: pendingWorkflows, icon: GitBranch, color: '#0891b2', action: 'approvals' },
          { label: 'Overdue obligations', value: overdueObligations, icon: ClipboardCheck, color: '#ea580c', action: 'obligations' },
          { label: 'Overdue payments', value: overduePayments, icon: Wallet, color: '#dc2626', action: 'finances' },
        ].map(item => { const Icon = item.icon; return <button key={item.label} onClick={() => onNavigate(item.action)} style={{ ...card, textAlign: 'left', cursor: 'pointer', transition: 'transform .15s', borderTop: `3px solid ${item.color}` }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}><span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>{item.label}</span><Icon size={18} color={item.color} /></div><strong style={{ display: 'block', fontSize: '28px', color: '#0f172a', marginTop: '12px' }}>{item.value}</strong><span style={{ fontSize: '11px', color: '#94a3b8' }}>View details <ArrowRight size={11} style={{ verticalAlign: '-1px' }} /></span></button>; })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(300px, .65fr)', gap: '18px' }}>
        <section style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}><div><h3 style={{ margin: 0, fontSize: '16px' }}>Action center</h3><p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '12px' }}>Signals that deserve a decision or follow-up.</p></div><button onClick={() => onNavigate('intelligence')} style={{ ...button, background: '#f1f5f9', color: '#475569' }}>View intelligence <ArrowRight size={13} /></button></div>
          {displayAlerts.length === 0 ? <div style={{ textAlign: 'center', padding: '28px 10px', color: '#64748b' }}><CheckCircle2 size={28} color="#16a34a" /><div style={{ fontWeight: 700, marginTop: '8px', color: '#334155' }}>Portfolio is clear</div><div style={{ fontSize: '12px', marginTop: '4px' }}>No predictive alerts in the current horizon.</div></div> : <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>{displayAlerts.map((alert, index) => <button key={`${alert.entity_id || alert.contract_id}-${index}`} onClick={() => alert.contract_id ? onOpenContract(alert.contract_id) : onNavigate(alert.entity_type === 'payment' ? 'finances' : 'obligations')} style={{ display: 'grid', gridTemplateColumns: '28px 1fr auto', alignItems: 'center', gap: '10px', textAlign: 'left', border: '1px solid #f1f5f9', background: '#fafafa', borderRadius: '8px', padding: '10px', cursor: 'pointer' }}><span style={{ ...severityStyle(alert.severity), width: '26px', height: '26px', borderRadius: '7px', display: 'grid', placeItems: 'center' }}><ShieldAlert size={15} /></span><span><strong style={{ display: 'block', fontSize: '12px', color: '#334155' }}>{alert.message}</strong><span style={{ fontSize: '11px', color: '#94a3b8' }}>{titleCase(alert.alert_type)}</span></span><span style={{ ...severityStyle(alert.severity), fontSize: '10px', fontWeight: 800, borderRadius: '10px', padding: '3px 7px' }}>{alert.severity}</span></button>)}</div>}
        </section>

        <section style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}><div><h3 style={{ margin: 0, fontSize: '16px' }}>Recent activity</h3><p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '12px' }}>{unread} unread notification{unread === 1 ? '' : 's'}</p></div><Bell size={18} color="#7c3aed" /></div>
          {recentNotifications.length === 0 ? <div style={{ color: '#94a3b8', fontSize: '12px', padding: '24px 0', textAlign: 'center' }}>No recent activity yet.</div> : <div style={{ display: 'flex', flexDirection: 'column', gap: '11px' }}>{recentNotifications.map(item => <div key={item.id} style={{ display: 'flex', gap: '9px', alignItems: 'flex-start' }}><span style={{ width: '7px', height: '7px', marginTop: '5px', borderRadius: '50%', background: item.is_read ? '#cbd5e1' : '#7c3aed', flexShrink: 0 }} /><div style={{ minWidth: 0 }}><strong style={{ display: 'block', color: '#334155', fontSize: '12px' }}>{item.subject}</strong><span style={{ display: 'block', color: '#64748b', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.body}</span></div></div>)}</div>}
          <button onClick={() => onNavigate('notifications')} style={{ ...button, marginTop: '15px', background: '#f5f3ff', color: '#6d28d9', width: '100%', justifyContent: 'center' }}>Open activity feed <ArrowRight size={13} /></button>
        </section>
      </div>

      <section style={{ ...card, marginTop: '18px', background: '#f8fafc' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}><div><h3 style={{ margin: 0, fontSize: '15px' }}>Portfolio snapshot</h3><p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '12px' }}>A quick read on the operating state of your organization.</p></div><TrendingUp size={18} color="#0891b2" /></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '10px' }}>
          <div><span style={{ color: '#64748b', fontSize: '11px' }}>Active contracts</span><strong style={{ display: 'block', fontSize: '17px', marginTop: '3px' }}>{activeContracts}</strong></div>
          <div><span style={{ color: '#64748b', fontSize: '11px' }}>Risk score</span><strong style={{ display: 'block', fontSize: '17px', marginTop: '3px' }}>{riskOverview?.average_portfolio_risk_score ?? 0}<small style={{ fontSize: '11px', color: '#64748b' }}> / 100</small></strong></div>
          <div><span style={{ color: '#64748b', fontSize: '11px' }}>High-risk signals</span><strong style={{ display: 'block', fontSize: '17px', marginTop: '3px', color: highRisk ? '#dc2626' : '#166534' }}>{highRisk}</strong></div>
          <div><span style={{ color: '#64748b', fontSize: '11px' }}>Critical alerts</span><strong style={{ display: 'block', fontSize: '17px', marginTop: '3px', color: criticalAlerts ? '#dc2626' : '#166534' }}>{criticalAlerts}</strong></div>
        </div>
      </section>

      <section className="dashboard-chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '18px', marginTop: '18px' }}>
        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}><div><h3 style={{ margin: 0, fontSize: '15px' }}>Contract lifecycle mix</h3><p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '12px' }}>Where the portfolio stands today.</p></div><FileText size={18} color="#4f46e5" /></div>
          {stateEntries.length === 0 ? <div style={{ color: '#94a3b8', fontSize: '12px', padding: '16px 0' }}>Create contracts to see lifecycle distribution.</div> : <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>{stateEntries.map(([state, count]) => <div key={state}><div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#475569', marginBottom: '4px' }}><span>{state.replace('_', ' ')}</span><strong>{count}</strong></div><div style={{ height: '7px', background: '#eef2ff', borderRadius: '6px', overflow: 'hidden' }}><div style={{ width: `${(count / maxStateCount) * 100}%`, height: '100%', background: state === 'ACTIVE' ? '#22c55e' : state === 'REJECTED' ? '#ef4444' : '#8b5cf6', borderRadius: '6px' }} /></div></div>)}</div>}
        </div>
        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}><div><h3 style={{ margin: 0, fontSize: '15px' }}>Financial exposure</h3><p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '12px' }}>Paid value versus active exposure.</p></div><Wallet size={18} color="#0891b2" /></div>
          <div style={{ height: '13px', background: '#e0f2fe', borderRadius: '10px', overflow: 'hidden', display: 'flex', margin: '18px 0' }}><div style={{ width: `${Math.min(100, (paid / totalValue) * 100)}%`, background: '#22c55e' }} /><div style={{ flex: 1, background: '#f59e0b' }} /></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}><div><span style={{ display: 'block', color: '#64748b', fontSize: '11px' }}>Paid</span><strong style={{ color: '#166534', fontSize: '18px' }}>${paid.toLocaleString()}</strong></div><div><span style={{ display: 'block', color: '#64748b', fontSize: '11px' }}>Active exposure</span><strong style={{ color: '#b45309', fontSize: '18px' }}>${exposure.toLocaleString()}</strong></div></div>
        </div>
      </section>

      <section style={{ ...card, marginTop: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}><div><h3 style={{ margin: 0, fontSize: '15px' }}>Portfolio momentum</h3><p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '12px' }}>Monthly activity across contracts, obligations, and scheduled cash.</p></div><TrendingUp size={18} color="#0891b2" /></div>
        {trends.length === 0 ? <div style={{ color: '#94a3b8', fontSize: '12px', padding: '18px 0' }}>Trend data will appear as portfolio activity accumulates.</div> : <div style={{ display: 'grid', gridTemplateColumns: `repeat(${trends.length}, minmax(40px, 1fr))`, gap: '10px', alignItems: 'end', minHeight: '145px' }}>{trends.map(item => <div key={item.month} style={{ display: 'flex', flexDirection: 'column', gap: '7px', alignItems: 'center', height: '100%' }}><div style={{ display: 'flex', alignItems: 'end', gap: '3px', height: '92px', width: '100%', justifyContent: 'center' }}><div title={`${item.contracts_created} contracts created`} style={{ width: '9px', height: `${Math.max(5, (item.contracts_created / maxTrendValue) * 92)}px`, background: '#6366f1', borderRadius: '4px 4px 1px 1px' }} /><div title={`${item.obligations_due} obligations due`} style={{ width: '9px', height: `${Math.max(5, (item.obligations_due / maxTrendValue) * 92)}px`, background: '#f59e0b', borderRadius: '4px 4px 1px 1px' }} /></div><span style={{ fontSize: '10px', color: '#64748b' }}>{item.month.slice(5)}</span><span style={{ fontSize: '10px', color: '#94a3b8' }}>${Math.round(item.payments_scheduled).toLocaleString()}</span></div>)}</div>}
        <div style={{ display: 'flex', gap: '15px', marginTop: '12px', fontSize: '11px', color: '#64748b' }}><span><i style={{ display: 'inline-block', width: '8px', height: '8px', background: '#6366f1', borderRadius: '2px', marginRight: '5px' }} />Contracts created</span><span><i style={{ display: 'inline-block', width: '8px', height: '8px', background: '#f59e0b', borderRadius: '2px', marginRight: '5px' }} />Obligations due</span><span><i style={{ display: 'inline-block', width: '8px', height: '8px', background: '#22c55e', borderRadius: '2px', marginRight: '5px' }} />Payment value</span></div>
      </section>

      <div style={{ display: 'flex', gap: '9px', flexWrap: 'wrap', marginTop: '18px' }}><button onClick={() => onNavigate('imports')} style={{ ...button, background: '#ede9fe', color: '#6d28d9' }}><Zap size={14} /> Import data</button><button onClick={() => onNavigate('integrations')} style={{ ...button, background: '#cffafe', color: '#155e75' }}><ArrowRight size={14} /> Run an integration</button></div>
    </div>
  );
}
