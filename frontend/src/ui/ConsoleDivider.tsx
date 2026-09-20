import { useState, type KeyboardEvent, type PointerEvent } from 'react'
import { useI18n } from './i18n'

// The line between the console and the map on a laptop: drag it to give either side more room.
// The line itself is a hairline, but the grip in the middle is a 44 px target, and the whole
// divider takes focus so the keyboard can move it without a pointer at all.

/** One arrow key, and one arrow key with shift. */
const STEP = 16
const BIG_STEP = 64

interface ConsoleDividerProps {
  /** The console's width in pixels: where the divider sits, and what it reports to a reader. */
  width: number
  min: number
  max: number
  onWidthChange: (width: number) => void
}

export function ConsoleDivider({ width, min, max, onWidthChange }: ConsoleDividerProps) {
  const { t } = useI18n()
  const [dragging, setDragging] = useState(false)

  const move = (next: number) => onWidthChange(Math.min(max, Math.max(min, next)))

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    event.preventDefault()
    setDragging(true)
  }

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    // The console starts at the left edge, so the pointer's x is the width it is asking for.
    if (dragging) move(event.clientX)
  }

  const onPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    setDragging(false)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? BIG_STEP : STEP
    if (event.key === 'ArrowLeft') move(width - step)
    else if (event.key === 'ArrowRight') move(width + step)
    else if (event.key === 'Home') move(min)
    else if (event.key === 'End') move(max)
    else return
    event.preventDefault()
  }

  return (
    <div
      className={dragging ? 'console-divider dragging' : 'console-divider'}
      role="separator"
      tabIndex={0}
      aria-orientation="vertical"
      aria-label={t('console.divider')}
      aria-valuenow={width}
      aria-valuemin={min}
      aria-valuemax={max}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onKeyDown={onKeyDown}
    >
      <span className="console-grip" aria-hidden="true" />
    </div>
  )
}
