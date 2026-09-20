// Map markers: the one filled icon family. See ./icons/README.md, section "Markers".
// Each function returns an inline SVG string for a MapLibre Marker element.

import { iconMarkup, type IconName } from './Icon'
import { MARKER_OUTLINE_COLOR, PLACE_MARKER_INK } from './theme'

// Teardrop pin in a 32 × 40 box: a round head centred at (16, 15), radius 13, tip at (16, 38).
const PIN_PATH = 'M16 38C11 32 3 24 3 15a13 13 0 0 1 26 0c0 9-8 17-13 23z'

/**
 * The SVG `markup` as a DOM node, for `element.replaceChildren(svgNode(...))`. Recommended by Norma —
 * fixed with Claude Sonnet 5 via Claude Code: a marker is built from the parser, not by assigning
 * `innerHTML`. The parsed document is inert (no script runs, nothing loads), and the HTML parser is
 * as forgiving as `innerHTML` was, so every marker draws as before.
 */
export function svgNode(markup: string): Element {
  const node = new DOMParser().parseFromString(markup, 'text/html').body.firstElementChild
  if (node === null || node.nodeName.toLowerCase() !== 'svg') throw new Error('Marker markup is not an SVG')
  return node
}

/** Nests an icon's own 24-grid markup as a size × size square at (x, y), inked in `color`. */
function placeIcon(icon: IconName, x: number, y: number, size: number, color: string): string {
  return iconMarkup(icon).replace('<svg ', `<svg x="${x}" y="${y}" width="${size}" height="${size}" color="${color}" `)
}

/** Drawn size of a resident pin: the 32 × 40 drawing scaled up so a thumb can hit it. */
export const STATUS_MARKER_HEIGHT = 48
const STATUS_MARKER_WIDTH = 38

/** A resident pin filled with `color`, a white outline, and the icon in white inside its head. */
export function statusMarkerSvg(color: string, icon: IconName): string {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${STATUS_MARKER_WIDTH}" height="${STATUS_MARKER_HEIGHT}" viewBox="0 0 32 40">` +
    `<path d="${PIN_PATH}" fill="${color}" stroke="${MARKER_OUTLINE_COLOR}" stroke-width="2" stroke-linejoin="round"/>` +
    placeIcon(icon, 8, 7, 16, MARKER_OUTLINE_COLOR) +
    '</svg>'
  )
}

/** A 28 px white disc with a dark outline and the icon in dark grey: the safe point and the crew base. */
export function placeMarkerSvg(icon: IconName): string {
  return (
    '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">' +
    `<circle cx="14" cy="14" r="13" fill="${MARKER_OUTLINE_COLOR}" stroke="${PLACE_MARKER_INK}" stroke-width="2"/>` +
    placeIcon(icon, 6, 6, 16, PLACE_MARKER_INK) +
    '</svg>'
  )
}
