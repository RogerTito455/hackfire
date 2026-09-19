import { useI18n } from './i18n'
import { LOCALES } from './locales'

// The interface language. The pill shows the short code; tapping it opens the phone's own picker
// with every language in src/locales/, so a new locale file shows up here with no code change.
export function LanguagePicker() {
  const { locale, setLocale, t } = useI18n()
  const current = LOCALES.find((entry) => entry.code === locale)
  return (
    <label className="language">
      <span aria-hidden="true">{locale.toUpperCase()}</span>
      <select
        value={locale}
        aria-label={t('app.language', { name: current?.name ?? locale })}
        onChange={(event) => setLocale(event.target.value)}
      >
        {LOCALES.map((entry) => (
          <option key={entry.code} value={entry.code} lang={entry.code}>
            {entry.name}
          </option>
        ))}
      </select>
    </label>
  )
}
