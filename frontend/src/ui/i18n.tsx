// The language in use, shared through context. The words and the lookup live in locales.ts.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { hasLocale, localeInfo, preferredLocale, translate, type Vars } from './locales'

const STORAGE_KEY = 'hackfire.locale'

function initialLocale(): string {
  let saved: string | null = null
  try {
    saved = window.localStorage.getItem(STORAGE_KEY)
  } catch {
    // Storage blocked (private mode): the browser's language decides.
  }
  return preferredLocale(saved, navigator.languages ?? [])
}

export interface I18n {
  locale: string
  /** BCP 47 tag for Intl date and number formats. */
  intl: string
  setLocale: (code: string) => void
  /** The text for `key`; `{name}` placeholders filled from `vars`; `vars.count` picks a plural form. */
  t: (key: string, vars?: Vars) => string
}

const I18nContext = createContext<I18n | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState(initialLocale)
  const { intl } = localeInfo(locale)

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const setLocale = useCallback((code: string) => {
    if (!hasLocale(code)) return
    setLocaleState(code)
    try {
      window.localStorage.setItem(STORAGE_KEY, code)
    } catch {
      // Not remembered this time; nothing else depends on it.
    }
  }, [])

  const t = useCallback((key: string, vars?: Vars) => translate(locale, key, vars), [locale])

  const value = useMemo(() => ({ locale, intl, setLocale, t }), [locale, intl, setLocale, t])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

// oxlint-disable-next-line react/only-export-components -- the hook belongs with its provider
export function useI18n(): I18n {
  const context = useContext(I18nContext)
  if (context === null) throw new Error('useI18n must be used inside <I18nProvider>')
  return context
}
