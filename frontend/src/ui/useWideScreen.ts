import { useEffect, useState } from 'react'

// Which layout the coordinator gets. Presentation, so it lives with the components: a phone gets the
// bottom sheet, a laptop the console (rail plus open section). The width matches dashboard.css.
const CONSOLE = '(min-width: 900px)'

export function useWideScreen(): boolean {
  const [wide, setWide] = useState(() => window.matchMedia(CONSOLE).matches)

  useEffect(() => {
    const query = window.matchMedia(CONSOLE)
    const update = () => setWide(query.matches)
    update()
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])

  return wide
}
