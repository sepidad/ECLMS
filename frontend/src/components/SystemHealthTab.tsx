import { useEffect, useState } from 'react';
import { Activity, RefreshCw, Server, Database, ShieldCheck, AlertTriangle } from 'lucide-react';

interface Props {
  headers: Record<string, string>;
}

interface ModHealth {
  status: string;
  [key: string]: any;
}

interface HealthData {
  status: string;
  app: string;
  version: string;
  database: string;
  database_pool: { checked_out: number; size: number; overflow: number } | null;
  modules: Record<string, ModHealth>;
}

const box = (): React.CSSProperties => ({ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '18px', marginBottom: '16px' });
const btnPrimary: React.CSSProperties = { background: '#7c3aed', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', fontWeight: 600, fontSize: '13px', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' };
const pill = (ok: boolean) => ({ padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700, background: ok ? '#dcfce7' : '#fee2e2', color: ok ? '#166534' : '#991b1b' });

export default function SystemHealthTab({ headers }: Props) {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [metrics, setMetrics] = useState<string>('');
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const res = await fetch('/health', { headers });
      const data = await res.json();
      setHealth(data);
      const m = await fetch('/metrics', { headers });
      setMetrics(await m.text());
    } catch (e: any) {
      setError(e.message || 'Failed to load health');
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', margin: 0 }}>System Health & Observability</h2>
          <p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0' }}>Live readiness, database pool gauges, module health, and raw Prometheus metrics.</p>
        </div>
        <button onClick={load} style={btnPrimary}><RefreshCw size={14} /> Refresh</button>
      </div>

      {error && <div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}><AlertTriangle size={16} /> {error}</div>}

      <div style={box()}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <Activity size={16} color="#7c3aed" />
          <h3 style={{ fontSize: '15px', margin: 0 }}>Readiness</h3>
          <span style={pill(health?.status === 'ok')}>{health ? health.database : '…'}</span>
        </div>
        {health && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>Application</div>
              <strong style={{ fontSize: '13px' }}>{health.app} v{health.version}</strong>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>Database</div>
              <strong style={{ fontSize: '13px' }}>{health.database}</strong>
            </div>
            {health.database_pool && (
              <div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>Connection Pool</div>
                <strong style={{ fontSize: '13px' }}>{health.database_pool.checked_out} / {health.database_pool.size} checked out (overflow {health.database_pool.overflow})</strong>
              </div>
            )}
          </div>
        )}
      </div>

      <div style={box()}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <Database size={16} color="#7c3aed" />
          <h3 style={{ fontSize: '15px', margin: 0 }}>Module Health</h3>
        </div>
        {health && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '8px' }}>
            {Object.entries(health.modules || {}).map(([name, mh]) => (
              <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '8px 10px', background: '#f8fafc' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>{name}</span>
                <span style={pill((mh.status || 'up') === 'up')}>{(mh.status || 'up').toUpperCase()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={box()}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <Server size={16} color="#7c3aed" />
          <h3 style={{ fontSize: '15px', margin: 0 }}>Raw Prometheus Metrics</h3>
        </div>
        {metrics && (
          <pre style={{ margin: 0, background: '#0f172a', color: '#a5f3fc', borderRadius: '8px', padding: '14px', fontSize: '11px', overflow: 'auto', maxHeight: '360px', fontFamily: 'monospace' }}>{metrics}</pre>
        )}
      </div>

      <div style={box()}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <ShieldCheck size={16} color="#7c3aed" />
          <h3 style={{ fontSize: '15px', margin: 0 }}>Security Posture</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '8px', fontSize: '12px', color: '#334155' }}>
          <div>· RBAC / ABAC role guards on all routes</div>
          <div>· Organization-scoped data isolation (ADR-003)</div>
          <div>· Webhook delivery HMAC-SHA256 signed</div>
          <div>· Security headers behind TLS proxy</div>
          <div>· Rate limiting + request body caps</div>
          <div>· Immutable, hash-verified document versions</div>
        </div>
      </div>
    </div>
  );
}