import type { CameraState } from '../domain/video'
import { useI18n } from './i18n'
import './resident-camera.css'

interface ResidentCameraPageProps {
  state: CameraState
  videoRef: React.RefObject<HTMLDivElement | null>
}

// What a resident sees on their phone after tapping the SMS link (#18), in their phone's language.
export function ResidentCameraPage({ state, videoRef }: ResidentCameraPageProps) {
  const { t } = useI18n()
  return (
    <main className="resident-camera">
      <header>
        <strong>HackFire</strong> · {t('residentCamera.title')}
      </header>
      <div ref={videoRef} className="resident-camera-video" hidden={state === 'used' || state === 'error'} />
      <p className={state === 'live' ? 'resident-camera-text live' : 'resident-camera-text'}>
        {t(`residentCamera.${state}`)}
      </p>
    </main>
  )
}
