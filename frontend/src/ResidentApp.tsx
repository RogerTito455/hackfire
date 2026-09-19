import { useResidentCamera } from './hooks/useResidentCamera'
import { ResidentCameraPage } from './ui/ResidentCameraPage'

// The page a resident's video link opens (/v/<link>): composition root only, hook → UI.
function ResidentApp({ linkId }: { linkId: string }) {
  const camera = useResidentCamera(linkId)
  return <ResidentCameraPage state={camera.state} videoRef={camera.videoRef} />
}

export default ResidentApp
