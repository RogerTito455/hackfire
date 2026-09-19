import { hotspotColor, MINI } from './miniDemoScript'

// The hero's backdrop: every sampled hotspot of 23 July, lit in the order the satellites saw it
// and coloured by its age at the end of the day. Pure CSS animation, off under reduced motion.
const END_MINUTE = 1440
const IGNITION_SECONDS = 2.6

export function FireField() {
  return (
    <svg className="fire-field" viewBox={`0 0 ${MINI.width} ${MINI.height}`} aria-hidden="true">
      <defs>
        <filter id="fire-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="14" />
        </filter>
      </defs>
      <g className="fire-glow" filter="url(#fire-glow)">
        {MINI.hotspots.map(([x, y, minute], index) => (
          <circle key={index} cx={x} cy={y} r={16} fill={hotspotColor((END_MINUTE - minute) / 60)} />
        ))}
      </g>
      <g className="fire-embers">
        {MINI.hotspots.map(([x, y, minute], index) => (
          <circle
            key={index}
            cx={x}
            cy={y}
            r={5}
            fill={hotspotColor((END_MINUTE - minute) / 60)}
            style={{ animationDelay: `${(Math.max(0, minute) / END_MINUTE) * IGNITION_SECONDS}s` }}
          />
        ))}
      </g>
    </svg>
  )
}
