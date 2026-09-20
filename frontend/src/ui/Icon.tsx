// The dashboard's icon set. Rules, catalogue and how to add one: ./icons/README.md.

import './icons.css'

// Every file in ./icons as its raw SVG text, keyed by path ('./icons/play.svg').
const FILES = import.meta.glob<string>('./icons/*.svg', { query: '?raw', import: 'default', eager: true })

// The icon set is one module on purpose: names, markup and component in one import. The only
// cost is a full page reload instead of React fast refresh when this file changes, so the
// fast-refresh lint rule is switched off for the two non-component exports below.

// Keep in step with the files and the README catalogue; `pnpm check` fails when they differ.
// oxlint-disable-next-line react/only-export-components
export const ICON_NAMES = [
  'bell',
  'burned-area',
  'car',
  'close',
  'exit',
  'fire-truck',
  'flag',
  'flame',
  'hourglass',
  'home',
  'lifebuoy',
  'live',
  'logo',
  'mic',
  'mic-off',
  'pause',
  'phone',
  'phone-missed',
  'play',
  'replay',
  'reset',
  'road-closed',
  'route',
  'satellite',
  'walk',
] as const

export type IconName = (typeof ICON_NAMES)[number]

const MARKUP = new Map(
  Object.entries(FILES).map(([path, svg]) => [path.slice('./icons/'.length, -'.svg'.length), svg.trim()]),
)

/** The icon's raw SVG, drawn in currentColor on the 24 × 24 grid. */
// oxlint-disable-next-line react/only-export-components
export function iconMarkup(name: IconName): string {
  return MARKUP.get(name) ?? ''
}

interface IconProps {
  name: IconName
  /** Rendered width and height in CSS pixels. */
  size?: number
  className?: string
}

/**
 * Decorative icon: hidden from assistive technology, so the surrounding button or text
 * carries the accessible name. It takes the text colour of its parent.
 */
export function Icon({ name, size = 20, className }: IconProps) {
  return (
    <span
      className={className ? `icon ${className}` : 'icon'}
      aria-hidden="true"
      style={{ width: size, height: size }}
      // Safe: the markup is one of our own static files in ./icons, bundled at build time and
      // validated by scripts/check-icons.mjs. No user or network data ever reaches it.
      dangerouslySetInnerHTML={{ __html: iconMarkup(name) }}
    />
  )
}
