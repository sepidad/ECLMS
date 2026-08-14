import { useMemo, useState } from 'react';
import { AlertCircle, CheckCircle2, Clipboard, FileUp, Upload } from 'lucide-react';

interface Props {
  headers: Record<string, string>;
  contracts?: { id: string; title: string; reference_number: string }[];
}

type ImportKind = 'contracts' | 'obligations' | 'commitments';

const config: Record<ImportKind, { label: string; endpoint: string; columns: string[]; description: string }> = {
  contracts: {
    label: 'Contracts', endpoint: '/api/v1/import/contracts',
    columns: ['title', 'reference_number', 'counterparty', 'content'],
    description: 'Create contract records and immutable initial versions.',
  },
  obligations: {
    label: 'Obligations', endpoint: '/api/v1/import/obligations',
    columns: ['contract_reference', 'description', 'due_date'],
    description: 'Create obligations linked to existing contracts. Use a contract ID in the first column.',
  },
  commitments: {
    label: 'Financial commitments', endpoint: '/api/v1/import/commitments',
    columns: ['contract_reference', 'description', 'amount', 'currency'],
    description: 'Create financial commitments linked to existing contracts.',
  },
};

const box: React.CSSProperties = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '20px', marginBottom: '18px' };
const button: React.CSSProperties = { background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '6px', padding: '9px 14px', fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '7px' };
const input: React.CSSProperties = { width: '100%', boxSizing: 'border-box', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '9px 10px', fontSize: '13px' };

export default function DataImportTab({ headers, contracts = [] }: Props) {
  const [kind, setKind] = useState<ImportKind>('contracts');
  const [csv, setCsv] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const selected = config[kind];
  const template = useMemo(() => `${selected.columns.join(',')}\n${selected.columns.map(column => column === 'contract_reference' ? (contracts[0]?.id || 'contract-id') : column === 'amount' ? '1000' : column === 'currency' ? 'USD' : column === 'due_date' ? '2026-12-31' : `Example ${column}`).join(',')}`, [selected, contracts]);

  const useTemplate = () => setCsv(template);

  const readFile = (file?: File) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setCsv(String(reader.result || ''));
    reader.readAsText(file);
  };

  const importCsv = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(''); setResult(null);
    if (!csv.trim()) return setError('Paste CSV data or choose a file first.');
    setLoading(true);
    try {
      const response = await fetch(selected.endpoint, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'text/csv' },
        body: csv,
      });
      const data = await response.json();
      if (!data.success) throw new Error(data.error?.message || 'Import failed');
      setResult(data.data);
    } catch (e: any) {
      setError(e.message || 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '18px', margin: 0 }}>Data Import</h2>
        <p style={{ fontSize: '13px', color: '#64748b', margin: '5px 0 0' }}>Bulk-load operational data with a row-by-row result report.</p>
      </div>

      {error && <div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}><AlertCircle size={16} />{error}</div>}

      <div style={box}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 280px) 1fr', gap: '18px', alignItems: 'end' }}>
          <label style={{ fontSize: '12px', fontWeight: 700, color: '#475569' }}>
            Import type
            <select value={kind} onChange={e => { setKind(e.target.value as ImportKind); setResult(null); setError(''); }} style={{ ...input, marginTop: '6px', background: '#fff' }}>
              {Object.entries(config).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}
            </select>
          </label>
          <div style={{ fontSize: '13px', color: '#64748b' }}>{selected.description}<div style={{ marginTop: '5px', fontFamily: 'monospace', fontSize: '11px', color: '#475569' }}>{selected.columns.join('  |  ')}</div></div>
        </div>
      </div>

      <form onSubmit={importCsv} style={box}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3 style={{ fontSize: '15px', margin: 0 }}>CSV payload</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button type="button" onClick={useTemplate} style={{ ...button, background: '#f1f5f9', color: '#475569' }}><Clipboard size={14} /> Use template</button>
            <label style={{ ...button, background: '#ede9fe', color: '#6d28d9' }}><FileUp size={14} /> Choose CSV<input type="file" accept=".csv,text/csv" onChange={e => readFile(e.target.files?.[0])} style={{ display: 'none' }} /></label>
          </div>
        </div>
        <textarea value={csv} onChange={e => setCsv(e.target.value)} rows={10} placeholder={template} style={{ ...input, fontFamily: 'monospace', resize: 'vertical' }} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}><button type="submit" disabled={loading} style={{ ...button, opacity: loading ? 0.65 : 1 }}><Upload size={15} />{loading ? 'Importing…' : `Import ${selected.label}`}</button></div>
      </form>

      {result && <div style={box}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}><CheckCircle2 size={18} color="#16a34a" /><h3 style={{ fontSize: '15px', margin: 0 }}>Import report</h3></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(120px, 1fr))', gap: '10px', marginBottom: '16px' }}>
          {([['Rows', result.total, '#334155'], ['Created', result.created, '#166534'], ['Failed', result.failed, result.failed ? '#991b1b' : '#166534']] as const).map(([label, value, color]) => <div key={label} style={{ background: '#f8fafc', borderRadius: '8px', padding: '12px' }}><div style={{ fontSize: '11px', color: '#64748b' }}>{label}</div><strong style={{ fontSize: '20px', color }}>{value}</strong></div>)}
        </div>
        {result.failed_items?.length > 0 && <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>{result.failed_items.map((item: any) => <div key={item.row} style={{ border: '1px solid #fecaca', background: '#fff7f7', borderRadius: '7px', padding: '9px 11px', fontSize: '12px' }}><strong>Row {item.row}:</strong> {item.reason}</div>)}</div>}
      </div>}
    </div>
  );
}
