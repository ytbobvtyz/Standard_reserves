export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function filenameFromContentDisposition(header?: string): string | null {
  if (!header) {
    return null
  }
  const utfMatch = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (utfMatch) {
    try {
      return decodeURIComponent(utfMatch[1])
    } catch {
      return utfMatch[1]
    }
  }
  const match = /filename="?([^";]+)"?/i.exec(header)
  return match?.[1] ?? null
}
