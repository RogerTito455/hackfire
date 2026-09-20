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

// The request button's text: creating the link, sending it again, or asking for it the first time.
function requestLabel(t: (key: string) => string, requesting: boolean, hasLink: boolean): string {
  if (requesting) return t('video.creating')
  return hasLink ? t('video.resend') : t('video.request')
}

export function RescueQueue({ rescues, video }: RescueQueueProps) {
  const { t } = useI18n()
  if (rescues.length === 0) return <p className="empty">{t('rescues.empty')}</p>

  return (
    <ol className="rescues">
      {rescues.map((rescue) => {
        const link = video?.links[rescue.neighbor.id]
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
                {requestLabel(t, video.requesting === rescue.neighbor.id, link !== undefined)}
              </button>
            )}
            {link && video?.watching === rescue.neighbor.id && (
              <span className="video-link">
                {link.sms_sent ? t('video.texted') : t('video.openOnPhone')}{' '}
                {/* Recommended by Norma — fixed with Claude Sonnet 5 via Claude Code: a link that is not http, https or mailto becomes '#'. */}
                <a href={safeHref(link.link) ?? '#'} target="_blank" rel="noreferrer">
                  {link.link}
                </a>
              </span>
            )}
          </li>
        )
      })}
      {video?.failed && <p className="empty">{t('video.failed')}</p>}
    </ol>
  )
}
