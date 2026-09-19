import { useAutopilot } from './hooks/useAutopilot'
import { useScriptedCall } from './hooks/useScriptedCall'
import { useFireForecast } from './hooks/useFireForecast'
import { useFireReplay } from './hooks/useFireReplay'
import { useLeadTime } from './hooks/useLeadTime'
import { useScenario } from './hooks/useScenario'
import { useLiveFires } from './hooks/useLiveFires'
import { useLiveOperations } from './hooks/useLiveOperations'
import { useMapMode, type MapMode } from './hooks/useMapMode'
import { useSelectedRoute } from './hooks/useSelectedRoute'
import { useOrders } from './hooks/useOrders'
import { useTextTriage } from './hooks/useTextTriage'
import { useFollowAgent } from './hooks/useFollowAgent'
import { useTriage } from './hooks/useTriage'
import { useCampaign } from './hooks/useCampaign'
import { useVoiceConversations } from './hooks/useConversation'
import { useRescueVideo } from './hooks/useRescueVideo'
import { useCrewPlan } from './hooks/useCrewPlan'
import { useClosures } from './hooks/useClosures'
import { useCrewRoomHost } from './hooks/useCrewRoom'
import { useVoiceCapabilities } from './hooks/useVoiceCapabilities'
import { Dashboard } from './ui/Dashboard'
import { useI18n } from './ui/i18n'

// Composition root: logic comes from hooks, presentation from ui/.
function App() {
  const triage = useTriage()
  const scenario = useScenario()
  const replay = useFireReplay()
  const [mode, setMode] = useMapMode()
  const live = useLiveFires(mode === 'live')
  const liveOperations = useLiveOperations(mode === 'live', live.spread)
  const { locale } = useI18n()
  const closures = useClosures()
  const selection = useSelectedRoute(locale, closures.key)
  const orders = useOrders()
  const textTriage = useTextTriage()
  const voice = useVoiceCapabilities()
  const campaign = useCampaign()
  const voiceCalls = useVoiceConversations()
  const rescueVideo = useRescueVideo()
  // The demo autopilot changes the triage state: show it now, not on the next poll.
  const autopilot = useAutopilot(triage.refresh)
  const crewPlan = useCrewPlan()
  const crewRoom = useCrewRoomHost()

  // Reset restores everything between rehearsals: the backend's state and replay moment, the
  // slider back to the start, no resident selected.
  const resetDemo = async () => {
    await triage.reset()
    await autopilot.refresh()
    selection.select(null)
    textTriage.clear()
    if (replay.range) replay.setTime(replay.range.start)
  }
  const forecast = useFireForecast(replay.time)
  const scriptedCall = useScriptedCall(autopilot.script, replay.time)
  const leadTime = useLeadTime(replay.time)

  const changeMode = (next: MapMode) => {
    if (next === 'live' && replay.playing) replay.togglePlay()
    setMode(next)
  }

  useFollowAgent(triage.focus, (neighborId) => {
    changeMode('replay')
    selection.showRescue(neighborId)
  })

  return (
    <Dashboard
      triage={{ ...triage, reset: resetDemo }}
      replay={replay}
      replayBounds={scenario.bounds}
      mode={mode}
      onModeChange={changeMode}
      live={live}
      liveOperations={liveOperations}
      selection={selection}
      orders={orders}
      textTriage={textTriage}
      voice={voice}
      campaign={campaign}
      conversation={voiceCalls.resident}
      coordinatorCall={voiceCalls.coordinator}
      rescueVideo={rescueVideo}
      autopilot={autopilot}
      scriptedCall={scriptedCall}
      crewPlan={crewPlan}
      crewRoom={crewRoom}
      closures={closures}
      forecast={forecast}
      leadTime={leadTime}
    />
  )
}

export default App
