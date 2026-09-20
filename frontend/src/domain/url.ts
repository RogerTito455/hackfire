// Which links the dashboard renders. A link comes from the backend or the build's environment, but it
// ends up in an href, where a `javascript:` or `data:` URL would run inside the page.

const SAFE_PROTOCOLS = new Set(['https:', 'http:', 'mailto:'])

/** `value` when it is a relative URL or uses a safe protocol; `null` otherwise, so the caller shows no link. */
export function safeHref(value: string): string | null {
  try {
    // A relative URL takes the base's protocol, http:, which is safe.
    return SAFE_PROTOCOLS.has(new URL(value, 'http://localhost').protocol) ? value : null
  } catch {
    return null
  }
}
