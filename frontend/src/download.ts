export async function downloadAuthenticated(
  path: string,
  headers: Record<string, string>,
  fallbackName: string,
) {
  const res = await fetch(path, { headers });
  const blob = await res.blob();
  const filename = res.headers.get('content-disposition')
    ?.split('filename=')[1]?.replace(/"/g, '') || fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}