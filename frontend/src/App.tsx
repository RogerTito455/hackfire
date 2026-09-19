import { useFireForecast } from './hooks/useFireForecast'
import { useFireReplay } from './hooks/useFireReplay'
import { useLeadTime } from './hooks/useLeadTime'
import { useTriage } from './hooks/useTriage'
import { Dashboard } from './ui/Dashboard'

// Composition root: logic comes from hooks, presentation from ui/.
function App() {
  const triage = useTriage()
  const replay = useFireReplay()
  const forecast = useFireForecast(replay.time)
  const leadTime = useLeadTime(replay.time)
  return <Dashboard triage={triage} replay={replay} forecast={forecast} leadTime={leadTime} />
}

export default App
