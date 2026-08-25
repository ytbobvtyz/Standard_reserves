export function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleString('ru-RU')
}

export function formatShortName(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) {
    return fullName
  }
  if (parts.length === 1) {
    return parts[0]
  }
  return `${parts[0]} ${parts[1].charAt(0)}.`
}

export function formatInitiator(
  fullName: string,
  department?: string | null,
): string {
  const name = formatShortName(fullName)
  return department ? `${name} (${department})` : name
}
