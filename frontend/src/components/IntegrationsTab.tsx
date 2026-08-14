import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, ExternalLink, RefreshCw, RotateCw, XCircle } from 'lucide-react';

interface Props { headers: Record<string, string>; }

const box: React.CSSProperties = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', marginBottom: '18px' };
const button: React.CSSProperties = { background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '6px', padding: '8px 12px', fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '7px', fontSize: '12px' };
const badge = (ok: boolean) => ({ background: ok ? '#dcfce7' : '#fef3c7', color: ok ? '#166534' : '#92400e', borderRadius: '12px', padding: '3px 9px', fontSize: '11px', fontWeight: 700 });

export default function IntegrationsTab({ headers }: Props) {
  const [connectors, setConnectors] = useState<any[]>([]);
  const [syncs, setSyncs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [lastSync, setLastSync] = useState<any>(null);

  const api = async (path: string, options: RequestInit = {}) => {
    const response = await fetch(path, { ...options, headers });
    const data = await response.json();
    if (!data.success) throw new Error(data.error?.message || 'Request failed');
    return data.data;
  };

  const load = async () => {
    setLoading(true); setError('');
    try {
      const [registry, history] = await Promise.all([api('/api/v1/integration/connectors'), api('/api/v1/integration/connectors/syncs?limit=25')]);
      setConnectors(registry.items || []); setSyncs(history.items || []);
    } catch (e: any) { setError(e.message || 'Could not load integrations'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const sync = async (id: string) => {
    setSyncing(id); setError(''); setMessage('');
    try {
      const data = await api(`/api/v1/integration/connectors/${id}/sync`, { method: 'POST' });
      setLastSync(data);
      setMessage(data.dry_run ? `${id} completed as a dry run. Configure an endpoint to transmit data.` : `${id} sync completed.`);
      await load();
    } catch (e: any) { setError(e.message || 'Sync failed'); }
    finally { setSyncing(null); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div><h2 style={{ fontSize: '18px', margin: 0 }}>External Integrations</h2><p style={{ fontSize: '13px', color: '#64748b', margin: '5px 0 0' }}>Connect ECLMS to ERP and accounting systems, inspect configuration, and run syncs.</p></div>
        <button onClick={load} style={{ ...button, background: '#fff', color: '#475569', border: '1px solid #cbd5e1' }}><RefreshCw size={14} /> Refresh</button>
      </div>
      {error && <div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}><AlertCircle size={16} />{error}</div>}
      {message && <div style={{ background: '#dcfce7', color: '#166534', padding: '12px', borderRadius: '8px', marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}><CheckCircle2 size={16} />{message}</div>}

      <div style={box}>
        <h3 style={{ fontSize: '15px', margin: '0 0 14px' }}>Connector registry</h3>
        {loading && connectors.length === 0 ? <div style={{ color: '#64748b', fontSize: '13px' }}>Loading connectors…</div> : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {connectors.map(connector => <div key={connector.id} style={{ border: '1px solid #e2e8f0', borderRadius: '9px', padding: '14px', background: '#f8fafc' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '9px' }}><strong style={{ color: '#0f172a' }}>{connector.display_name}</strong><span style={badge(connector.configured)}>{connector.configured ? 'CONFIGURED' : 'DRY RUN'}</span></div>
            <div style={{ fontSize: '12px', color: '#64748b', minHeight: '18px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{connector.endpoint || 'No endpoint configured'}</div>
            <button onClick={() => sync(connector.id)} disabled={syncing === connector.id} style={{ ...button, marginTop: '13px', opacity: syncing === connector.id ? 0.6 : 1 }}><RotateCw size={14} />{syncing === connector.id ? 'Syncing…' : 'Run sync'}</button>
          </div>)}
        </div>}
      </div>

      {lastSync?.preview && <div style={box}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}><div><h3 style={{ fontSize: '15px', margin: 0 }}>Last mapping preview</h3><p style={{ fontSize: '12px', color: '#64748b', margin: '4px 0 0' }}>The records included in the most recent dry-run.</p></div><span style={{ background: '#fef3c7', color: '#92400e', borderRadius: '12px', padding: '4px 9px', fontSize: '10px', fontWeight: 800 }}>SAFE PREVIEW</span></div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>{Object.entries(lastSync.preview).filter(([key]) => key !== 'organization_id' && key !== 'kind').map(([key, value]) => <div key={key} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px 12px', minWidth: '120px' }}><div style={{ color: '#64748b', fontSize: '11px' }}>{key.replace('_', ' ')}</div><strong style={{ color: '#334155', fontSize: '18px' }}>{Array.isArray(value) ? value.length : '—'}</strong><div style={{ color: '#94a3b8', fontSize: '10px' }}>mapped records</div></div>)}</div>
      </div>}

      <div style={box}>
        <h3 style={{ fontSize: '15px', margin: '0 0 14px' }}>Sync history</h3>
        {syncs.length === 0 ? <div style={{ color: '#94a3b8', fontSize: '13px', textAlign: 'center', padding: '18px' }}>No sync attempts yet. Run a connector above to create history.</div> : <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {syncs.map(syncItem => { const ok = syncItem.status === 'ok'; return <div key={syncItem.id} style={{ display: 'grid', gridTemplateColumns: '150px 1fr auto', gap: '12px', alignItems: 'center', borderBottom: '1px solid #f1f5f9', padding: '10px 0', fontSize: '12px' }}><strong style={{ color: '#334155' }}>{syncItem.connector_id}</strong><span style={{ color: '#64748b' }}>{syncItem.executed_at ? new Date(syncItem.executed_at).toLocaleString() : '—'}{syncItem.detail?.dry_run && ' · dry run'}{syncItem.detail?.status_code ? ` · HTTP ${syncItem.detail.status_code}` : ''}</span><span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: ok ? '#166534' : '#991b1b', fontWeight: 700 }}>{ok ? <CheckCircle2 size={14} /> : <XCircle size={14} />}{syncItem.status}</span></div>; })}
        </div>}
      </div>
      <div style={{ fontSize: '12px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}><ExternalLink size={13} /> Configure <code>ECLMS_ERP_ENDPOINT</code> or <code>ECLMS_ACCOUNTING_ENDPOINT</code> for live delivery. Dry runs are safe and still recorded.</div>
    </div>
  );
}
