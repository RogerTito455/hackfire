// The interface's words. Every text the dashboard shows lives in src/locales/<code>.json; adding a
// language is adding one file there (its "_meta" block names it). No library: a lookup, {name}
// placeholders and Intl plural rules. English is the reference and the fallback for missing keys;
// `pnpm check` (scripts/check-locales.mjs) fails when a locale misses a key or the code uses one
// that does not exist.

export type Messages = { [key: string]: string | Messages }
export type Vars = Record<string, string | number>

const FILES = import.meta.glob<Messages>('../locales/*.json', { eager: true, import: 'default' })

const CATALOGUE: Record<string, Messages> = Object.fromEntries(
  Object.entries(FILES).map(([path, messages]) => [path.slice('../locales/'.length, -'.json'.length), messages]),
)

export const REFERENCE_LOCALE = 'en'

export interface LocaleInfo {
  code: string
  name: string
  /** BCP 47 tag for dates and numbers, e.g. "es-ES". */
  intl: string
}

export const LOCALES: LocaleInfo[] = Object.entries(CATALOGUE)
  .map(([code, messages]) => {
    const meta = messages._meta as Messages | undefined
    return { code, name: String(meta?.name ?? code), intl: String(meta?.intl ?? code) }
  })
  .sort((a, b) => a.code.localeCompare(b.code))

export function hasLocale(code: string): boolean {
  return code in CATALOGUE
}

export function localeInfo(code: string): LocaleInfo {
  return LOCALES.find((entry) => entry.code === code) ?? LOCALES.find((entry) => entry.code === REFERENCE_LOCALE)!
}

function lookup(messages: Messages | undefined, key: string): string | Messages | undefined {
  let node: string | Messages | undefined = messages
  for (const part of key.split('.')) {
    if (node === undefined || typeof node === 'string') return undefined
    node = node[part]
  }
  return node
}

/**
 * The text for `key` in `locale`. `{name}` placeholders are filled from `vars`, numbers written the
 * locale's way (1,234 or 1.234); a numeric `vars.count` picks the plural form.
 */
export function translate(locale: string, key: string, vars?: Vars): string {
  const { intl } = localeInfo(locale)
  let value = lookup(CATALOGUE[locale], key) ?? lookup(CATALOGUE[REFERENCE_LOCALE], key)
  if (value !== undefined && typeof value !== 'string' && typeof vars?.count === 'number') {
    value = value[new Intl.PluralRules(intl).select(vars.count)] ?? value.other
  }
  if (typeof value !== 'string') return key
  return value.replace(/\{(\w+)\}/g, (match, name: string) => {
    const filler = vars?.[name]
    if (filler === undefined) return match
    return typeof filler === 'number' ? new Intl.NumberFormat(intl).format(filler) : filler
  })
}

/** The saved choice, else the first of the browser's languages we have, else English. */
export function preferredLocale(saved: string | null, browser: readonly string[]): string {
  if (saved && hasLocale(saved)) return saved
  const codes = browser.map((tag) => tag.slice(0, 2).toLowerCase())
  return codes.find(hasLocale) ?? REFERENCE_LOCALE
}
