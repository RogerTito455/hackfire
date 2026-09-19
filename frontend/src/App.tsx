import { useFireReplay } from './hooks/useFireReplay'
import { useLiveFires } from './hooks/useLiveFires'
import { useMapMode, type MapMode } from './hooks/useMapMode'
import { useTriage } from './hooks/useTriage'
import { Dashboard } from './ui/Dashboard'

// Composition root: logic comes from hooks, presentation from ui/.
function App() {
  const triage = useTriage()
  const replay = useFireReplay()
  const [mode, setMode] = useMapMode()
  const live = useLiveFires(mode === 'live')

  const changeMode = (next: MapMode) => {
    if (next === 'live' && replay.playing) replay.togglePlay()
    setMode(next)
  }

  return <Dashboard triage={triage} replay={replay} mode={mode} onModeChange={changeMode} live={live} />
}

export default App
