import { useCrewRoomMember } from './hooks/useCrewRoom'
import { CrewRoomPage } from './ui/CrewRoomPage'

// The page a crew's link opens (/crew/<room>): composition root only, hook → UI.
function CrewApp({ roomId }: { roomId: string }) {
  const room = useCrewRoomMember(roomId)
  return <CrewRoomPage state={room.state} caption={room.caption} videoRef={room.videoRef} />
}

export default CrewApp
