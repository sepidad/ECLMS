import React from 'react';
import { ArrowRight, Brain, CheckCircle2, Plug, Settings2, Shield, Users } from 'lucide-react';

interface Props {
  headers: Record<string, string>;
  user: { full_name: string; organization_id: string; roles?: string[] } | null;
  users: Array<{ id: string; full_name: string; roles?: string[] }>;
  onNavigate: (tab: string) => void;
  onOpenSettings: () => void;
}

const card: React.CSSProperties = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '18px' };
const button: React.CSSProperties = { border: 'none', borderRadius: '7px', padding: '9px 12px', fontWeight: 700, fontSize: '12px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '7px' };

export default function AdminCenterTab({ user, users, headers, onNavigate, onOpenSettings }: Props) {
  const roles = user?.roles || [];
  const [role, setRole] = React.useState('CONTRACT_MANAGER');
  const [permissions, setPermissions] = React.useState<{ code: string; description: string; enabled: boolean }[]>([]);
  const [saving, setSaving] = React.useState(false);
  const [selectedUser, setSelectedUser] = React.useState('');
  const [userPermissions, setUserPermissions] = React.useState<{ code: string; description: string; enabled: boolean }[]>([]);
  React.useEffect(() => { fetch(`/api/v1/identity/roles/${role}/permissions`, { headers }).then(r => r.json()).then(d => { if (d.success) { const enabled = new Set(d.data.permissions); setPermissions((d.data.all_permissions || []).map((p: any) => ({ ...p, enabled: enabled.has(p.code) }))); } }); }, [role]);
  const savePermissions = async () => { setSaving(true); await fetch(`/api/v1/identity/roles/${role}/permissions`, { method: 'PUT', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ permissions: permissions.filter(p => p.enabled).map(p => p.code) }) }); setSaving(false); };
  const loadUserPermissions = async (userId: string) => { setSelectedUser(userId); const response = await fetch(`/api/v1/identity/users/${userId}/permissions`, { headers }); const data = await response.json(); if (data.success) { const enabled = new Set(data.data.effective); setUserPermissions((data.data.all_permissions || []).map((p: any) => ({ ...p, enabled: enabled.has(p.code) }))); } };
  const saveUserPermissions = async () => { if (!selectedUser) return; setSaving(true); await fetch(`/api/v1/identity/users/${selectedUser}/permissions`, { method: 'PUT', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ permissions: Object.fromEntries(userPermissions.map(p => [p.code, p.enabled])) }) }); setSaving(false); };
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
      <section style={{ ...card, marginTop: '18px' }}>
        <h3 style={{ margin: 0, fontSize: '15px' }}>Contract Manager permissions</h3>
        <p style={{ color: '#64748b', fontSize: '12px' }}>Enable or disable each capability. Changes apply to users with this role.</p>
        <select value={role} onChange={e => setRole(e.target.value)} style={{ padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', marginBottom: '12px' }}><option>CONTRACT_MANAGER</option><option>VIEWER</option></select>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '8px' }}>{permissions.map(permission => <label key={permission.code} style={{ display: 'flex', gap: '8px', alignItems: 'start', padding: '8px', background: '#f8fafc', borderRadius: '6px', fontSize: '12px' }}><input type="checkbox" checked={permission.enabled} onChange={e => setPermissions(permissions.map(p => p.code === permission.code ? { ...p, enabled: e.target.checked } : p))} /><span><strong>{permission.code}</strong><br /><span style={{ color: '#64748b' }}>{permission.description}</span></span></label>)}</div>
        <button onClick={savePermissions} disabled={saving} style={{ ...button, marginTop: '14px', background: '#4338ca', color: '#fff' }}>{saving ? 'Saving…' : 'Save permissions'}</button>
      </section>
      <section style={{ ...card, marginTop: '18px' }}>
        <h3 style={{ margin: 0, fontSize: '15px' }}>Individual permission overrides</h3>
        <p style={{ color: '#64748b', fontSize: '12px' }}>Use this for exceptions such as Manager 2. These settings override the person’s role defaults.</p>
        <select value={selectedUser} onChange={e => loadUserPermissions(e.target.value)} style={{ padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', marginBottom: '12px' }}><option value="">Select a person</option>{users.map(person => <option key={person.id} value={person.id}>{person.full_name} · {(person.roles || []).join(', ')}</option>)}</select>
        {selectedUser && <><div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '8px' }}>{userPermissions.map(permission => <label key={permission.code} style={{ display: 'flex', gap: '8px', alignItems: 'start', padding: '8px', background: '#f8fafc', borderRadius: '6px', fontSize: '12px' }}><input type="checkbox" checked={permission.enabled} onChange={e => setUserPermissions(userPermissions.map(p => p.code === permission.code ? { ...p, enabled: e.target.checked } : p))} /><span><strong>{permission.code}</strong><br /><span style={{ color: '#64748b' }}>{permission.description}</span></span></label>)}</div><button onClick={saveUserPermissions} disabled={saving} style={{ ...button, marginTop: '14px', background: '#0f766e', color: '#fff' }}>{saving ? 'Saving…' : 'Save individual overrides'}</button></>}
      </section>
    </div>
  );
}
