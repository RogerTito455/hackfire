import type { Rescue } from '../domain/triage'
import { useI18n } from './i18n'
import { formatMinutes } from './theme'

interface RescueQueueProps {
  rescues: Rescue[]
}

export function RescueQueue({ rescues }: RescueQueueProps) {
  const { t } = useI18n()
  if (rescues.length === 0) return <p className="empty">{t('rescues.empty')}</p>

  return (
    <ol className="rescues">
      {rescues.map((rescue) => (
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
        </li>
      ))}
    </ol>
  )
}
