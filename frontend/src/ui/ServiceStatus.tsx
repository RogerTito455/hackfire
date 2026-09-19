import type { ProviderStatus } from '../domain/operations'
import { useI18n } from './i18n'
import { PROVIDER_STATE_COLOR, formatClock } from './theme'

interface ServiceStatusProps {
  providers: ProviderStatus[]
  loaded: boolean
  failed: boolean
}

// One row per external service: a dot in the status colours, its state in words and the reason.
export function ServiceStatus({ providers, loaded, failed }: ServiceStatusProps) {
  const { t, intl } = useI18n()
  if (providers.length === 0) {
    return <p className="empty">{failed || loaded ? t('providers.unavailable') : t('providers.loading')}</p>
  }
  return (
    <ul className="services">
      {providers.map((provider) => (
        <li key={provider.id} data-state={provider.state}>
          <span
            className="service-dot"
            aria-hidden="true"
            style={{ borderColor: PROVIDER_STATE_COLOR[provider.state], backgroundColor: provider.state === 'configured' ? 'transparent' : PROVIDER_STATE_COLOR[provider.state] }}
          />
          <span className="service-text">
            <span className="service-head">
              <strong translate="no">{provider.name}</strong>
              <span className="service-state">{t(`providers.state.${provider.state}`)}</span>
            </span>
            <span className="service-reason">{provider.reason}</span>
            {provider.checked_at && (
              <time className="service-checked" dateTime={provider.checked_at}>
                {t('providers.checkedAt', { time: formatClock(provider.checked_at, intl) })}
              </time>
            )}
          </span>
        </li>
      ))}
    </ul>
  )
}
