import React, { useEffect, useRef } from 'react';
import { AlignCenter, AlignLeft, AlignRight, Bold, ImagePlus, Italic, List, ListOrdered, Table2, Underline } from 'lucide-react';
import { sanitizeRichHtml } from './richTextUtils';

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: number;
}

const button: React.CSSProperties = { border: '1px solid #cbd5e1', background: '#fff', borderRadius: 4, padding: '4px 6px', cursor: 'pointer', fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 3 };

export default function RichTextEditor({ value, onChange, placeholder, minHeight = 96 }: Props) {
  const editor = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editor.current && editor.current.innerHTML !== sanitizeRichHtml(value)) editor.current.innerHTML = sanitizeRichHtml(value);
  }, [value]);

  const command = (name: string, commandValue?: string) => {
    editor.current?.focus();
    document.execCommand(name, false, commandValue);
    onChange(editor.current?.innerHTML || '');
  };

  const setDirection = (direction: 'ltr' | 'rtl') => {
    editor.current?.focus();
    const selection = window.getSelection();
    const node = selection?.anchorNode;
    const element = node instanceof Element ? node : node?.parentElement;
    const block = element?.closest('p,div,li,h1,h2,h3') as HTMLElement | null;
    if (block && editor.current?.contains(block)) block.dir = direction;
    else if (editor.current) editor.current.dir = direction;
    onChange(editor.current?.innerHTML || '');
  };

  const insertTable = () => {
    const rows = Math.max(1, Math.min(12, Number(window.prompt('Number of rows', '3')) || 3));
    const columns = Math.max(1, Math.min(8, Number(window.prompt('Number of columns', '3')) || 3));
    const cells = Array.from({ length: columns }, () => '<td style="border:1px solid #94a3b8;padding:6px;min-width:70px">Cell</td>').join('');
    const table = `<table style="border-collapse:collapse;width:100%;margin:8px 0"><tbody>${Array.from({ length: rows }, () => `<tr>${cells}</tr>`).join('')}</tbody></table><p><br></p>`;
    command('insertHTML', table);
  };

  const addImage = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = () => command('insertImage', String(reader.result));
    reader.readAsDataURL(file);
    event.target.value = '';
  };

  return <div style={{ border: '1px solid #cbd5e1', borderRadius: 6, overflow: 'hidden', background: '#fff' }}>
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', padding: 5, background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
      <button type="button" title="Bold" onMouseDown={e => e.preventDefault()} onClick={() => command('bold')} style={button}><Bold size={13} /></button>
      <button type="button" title="Italic" onMouseDown={e => e.preventDefault()} onClick={() => command('italic')} style={button}><Italic size={13} /></button>
      <button type="button" title="Underline" onMouseDown={e => e.preventDefault()} onClick={() => command('underline')} style={button}><Underline size={13} /></button>
      <label title="Text color" style={{ ...button, padding: '2px 5px' }}>A <input type="color" defaultValue="#1f2937" onChange={e => command('foreColor', e.target.value)} style={{ width: 18, height: 18, border: 0, padding: 0 }} /></label>
      <span style={{ borderLeft: '1px solid #cbd5e1', margin: '0 2px' }} />
      <button type="button" title="Align left" onMouseDown={e => e.preventDefault()} onClick={() => command('justifyLeft')} style={button}><AlignLeft size={13} /></button>
      <button type="button" title="Align center" onMouseDown={e => e.preventDefault()} onClick={() => command('justifyCenter')} style={button}><AlignCenter size={13} /></button>
      <button type="button" title="Align right" onMouseDown={e => e.preventDefault()} onClick={() => command('justifyRight')} style={button}><AlignRight size={13} /></button>
      <button type="button" title="Left-to-right" onClick={() => setDirection('ltr')} style={button}>LTR</button>
      <button type="button" title="Right-to-left" onClick={() => setDirection('rtl')} style={button}>RTL</button>
      <span style={{ borderLeft: '1px solid #cbd5e1', margin: '0 2px' }} />
      <button type="button" title="Bulleted list" onClick={() => command('insertUnorderedList')} style={button}><List size={13} /></button>
      <button type="button" title="Numbered list" onClick={() => command('insertOrderedList')} style={button}><ListOrdered size={13} /></button>
      <button type="button" title="Insert table" onClick={insertTable} style={button}><Table2 size={13} /></button>
      <button type="button" title="Add image" onClick={() => fileInput.current?.click()} style={button}><ImagePlus size={13} /></button>
      <input ref={fileInput} type="file" accept="image/*" onChange={addImage} style={{ display: 'none' }} />
    </div>
    <div ref={editor} contentEditable suppressContentEditableWarning role="textbox" aria-label={placeholder || 'Rich contract text'} onInput={() => onChange(editor.current?.innerHTML || '')} data-placeholder={placeholder || 'Write contract text…'} style={{ minHeight, padding: 10, outline: 'none', fontSize: 13, lineHeight: 1.55, direction: 'ltr' }} />
  </div>;
}
