import { ArrowRight, Brain, CheckCircle2, Plug, Settings2, Shield, Users } from 'lucide-react';

interface Props {
  user: { full_name: string; organization_id: string; roles?: string[] } | null;
  users: Array<{ id: string; full_name: string; roles?: string[] }>;
  onNavigate: (tab: string) => void;
  onOpenSettings: () => void;
}

const card: React.CSSProperties = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '18px' };
const button: React.CSSProperties = { border: 'none', borderRadius: '7px', padding: '9px 12px', fontWeight: 700, fontSize: '12px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '7px' };

export default function AdminCenterTab({ user, users, onNavigate, onOpenSettings }: Props) {
  const roles = user?.roles || [];
  return (
    <div>
      <section style={{ background: 'linear-gradient(135deg, #0f172a, #334155)', color: '#fff', borderRadius: '16px', padding: '26px 28px', marginBottom: '18px' }}>
        <div style={{ fontSize: '11px', letterSpacing: '.08em', textTransform: 'uppercase', opacity: .7, fontWeight: 700 }}>Administration</div>
        <h2 style={{ margin: '8px 0 6px', fontSize: '24px' }}>Keep the workspace governed and ready.</h2>
        <p style={{ margin: 0, color: '#cbd5e1', fontSize: '13px', maxWidth: '650px' }}>Manage access, intelligence settings, and connected systems from one operational control surface.</p>
      </section>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '14px', marginBottom: '18px' }}>
        <section style={card}><Users size={20} color="#4f46e5" /><div style={{ color: '#64748b', fontSize: '12px', marginTop: '14px' }}>Organization users</div><strong style={{ display: 'block', fontSize: '25px', marginTop: '3px' }}>{users.length}</strong><button onClick={() => onNavigate('users')} style={{ ...button, marginTop: '13px', background: '#eef2ff', color: '#4338ca' }}>Manage access <ArrowRight size={13} /></button></section>
        <section style={card}><Brain size={20} color="#7c3aed" /><div style={{ color: '#64748b', fontSize: '12px', marginTop: '14px' }}>AI review configuration</div><strong style={{ display: 'block', fontSize: '16px', marginTop: '7px' }}>Workspace intelligence</strong><button onClick={onOpenSettings} style={{ ...button, marginTop: '13px', background: '#f5f3ff', color: '#6d28d9' }}>Open settings <Settings2 size={13} /></button></section>
        <section style={card}><Plug size={20} color="#0891b2" /><div style={{ color: '#64748b', fontSize: '12px', marginTop: '14px' }}>Data connections</div><strong style={{ display: 'block', fontSize: '16px', marginTop: '7px' }}>ERP and accounting</strong><button onClick={() => onNavigate('integrations')} style={{ ...button, marginTop: '13px', background: '#ecfeff', color: '#0e7490' }}>Configure mappings <ArrowRight size={13} /></button></section>
      </div>
      <section style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', alignItems: 'start' }}><div><h3 style={{ margin: 0, fontSize: '15px' }}>Your administrative scope</h3><p style={{ color: '#64748b', fontSize: '12px', margin: '5px 0 0' }}>{user?.full_name || 'Current user'} · organization {user?.organization_id || '—'}</p></div><Shield size={20} color="#64748b" /></div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '18px' }}>{roles.length ? roles.map(role => <span key={role} style={{ background: '#f1f5f9', color: '#334155', borderRadius: '999px', padding: '6px 10px', fontSize: '11px', fontWeight: 700 }}>{role}</span>) : <span style={{ background: '#f1f5f9', color: '#334155', borderRadius: '999px', padding: '6px 10px', fontSize: '11px', fontWeight: 700 }}>Authenticated administrator</span>}</div>
        <div style={{ display: 'flex', gap: '9px', alignItems: 'center', marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #f1f5f9', color: '#166534', fontSize: '12px' }}><CheckCircle2 size={15} /> Configuration changes are scoped to the authenticated workspace.</div>
      </section>
    </div>
  );
}
