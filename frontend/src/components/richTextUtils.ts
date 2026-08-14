export function initialRichHtml(value: string): string {
  if (!value) return '';
  if (/<\/?(p|div|br|strong|b|em|i|u|ul|ol|table|img)\b/i.test(value)) return value;
  return value.split('\n').map(line => `<p>${line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') || '<br>'}</p>`).join('');
}

export function sanitizeRichHtml(value: string): string {
  const html = initialRichHtml(value);
  if (typeof DOMParser === 'undefined') return html;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('script,style,iframe,object,embed,form').forEach(node => node.remove());
  doc.querySelectorAll('*').forEach(node => {
    [...node.attributes].forEach(attribute => {
      if (attribute.name.toLowerCase().startsWith('on')) node.removeAttribute(attribute.name);
      if (attribute.name.toLowerCase() === 'href' && !attribute.value.startsWith('#')) node.removeAttribute(attribute.name);
      if (attribute.name.toLowerCase() === 'src' && !attribute.value.startsWith('data:image/')) node.removeAttribute(attribute.name);
    });
  });
  return doc.body.innerHTML;
}
