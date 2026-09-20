import { useCallback, useEffect, useState } from 'react'

// How much of a laptop screen the console takes, and whether it is out of the way entirely.
// Presentation, so it lives with the components like useWideScreen: nothing here is fetched.
// The choice is remembered per browser, because a coordinator who wants more map wants it after a
// reload too. localStorage throws in a private window with site data blocked, so every read and
// write is guarded.

const WIDTH_KEY = 'hackfire.console.width'
const HIDDEN_KEY = 'hackfire.console.hidden'

/** Narrower than this the rail and the open section stop being two readable columns. */
export const MIN_CONSOLE = 400

/** Under this the strip goes two by two, the rail narrows and the brand name folds away. */
const NARROW_CONSOLE = 520

/** The defaults in dashboard.css, so the divider starts from the width the screen already shows. */
function defaultWidth(viewport: number): number {
  if (viewport >= 1500) return 736
  if (viewport >= 1200) return 632
  return 520
}

/** Half the viewport: past it the map would be the smaller half, which is not what it is for. */
function maxWidth(viewport: number): number {
  return Math.max(MIN_CONSOLE, Math.round(viewport / 2))
}

function readStored(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // A browser that refuses to remember it still resizes: the choice just lasts this session.
  }
}

function readWidth(): number | null {
  const stored = readStored(WIDTH_KEY)
  if (stored === null) return null
  const width = Number.parseInt(stored, 10)
  return Number.isFinite(width) ? width : null
}

export interface ConsoleLayout {
  /** The console's width in pixels right now, whether it was chosen or comes from the stylesheet. */
  width: number
  /** The bounds the divider may move between on this viewport. */
  min: number
  max: number
  /** Someone dragged the divider: the width is theirs, not the stylesheet's. */
  chosen: boolean
  /** Map only: the console is out of the way and the top bar spans the screen. */
  hidden: boolean
  /** The viewport's width, so the caller can work out what the map is left with. */
  viewport: number
  setWidth: (width: number) => void
  toggleHidden: () => void
}

export function useConsoleLayout(): ConsoleLayout {
  const [chosenWidth, setChosenWidth] = useState<number | null>(readWidth)
  const [hidden, setHidden] = useState(() => readStored(HIDDEN_KEY) === 'true')
  const [viewport, setViewport] = useState(() => window.innerWidth)

  useEffect(() => {
    const measure = () => setViewport(window.innerWidth)
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])

  const min = MIN_CONSOLE
  const max = maxWidth(viewport)
  // An untouched browser keeps exactly the stylesheet's layout; a chosen width is clamped to the
  // screen it is shown on, so a width picked on a big monitor cannot swallow a small one.
  const width = chosenWidth === null ? defaultWidth(viewport) : Math.min(max, Math.max(min, chosenWidth))

  const setWidth = useCallback(
    (next: number) => {
      const clamped = Math.min(maxWidth(window.innerWidth), Math.max(MIN_CONSOLE, Math.round(next)))
      setChosenWidth(clamped)
      write(WIDTH_KEY, String(clamped))
    },
    [],
  )

  const toggleHidden = useCallback(() => {
    setHidden((current) => {
      write(HIDDEN_KEY, String(!current))
      return !current
    })
  }, [])

  return { width, min, max, chosen: chosenWidth !== null, hidden, viewport, setWidth, toggleHidden }
}

/** What the app element says about the console, so the stylesheet can answer without a second prop. */
export function consoleState(layout: ConsoleLayout, wide: boolean): 'hidden' | 'narrow' | undefined {
  if (!wide) return undefined
  if (layout.hidden) return 'hidden'
  return layout.width < NARROW_CONSOLE ? 'narrow' : undefined
}
