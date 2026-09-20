import { useEffect, useRef, useState, type CSSProperties, type PointerEvent, type ReactNode } from 'react'
import { useI18n } from './i18n'

// The phone layout's bottom sheet, like a native maps app: the map stays full screen and the
// panels live in a sheet the thumb drags between three heights. On wide screens CSS turns it into a
// side panel and the handle disappears. Pure presentation: the only state is how open it is.

export type SheetSnap = 'peek' | 'half' | 'full'

const ORDER: readonly SheetSnap[] = ['peek', 'half', 'full']

/** Before the header is measured, and the least a peek can be. */
const PEEK_FALLBACK = 196

/** The panel half opens on to; the CSS rule for [data-snap='half'] says the same in vh. */
const HALF_BODY = 240

/** Visible height of each snap, in pixels: peek shows the whole header, whatever the language. */
function heights(peek: number): Record<SheetSnap, number> {
  const viewport = window.innerHeight
  const full = Math.round(viewport * 0.9)
  // A header with a scrubber, four counters and a live note can be 290 px on a phone: half has to
  // clear it, or opening the sheet shows a strip of panel and looks like it did not open at all.
  return { peek, half: Math.min(full, Math.max(peek + HALF_BODY, Math.round(viewport * 0.52))), full }
}

function nearest(px: number, peek: number): SheetSnap {
  const h = heights(peek)
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
  const grab = useRef<HTMLDivElement | null>(null)
  const headerBox = useRef<HTMLDivElement | null>(null)
  const [peek, setPeek] = useState(PEEK_FALLBACK)

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

  // A newly selected resident opens the sheet halfway (state adjusted during render, not in an effect).
  const [lastWake, setLastWake] = useState(wake)
  if (wake !== lastWake) {
    setLastWake(wake)
    if (wake !== null && snap === 'peek') setSnap('half')
  }

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    drag.current = { startY: event.clientY, startPx: heights(peek)[snap], moved: false }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return
    const dy = drag.current.startY - event.clientY
    if (Math.abs(dy) > 6) drag.current.moved = true
    if (drag.current.moved) {
      const h = heights(peek)
      setDragPx(Math.min(h.full, Math.max(h.peek - 40, drag.current.startPx + dy)))
    }
  }

  const settle = (tapped: boolean) => {
    if (!drag.current) return
    const { moved } = drag.current
    drag.current = null
    if (moved && dragPx !== null) setSnap(nearest(dragPx, peek))
    else if (tapped) setSnap((current) => ORDER[(ORDER.indexOf(current) + 1) % ORDER.length])
    setDragPx(null)
  }

  const onPointerUp = () => settle(true)

  // The browser can take the gesture back (it decides the swipe was a scroll). That is not a tap on
  // the handle: settle where the drag reached, and leave the sheet where it is if it never moved.
  const onPointerCancel = () => settle(false)

  const style = {
    '--sheet-peek': `${peek}px`,
    ...(dragPx !== null && { height: `${dragPx}px`, transition: 'none' }),
  } as CSSProperties

  return (
    <section className="sheet" data-snap={snap} style={style} aria-label={t('sheet.label')}>
      <div
        ref={grab}
        className="sheet-grab"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerCancel}
      >
        <button
          type="button"
          className="sheet-handle"
          aria-label={t(`sheet.${snap}`)}
          aria-expanded={snap !== 'peek'}
          onClick={(event) => event.preventDefault()}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              setSnap((current) => ORDER[(ORDER.indexOf(current) + 1) % ORDER.length])
            }
          }}
        />
      </div>
      <div ref={headerBox} className="sheet-header">
        {header}
      </div>
      <div className="sheet-body">{children}</div>
    </section>
  )
}
