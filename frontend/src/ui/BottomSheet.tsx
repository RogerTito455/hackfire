import { useEffect, useRef, useState, type CSSProperties, type PointerEvent, type ReactNode } from 'react'
import { useI18n } from './i18n'

// The phone layout's bottom sheet, like a native maps app: the map stays full screen and the
// panels live in a sheet the thumb drags between three heights. On wide screens CSS turns it into a
// side panel and the handle disappears. Pure presentation: the only state is how open it is.

export type SheetSnap = 'peek' | 'half' | 'full'

const ORDER: readonly SheetSnap[] = ['peek', 'half', 'full']

/** Before the header is measured, and the least a peek can be. */
const PEEK_FALLBACK = 196

/** The panel half opens on to; the CSS rule for [data-snap='half'] says the same. */
const HALF_BODY = 240

/**
 * What the sheet leaves above itself, even wide open: the top bar — where the brand is the way back
 * — and the map's key under it, whole rather than cut in half. `--sheet-top-gap` in the CSS says the
 * same, with the safe area added.
 */
const TOP_GAP = 110

/** Visible height of each snap, in pixels: peek shows the whole header, whatever the language. */
function heights(peek: number, viewport: number): Record<SheetSnap, number> {
  const full = Math.max(peek, viewport - TOP_GAP)
  // A header with a scrubber, four counters and a live note can be 290 px on a phone: half has to
  // clear it, or opening the sheet shows a strip of panel and looks like it did not open at all.
  const half = Math.min(full, Math.max(peek + HALF_BODY, Math.round(viewport * 0.52)))
  return { peek, half, full }
}

function nearest(px: number, peek: number, viewport: number): SheetSnap {
  const h = heights(peek, viewport)
  return ORDER.reduce((best, snap) => (Math.abs(h[snap] - px) < Math.abs(h[best] - px) ? snap : best), 'peek')
}

interface BottomSheetProps {
  /** Always visible: the replay scrubber and the status strip. */
  header: ReactNode
  children: ReactNode
  /** When this changes to a non-null value (a resident was selected), open at least halfway. */
  wake: string | null
}

export function BottomSheet({ header, children, wake }: BottomSheetProps) {
  const { t } = useI18n()
  const [snap, setSnap] = useState<SheetSnap>('peek')
  const [dragPx, setDragPx] = useState<number | null>(null)
  const drag = useRef<{ startY: number; startPx: number; moved: boolean } | null>(null)
  const dragged = useRef(false) // a drag ends in a click too, and that click must not toggle the sheet
  const grab = useRef<HTMLButtonElement | null>(null)
  const headerBox = useRef<HTMLDivElement | null>(null)
  const [peek, setPeek] = useState(PEEK_FALLBACK)
  // Measured, not `vh`: on a phone `100vh` is the window with the browser's URL bar hidden, so the
  // CSS and this file would disagree by the height of that bar and the sheet would climb too high.
  const [viewport, setViewport] = useState(() => window.innerHeight)

  // The header's height changes with the language, the mode and the screen width.
  // Norma rct-prf-setstate-in-useeffect: setPeek runs inside the ResizeObserver callback, not in
  // the effect body — a height is only known after layout. The one state change that does belong
  // in render is already done during render, just below.
  useEffect(() => {
    if (!headerBox.current || !grab.current) return
    const measure = () => setPeek(Math.ceil((grab.current?.offsetHeight ?? 0) + (headerBox.current?.offsetHeight ?? 0)))
    const observer = new ResizeObserver(measure)
    observer.observe(headerBox.current)
    return () => observer.disconnect()
  }, [])

  // The window height changes when the browser's URL bar slides away, and on rotation.
  // Norma rct-prf-setstate-in-useeffect: setViewport runs in the listener, not in the effect body.
  useEffect(() => {
    const update = () => setViewport(window.innerHeight)
    window.addEventListener('resize', update)
    window.addEventListener('orientationchange', update)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('orientationchange', update)
    }
  }, [])

  // A newly selected resident opens the sheet halfway (state adjusted during render, not in an effect).
  const [lastWake, setLastWake] = useState(wake)
  if (wake !== lastWake) {
    setLastWake(wake)
    if (wake !== null && snap === 'peek') setSnap('half')
  }

  const onPointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    drag.current = { startY: event.clientY, startPx: heights(peek, viewport)[snap], moved: false }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const onPointerMove = (event: PointerEvent<HTMLButtonElement>) => {
    if (!drag.current) return
    const dy = drag.current.startY - event.clientY
    if (Math.abs(dy) > 6) drag.current.moved = true
    if (drag.current.moved) {
      const h = heights(peek, viewport)
      setDragPx(Math.min(h.full, Math.max(h.peek - 40, drag.current.startPx + dy)))
    }
  }

  // A drag settles where the thumb left it, and so does a gesture the browser takes back (it
  // decided the swipe was a scroll). Neither is a tap: the button's click is the tap.
  const settle = () => {
    if (!drag.current) return
    const { moved } = drag.current
    drag.current = null
    if (moved && dragPx !== null) {
      setSnap(nearest(dragPx, peek, viewport))
      dragged.current = true
    }
    setDragPx(null)
  }

  // One tap opens the sheet, the next closes it, and the height transition carries it. The middle
  // height is still there under the thumb, by dragging. Enter and Space reach this too: it is a
  // button.
  const toggle = () => {
    if (dragged.current) {
      dragged.current = false
      return
    }
    setSnap((current) => (current === 'full' ? 'peek' : 'full'))
  }

  const style = {
    '--sheet-peek': `${peek}px`,
    '--sheet-vh': `${viewport}px`,
    ...(dragPx !== null && { height: `${dragPx}px`, transition: 'none' }),
  } as CSSProperties

  return (
    <section className="sheet" data-snap={snap} style={style} aria-label={t('sheet.label')}>
      <div className="sheet-grab">
        <button
          ref={grab}
          type="button"
          className="sheet-handle"
          aria-label={t(`sheet.${snap}`)}
          aria-expanded={snap !== 'peek'}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={settle}
          onPointerCancel={settle}
          onClick={toggle}
        />
      </div>
      <div ref={headerBox} className="sheet-header">
        {header}
      </div>
      <div className="sheet-body">{children}</div>
    </section>
  )
}
