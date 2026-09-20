import type { Rescue } from '../domain/triage'
import { safeHref } from '../domain/url'
import type { RescueVideoLink } from '../domain/video'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { formatMinutes } from './theme'

interface RescueQueueProps {
  rescues: Rescue[]
  /** Live video from a resident (#18); absent when Vonage is not set up. */
  video?: {
    links: Record<string, RescueVideoLink>
    requesting: string | null
    /** The resident being watched, or waited for. */
    watching: string | null
    failed: boolean
    onRequest: (neighborId: string) => void
  }
}

export function RescueQueue({ rescues, video }: RescueQueueProps) {
  const { t } = useI18n()
  if (rescues.length === 0) return <p className="empty">{t('rescues.empty')}</p>

  return (
    <ol className="rescues">
      {rescues.map((rescue) => {
        const link = video?.links[rescue.neighbor.id]
        // Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: only a safe-protocol link becomes an anchor.
        const linkHref = link ? safeHref(link.link) : null
        return (
          <li key={rescue.rescue_id}>
            <strong>{rescue.neighbor.name}</strong>
            <span>{rescue.neighbor.address}</span>
            <span>
              {rescue.neighbor.people === null
                ? t('rescues.peopleUnknown')
                : t('rescues.people', { count: rescue.neighbor.people })}
              , {rescue.neighbor.mobility ?? t('rescues.mobilityUnknown')}
            </span>
            {rescue.minutes_to_impact !== null && (
              <span className="impact">
                {rescue.minutes_to_impact > 0
                  ? t('rescues.impact', { time: formatMinutes(rescue.minutes_to_impact) })
                  : t('rescues.impactNow')}
              </span>
            )}
            {video && (
              <button
                type="button"
                className="video-request icon-button"
                disabled={video.requesting === rescue.neighbor.id}
                onClick={() => video.onRequest(rescue.neighbor.id)}
              >
                <Icon name="live" size={16} />
                {video.requesting === rescue.neighbor.id
                  ? t('video.creating')
                  : link
                    ? t('video.resend')
                    : t('video.request')}
              </button>
            )}
            {link && video?.watching === rescue.neighbor.id && (
              <span className="video-link">
                {link.sms_sent ? t('video.texted') : t('video.openOnPhone')}{' '}
                {linkHref ? (
                  <a href={linkHref} target="_blank" rel="noreferrer">
                    {link.link}
                  </a>
                ) : (
                  link.link
                )}
              </span>
            )}
          </li>
        )
      })}
      {video?.failed && <p className="empty">{t('video.failed')}</p>}
    </ol>
  )
}
