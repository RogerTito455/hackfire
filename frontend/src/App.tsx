import { useFireReplay } from './hooks/useFireReplay'
import { useTriage } from './hooks/useTriage'
import { Dashboard } from './ui/Dashboard'

// Composition root: logic comes from hooks, presentation from ui/.
function App() {
  const triage = useTriage()
  const replay = useFireReplay()
  return <Dashboard triage={triage} replay={replay} />
}

export default App
