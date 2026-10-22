export function getBotSection(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean)
  if (segments[0] !== 'app' || segments[1] !== 'bots' || !segments[2]) {
    return 'overview'
  }
  return segments[3] ?? 'overview'
}
