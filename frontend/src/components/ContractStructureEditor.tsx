import React from 'react';
import RichTextEditor from './RichTextEditor';

export interface ContractNode {
  id: string;
  title: string;
  body: string;
  children: ContractNode[];
  notes: string[];
  number?: string;
}

interface Props { value: ContractNode[]; onChange: (value: ContractNode[]) => void; }

const id = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const blank = (): ContractNode => ({ id: id(), title: 'New article title', body: '', children: [], notes: [] });

function update(nodes: ContractNode[], nodeId: string, fn: (node: ContractNode) => ContractNode): ContractNode[] {
  return nodes.map(node => node.id === nodeId ? fn(node) : { ...node, children: update(node.children, nodeId, fn) });
}

function remove(nodes: ContractNode[], nodeId: string): ContractNode[] {
  return nodes.filter(node => node.id !== nodeId).map(node => ({ ...node, children: remove(node.children, nodeId) }));
}

function insertSibling(nodes: ContractNode[], nodeId: string, before: boolean): ContractNode[] {
  const result: ContractNode[] = [];
  for (const node of nodes) {
    if (node.id === nodeId && before) result.push(blank());
    result.push({ ...node, children: insertSibling(node.children, nodeId, before) });
    if (node.id === nodeId && !before) result.push(blank());
  }
  return result;
}

const input: React.CSSProperties = { width: '100%', boxSizing: 'border-box', border: '1px solid #cbd5e1', borderRadius: 5, padding: '6px 8px', fontFamily: 'inherit', fontSize: 12 };
const action: React.CSSProperties = { border: '1px solid #cbd5e1', background: '#fff', borderRadius: 5, padding: '4px 7px', cursor: 'pointer', fontSize: 11 };

function count(nodes: ContractNode[]): { articles: number; notes: number } {
  return nodes.reduce((sum, node) => { const child = count(node.children); return { articles: sum.articles + 1 + child.articles, notes: sum.notes + node.notes.length + child.notes }; }, { articles: 0, notes: 0 });
}

export default function ContractStructureEditor({ value, onChange }: Props) {
  const totals = count(value);
  const render = (nodes: ContractNode[], depth = 0): React.ReactNode => nodes.map((node, index) => (
    <div key={node.id} style={{ marginLeft: depth * 18, borderLeft: depth ? '2px solid #e2e8f0' : 'none', paddingLeft: depth ? 10 : 0, marginTop: 10 }}>
      <div style={{ display: 'flex', gap: 7, alignItems: 'center', marginBottom: 5 }}>
        <strong style={{ color: '#6d28d9', minWidth: 42 }}>{node.number || (depth === 0 ? `${index + 1}` : '')}</strong>
        <input aria-label={`Article ${node.number || index + 1} title`} value={node.title} onChange={e => onChange(update(value, node.id, n => ({ ...n, title: e.target.value })))} style={{ ...input, fontWeight: 600 }} />
      </div>
      <RichTextEditor value={node.body} onChange={next => onChange(update(value, node.id, n => ({ ...n, body: next })))} placeholder="Write the article or sub-article text…" />
      <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 5 }}>
        <button type="button" onClick={() => onChange(insertSibling(value, node.id, true))} style={action}>+ Article before</button>
        <button type="button" onClick={() => onChange(insertSibling(value, node.id, false))} style={action}>+ Article after</button>
        <button type="button" onClick={() => onChange(update(value, node.id, n => ({ ...n, children: [...n.children, blank()] })))} style={action}>+ Sub-article</button>
        <button type="button" onClick={() => onChange(update(value, node.id, n => ({ ...n, notes: [...n.notes, 'New note'] })))} style={action}>+ Note</button>
        <button type="button" onClick={() => onChange(remove(value, node.id))} style={{ ...action, color: '#b91c1c' }}>Delete</button>
      </div>
      {node.notes.map((note, noteIndex) => <div key={`${node.id}-note-${noteIndex}`} style={{ display: 'flex', gap: 6, marginTop: 6, marginLeft: 18 }}><strong style={{ color: '#92400e', whiteSpace: 'nowrap' }}>Note {noteIndex + 1}</strong><input aria-label={`Note ${noteIndex + 1}`} value={note} onChange={e => onChange(update(value, node.id, n => ({ ...n, notes: n.notes.map((x, i) => i === noteIndex ? e.target.value : x) })))} style={input} /><button type="button" onClick={() => onChange(update(value, node.id, n => ({ ...n, notes: n.notes.filter((_, i) => i !== noteIndex) })))} style={{ ...action, color: '#b91c1c' }}>×</button></div>)}
      {render(node.children, depth + 1)}
    </div>
  ));

  return <section style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 8, padding: 12 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, marginBottom: 8 }}>
      <div><strong>Articles and Notes</strong><div style={{ fontSize: 11, color: '#64748b', marginTop: 3 }}>Numbers are automatic. Inserting or deleting an item renumbers all following items.</div></div>
      <div style={{ fontSize: 11, color: '#475569', whiteSpace: 'nowrap' }}>Articles: <strong>{totals.articles}</strong> · Notes: <strong>{totals.notes}</strong></div>
    </div>
    <button type="button" onClick={() => onChange([...value, blank()])} style={{ ...action, background: '#7c3aed', color: '#fff', borderColor: '#7c3aed', marginBottom: 4 }}>+ New article</button>
    {value.length ? render(value) : <div style={{ padding: 18, textAlign: 'center', color: '#64748b', fontSize: 12 }}>Add the first article to begin.</div>}
  </section>;
}
