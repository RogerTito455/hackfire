# Icons

The dashboard's icons, drawn by hand for HackFire. CLAUDE.md rules out icon packages, so every icon lives here as one small SVG file that follows the format below. `pnpm check` enforces the format through [`frontend/scripts/check-icons.mjs`](../../../scripts/check-icons.mjs).

## Using an icon

```tsx
import { Icon } from './Icon'

<button type="button" className="icon-button" onClick={onTogglePlay} aria-label={t('replay.play')}>
  <Icon name="play" size={16} />
</button>
```

- `<Icon name size? className? />` renders `<span class="icon" aria-hidden="true">` with the SVG inside. The default size is 20 px.
- The icon takes its parent's text colour (`currentColor`): set `color` on the button or label, never on the icon.
- The icon is hidden from screen readers. The button's `aria-label` or its visible text carries the name.
- `.icon-button` (in `ui/icons.css`) lines up an icon and text: centred, 6 px gap.
- `iconMarkup(name)` returns the raw SVG string, for code that needs a string, such as map markers.
- `STATUS_ICON` in `ui/theme.ts` gives the icon for each triage status.

## The format: rounded outline

Every file in this folder follows these rules. The checker fails `pnpm check` when one is broken.

- **One file per icon:** `icons/<kebab-name>.svg`.
- **The root is exactly:**
  ```html
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  ```
  No width or height (CSS sizes the icon) and no other root attributes.
- **Live area 2–22.** The ink stays inside a 2 px padding. For a stroked shape, that means its coordinates stay within 3–21, so the 1 px half-stroke still fits; a filled dot may use the full 2–22. The checker tests shape bounds and path end points. It does not test how far a curve bulges between them, so check that by eye.
- **Stroke 2 px, no fills.** The stroke width, caps and joins come from the root only. Two exceptions: a tiny dot may use `fill="currentColor"` with `stroke="none"`, and a dashed outline may use `stroke-dasharray` (with `pathLength` to space the dashes evenly).
- **Rounded everywhere:** round caps and joins from the root; every `<rect>` has `rx` between 1 and 2.
- **Colour only through `currentColor`.** No hex, `rgb()` or named colours, no `style` attributes or elements.
- **Plain shapes only:** `path`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `rect`, self-closing, straight inside the root. No `<text>`, no `<title>` (the accessible name comes from the button's label), no `<g>`, no transforms, no ids or classes, no gradients, masks, clips or filters.
- **One idea per icon.** It must read at 16 px and at 24 px, on light and on dark. Keep it geometric and simple.
- **Drawn by us.** Don't copy paths from Lucide, Feather, Material or any other set.

Map markers are the one filled family: see below.

## Markers

Markers sit on a busy basemap, so they are filled and carry a white outline that keeps them readable on any background. They live in `ui/markers.ts`. Each one nests an icon's own file, so redrawing the icon updates its marker.

- `statusMarkerSvg(color, icon)`: a 32 × 40 teardrop pin filled with `color`, with a 2 px white outline and the icon in white, 16 px, centred in the pin's head. Use it with `STATUS_COLOR[status]` and `STATUS_ICON[status]`.
- `placeMarkerSvg(icon)`: a 28 px white disc with a 2 px dark grey (`#3c4043`) outline and the icon in the same grey. Use it for the safe point (`flag`) and the crew base (`fire-truck`).

Both return an SVG string with its own width and height. The pin's tip is at the bottom centre:

```ts
const element = document.createElement('div')
element.innerHTML = statusMarkerSvg(STATUS_COLOR[neighbor.status], STATUS_ICON[neighbor.status])
new Marker({ element, anchor: 'bottom' }).setLngLat([neighbor.lon, neighbor.lat]).addTo(map)
```

The marker colours (`MARKER_OUTLINE_COLOR`, `PLACE_MARKER_INK`) live in `ui/theme.ts` with the rest of the palette.

## Favicon

`frontend/public/favicon.svg` is the `logo` mark on a 32 × 32 canvas, drawn in `#d93025` (the "needs rescue" red) on a transparent background. It is the one icon file allowed a hard-coded colour, and it sits outside this folder, so the checker skips it. If you redraw `logo.svg`, copy its paths into the favicon.

## Adding an icon

1. **Draw it on the 24 grid.** Keep stroked geometry within 3–21, start from the simplest shape that carries the idea, and look at it at 16 px next to its neighbours.
2. **Add the file** as `icons/<kebab-name>.svg`, starting with the exact root line above.
3. **Add the name to `ICON_NAMES`** in `ui/Icon.tsx`.
4. **Add a catalogue row** below: preview, name, meaning, where it is used, and a one-line description of the drawing.
5. **Run `pnpm check`**, or only this check with `pnpm --filter frontend icons:check`.

## Catalogue

| Preview | Name | Meaning | Used in | Drawing |
|---|---|---|---|---|
| <img src="bell.svg" width="24"> | `bell` | Crew alerts | Crew alerts section header, alert items | A bell with a small clapper arc below it |
| <img src="burned-area.svg" width="24"> | `burned-area` | The burned area that routes avoid | Map legend | A dashed irregular polygon, like the dashed red outline on the map |
| <img src="car.svg" width="24"> | `car` | By car | Route travel mode | A car seen from the front: cabin, body, headlights and tyres |
| <img src="close.svg" width="24"> | `close` | Close a panel | Route panel | Two crossed diagonals |
| <img src="exit.svg" width="24"> | `exit` | Triage status "Evacuating" | Next to the status label, status marker | A door frame open on the right, with an arrow leaving through it |
| <img src="fire-truck.svg" width="24"> | `fire-truck` | The fire crew, their route and their base | Route mode "Crew route", crew-alert button, crew base marker | A truck seen from the side, with a raised ladder over the body |
| <img src="flag.svg" width="24"> | `flag` | A safe point: the evacuation destination | Marker at the route's end | A notched flag on a pole |
| <img src="flame.svg" width="24"> | `flame` | A satellite hotspot | Map legend | A flame with a small second tongue on its left |
| <img src="home.svg" width="24"> | `home` | A resident's home | Wherever a resident's home is shown | A house: pitched roof, walls and a door |
| <img src="hourglass.svg" width="24"> | `hourglass` | Triage status "Not called yet" | Next to the status label, status marker | An hourglass between two plates |
| <img src="lifebuoy.svg" width="24"> | `lifebuoy` | Triage status "Needs rescue" | Next to the status label, status marker | A ring with four diagonal bands |
| <img src="live.svg" width="24"> | `live` | Live mode | Map mode toggle | A dot with two broadcast arcs on each side |
| <img src="logo.svg" width="24"> | `logo` | The HackFire mark | Brand mark; the favicon is a red copy | A flame inside a rounded shield |
| <img src="pause.svg" width="24"> | `pause` | Pause the replay | Replay controls | Two rounded upright bars |
| <img src="phone-missed.svg" width="24"> | `phone-missed` | Triage status "No answer" | Next to the status label, status marker | A phone handset with a small × at the top right |
| <img src="play.svg" width="24"> | `play` | Start the replay | Replay controls | A triangle pointing right |
| <img src="replay.svg" width="24"> | `replay` | Replay mode | Map mode toggle | A clock with hands, its rim an arc with a counter-clockwise arrowhead on the left |
| <img src="reset.svg" width="24"> | `reset` | Restart the demo | Sidebar button | An open circular arrow turning counter-clockwise, arrowhead at the top; no clock hands, unlike `replay` |
| <img src="route.svg" width="24"> | `route` | Evacuation route | Route section header | Two points joined by an S-shaped path |
| <img src="satellite.svg" width="24"> | `satellite` | Data from satellites | Live-mode status bar | A satellite on the diagonal, two panels and a body, sending two signal arcs to the lower left |
| <img src="walk.svg" width="24"> | `walk` | On foot | Route travel mode | A person walking to the right |
