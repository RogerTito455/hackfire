import type { RoomState } from '../domain/video'
import { useI18n } from './i18n'
import './resident-camera.css'

interface CrewRoomPageProps {
  state: RoomState
  caption: string
  videoRef: React.RefObject<HTMLDivElement | null>
}

// What a fire crew sees on a phone: the command post's map and panels, live, with captions.
export function CrewRoomPage({ state, caption, videoRef }: CrewRoomPageProps) {
  const { t } = useI18n()
  return (
    <main className="resident-camera">
      <header>
        <strong>HackFire</strong> · {t('crewRoom.title')}
      </header>
      <div ref={videoRef} className="resident-camera-video" hidden={state === 'error'} />
      {caption && <p className="crew-room-caption">{caption}</p>}
      <p className={state === 'live' ? 'resident-camera-text live' : 'resident-camera-text'}>
        {t(`crewRoom.${state}`)}
      </p>
    </main>
  )
}
