import { useEffect, useState } from 'react';
import { Settings2, X, AlertCircle, CheckCircle2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  headers: Record<string, string>;
}

interface LLMSettings {
  llm_api_url: string;
  llm_api_key: string;
  llm_model: string;
  llm_timeout_seconds: number;
}

export default function SettingsModal({ isOpen, onClose, headers }: Props) {
  const [settings, setSettings] = useState<LLMSettings>({
    llm_api_url: '',
    llm_api_key: '',
    llm_model: 'gpt-4o-mini',
    llm_timeout_seconds: 30
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const api = async (path: string, opts: RequestInit = {}) => {
    const res = await fetch(path, { ...opts, headers });
    const data = await res.json();
    if (!data.success) throw new Error(data.error?.message || 'Request failed');
    return data.data;
  };

  const loadSettings = async () => {
    try {
      const backendSettings = await api('/api/v1/config/llm-settings');
      const mergedSettings = {
        llm_api_url: backendSettings.llm_api_url || '',
        llm_api_key: backendSettings.llm_api_key || '',
        llm_model: backendSettings.llm_model || 'gpt-4o-mini',
        llm_timeout_seconds: backendSettings.llm_timeout_seconds || 30
      };
      setSettings(mergedSettings);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    if (isOpen) loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const saveSettings = async () => {
    setSaving(true); setError(''); setMsg('');
    try {
      await api('/api/v1/config/llm-settings', {
        method: 'PATCH',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      setMsg('LLM settings updated successfully');
      setTimeout(onClose, 1500);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', width: '90%', maxWidth: '600px', maxHeight: '90vh', overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings2 size={20} color='#7c3aed' /> <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>LLM Configuration</h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={18} color='#64748b' /></button>
        </div>

        {error && (<div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}><AlertCircle size={16} /> {error}</div>)}
        {msg && (<div style={{ background: '#dcfce7', color: '#166534', padding: '12px', borderRadius: '8px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={16} /> {msg}</div>)}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600, color: '#475569' }}>API URL</label>
            <input value={settings.llm_api_url} onChange={e => setSettings({ ...settings, llm_api_url: e.target.value })} placeholder='https://api.openai.com/v1' style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' }} />
            <div style={{ marginTop: '6px', fontSize: '12px', color: '#64748b' }}>Your OpenAI-compatible endpoint URL.</div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600, color: '#475569' }}>API Key</label>
            <input type='password' value={settings.llm_api_key} onChange={e => setSettings({ ...settings, llm_api_key: e.target.value })} placeholder='sk-...' style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' }} />
            <div style={{ marginTop: '6px', fontSize: '12px', color: '#64748b' }}>'Bearer' token, stored encrypted in the backend.</div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600, color: '#475569' }}>Model</label>
              <input value={settings.llm_model} onChange={e => setSettings({ ...settings, llm_model: e.target.value })} placeholder='gpt-4o-mini' style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' }} />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600, color: '#475569' }}>Timeout (seconds)</label>
              <input type='number' min={1} max={300} value={settings.llm_timeout_seconds} onChange={e => setSettings({ ...settings, llm_timeout_seconds: parseInt(e.target.value) || 30 })} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' }} />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', marginTop: '28px', justifyContent: 'flex-end' }}>
          <button onClick={onClose} disabled={saving} style={{ padding: '10px 16px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#fff', cursor: 'pointer', fontSize: '14px' }}>Cancel</button>
          <button onClick={saveSettings} disabled={saving} style={{ padding: '10px 16px', borderRadius: '6px', background: '#7c3aed', color: '#fff', border: 'none', cursor: 'pointer', fontSize: '14px', fontWeight: 600 }}>{saving ? 'Saving…' : 'Save Settings'}</button>
        </div>
      </div>
    </div>
  );
}
