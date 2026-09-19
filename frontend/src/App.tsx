import { useFireForecast } from './hooks/useFireForecast'
import { useFireReplay } from './hooks/useFireReplay'
import { useLeadTime } from './hooks/useLeadTime'
import { useLiveFires } from './hooks/useLiveFires'
import { useMapMode, type MapMode } from './hooks/useMapMode'
import { useSelectedRoute } from './hooks/useSelectedRoute'
import { useTriage } from './hooks/useTriage'
import { Dashboard } from './ui/Dashboard'

// Composition root: logic comes from hooks, presentation from ui/.
function App() {
  const triage = useTriage()
  const replay = useFireReplay()
  const [mode, setMode] = useMapMode()
  const live = useLiveFires(mode === 'live')
  const selection = useSelectedRoute()
  const forecast = useFireForecast(replay.time)
  const leadTime = useLeadTime(replay.time)

  const changeMode = (next: MapMode) => {
    if (next === 'live' && replay.playing) replay.togglePlay()
    setMode(next)
  }

  return (
    <Dashboard
      triage={triage}
      replay={replay}
      mode={mode}
      onModeChange={changeMode}
      live={live}
      selection={selection}
      forecast={forecast}
      leadTime={leadTime}
    />
  )
}

export default App
