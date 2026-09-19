// Enforces the icon format documented in src/ui/icons/README.md. Plain Node, no dependencies.
// Run with `pnpm --filter frontend icons:check`; `pnpm check` runs it before the build.

import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), '..')
const ICONS_DIR = join(FRONTEND, 'src/ui/icons')
const README = join(ICONS_DIR, 'README.md')
const ICON_MODULE = join(FRONTEND, 'src/ui/Icon.tsx')

const ROOT_ATTRIBUTES = {
  xmlns: 'http://www.w3.org/2000/svg',
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2',
  'stroke-linecap': 'round',
  'stroke-linejoin': 'round',
}

const SHAPES = new Set(['path', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'rect'])

const GEOMETRY = ['d', 'cx', 'cy', 'r', 'rx', 'ry', 'x', 'y', 'width', 'height', 'x1', 'y1', 'x2', 'y2', 'points']
const SHAPE_ATTRIBUTES = new Set([...GEOMETRY, 'fill', 'stroke', 'stroke-dasharray', 'pathLength'])

const ELEMENT_REASONS = {
  title: 'no <title>: the accessible name comes from the button or label around the icon',
  text: 'no <text>: icons carry no words',
  style: 'no <style>: colour comes only from currentColor',
  linearGradient: 'no gradients',
  radialGradient: 'no gradients',
  mask: 'no masks',
  clipPath: 'no clips',
  g: 'no <g>: draw the shapes directly',
  svg: 'no nested <svg>',
}

const ATTRIBUTE_REASONS = {
  id: 'no ids',
  class: 'no classes',
  style: 'no style attributes: colour comes only from currentColor',
  transform: 'no transforms: draw the shape where it belongs',
  mask: 'no masks',
  'clip-path': 'no clips',
  filter: 'no filters',
  'stroke-width': 'stroke is 2 px everywhere: set only on the root',
  'stroke-linecap': 'round caps come from the root',
  'stroke-linejoin': 'round joins come from the root',
}

// The 2–22 live area holds the ink. A stroked shape's geometry must stay in 3–21 so its 1 px
// half-stroke stays inside; a filled dot (stroke="none") may use the whole 2–22.
const LIVE = { min: 2, max: 22 }
const HALF_STROKE = 1

const errors = []
const fail = (where, message) => errors.push(`${where}: ${message}`)

const TAG = /<(\/?)([A-Za-z][\w:-]*)((?:\s+[\w:-]+\s*=\s*"[^"]*")*)\s*(\/?)>/y
const ATTRIBUTE = /([\w:-]+)\s*=\s*"([^"]*)"/g

/** Splits a file into tags. Anything that is not a tag or whitespace is reported and skipped. */
function parseTags(source, where) {
  const tags = []
  let index = 0
  while (index < source.length) {
    const rest = source.slice(index)
    const space = /^\s+/.exec(rest)
    if (space) {
      index += space[0].length
      continue
    }
    TAG.lastIndex = index
    const match = TAG.exec(source)
    if (!match) {
      const snippet = rest.slice(0, 30).replace(/\s+/g, ' ')
      fail(where, `unexpected content "${snippet}": only tags with double-quoted attributes; no text, comments or prolog`)
      // Resume at the next tag: after this one if it is malformed, else after the text.
      const next = rest.startsWith('<') ? rest.indexOf('>') + 1 : rest.indexOf('<')
      if (next <= 0) return tags
      index += next
      continue
    }
    const [, closing, name, attributeText, selfClosing] = match
    const attributes = {}
    for (const [, key, value] of attributeText.matchAll(ATTRIBUTE)) attributes[key] = value
    tags.push({ name, attributes, closing: closing === '/', selfClosing: selfClosing === '/' })
    index += match[0].length
  }
  return tags
}

/** End points of every path segment. Control points and arc bulges are not checked. */
function pathPoints(d) {
  const points = []
  let index = 0
  let command = ''
  let x = 0
  let y = 0
  let startX = 0
  let startY = 0
  const skip = () => {
    while (index < d.length && /[\s,]/.test(d[index])) index += 1
  }
  const number = () => {
    skip()
    const match = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/.exec(d.slice(index))
    if (!match) throw new Error(`expected a number at character ${index} of the path`)
    index += match[0].length
    return Number(match[0])
  }
  const skipNumbers = (count) => {
    for (let k = 0; k < count; k += 1) number()
  }
  const flag = () => {
    skip()
    if (d[index] !== '0' && d[index] !== '1') throw new Error(`expected an arc flag at character ${index}`)
    index += 1
  }
  for (;;) {
    skip()
    if (index >= d.length) return points
    if (/[A-Za-z]/.test(d[index])) command = d[index++]
    else if (!command) throw new Error(`expected a command at character ${index} of the path`)
    const relative = command === command.toLowerCase()
    const baseX = relative ? x : 0
    const baseY = relative ? y : 0
    switch (command.toUpperCase()) {
      case 'M':
        x = baseX + number()
        y = baseY + number()
        startX = x
        startY = y
        command = relative ? 'l' : 'L'
        break
      case 'L':
      case 'T':
        x = baseX + number()
        y = baseY + number()
        break
      case 'H':
        x = baseX + number()
        break
      case 'V':
        y = baseY + number()
        break
      case 'C':
        skipNumbers(4)
        x = baseX + number()
        y = baseY + number()
        break
      case 'S':
      case 'Q':
        skipNumbers(2)
        x = baseX + number()
        y = baseY + number()
        break
      case 'A':
        skipNumbers(3)
        flag()
        flag()
        x = baseX + number()
        y = baseY + number()
        break
      case 'Z':
        x = startX
        y = startY
        command = ''
        break
      default:
        throw new Error(`unknown path command "${command}"`)
    }
    points.push([x, y])
  }
}

function numbers(value) {
  return (value.match(/[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/g) ?? []).map(Number)
}

/** Extent of a shape as [minX, minY, maxX, maxY], or null if it cannot be computed. */
function extent(name, a) {
  const n = (key) => Number(a[key] ?? 0)
  let xs = []
  let ys = []
  if (name === 'circle') {
    xs = [n('cx') - n('r'), n('cx') + n('r')]
    ys = [n('cy') - n('r'), n('cy') + n('r')]
  } else if (name === 'ellipse') {
    xs = [n('cx') - n('rx'), n('cx') + n('rx')]
    ys = [n('cy') - n('ry'), n('cy') + n('ry')]
  } else if (name === 'rect') {
    xs = [n('x'), n('x') + n('width')]
    ys = [n('y'), n('y') + n('height')]
  } else if (name === 'line') {
    xs = [n('x1'), n('x2')]
    ys = [n('y1'), n('y2')]
  } else if (name === 'polyline' || name === 'polygon') {
    const values = numbers(a.points ?? '')
    xs = values.filter((_, i) => i % 2 === 0)
    ys = values.filter((_, i) => i % 2 === 1)
  } else if (name === 'path') {
    const points = pathPoints(a.d ?? '')
    xs = points.map(([px]) => px)
    ys = points.map(([, py]) => py)
  }
  if (xs.length === 0) return null
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
}

function checkColourText(source, where) {
  const hex = source.match(/#[0-9a-fA-F]{3,8}\b/)
  if (hex) fail(where, `hard-coded colour ${hex[0]}: use currentColor`)
  const functional = source.match(/\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(/)
  if (functional) fail(where, `hard-coded colour ${functional[0]}…): use currentColor`)
}

function checkRoot(tag, where) {
  if (!tag || tag.name !== 'svg' || tag.closing) {
    fail(where, 'the file must start with the <svg> root')
    return
  }
  for (const [key, expected] of Object.entries(ROOT_ATTRIBUTES)) {
    if (!(key in tag.attributes)) fail(where, `root is missing ${key}="${expected}"`)
    else if (tag.attributes[key] !== expected) fail(where, `root ${key} must be "${expected}", found "${tag.attributes[key]}"`)
  }
  for (const key of Object.keys(tag.attributes)) {
    if (key in ROOT_ATTRIBUTES) continue
    const reason =
      key === 'width' || key === 'height' ? 'no width or height: CSS sizes the icon' : (ATTRIBUTE_REASONS[key] ?? 'not part of the format')
    fail(where, `root attribute ${key}: ${reason}`)
  }
}

function checkShape(tag, where) {
  const { name, attributes } = tag
  const at = `${where} <${name}>`
  for (const key of Object.keys(attributes)) {
    if (!SHAPE_ATTRIBUTES.has(key)) fail(at, `attribute ${key}: ${ATTRIBUTE_REASONS[key] ?? 'not part of the format'}`)
  }
  const { fill, stroke } = attributes
  if (fill !== undefined && fill !== 'none' && fill !== 'currentColor') {
    fail(at, `fill="${fill}": only none or currentColor`)
  }
  if (stroke !== undefined && stroke !== 'none' && stroke !== 'currentColor') {
    fail(at, `stroke="${stroke}": only none or currentColor`)
  }
  if (fill === 'currentColor' && stroke !== 'none') {
    fail(at, 'a filled shape is a tiny dot: add stroke="none"')
  }
  if (name === 'rect') {
    const rx = Number(attributes.rx)
    if (!(rx >= 1 && rx <= 2)) fail(at, `rectangles need rounded corners, rx between 1 and 2 (found ${attributes.rx ?? 'none'})`)
  }
  let box
  try {
    box = extent(name, attributes)
  } catch (error) {
    fail(at, error.message)
    return
  }
  if (!box) return
  const inset = stroke === 'none' ? 0 : HALF_STROKE
  const [minX, minY, maxX, maxY] = box
  const low = LIVE.min + inset
  const high = LIVE.max - inset
  if (minX < low || minY < low || maxX > high || maxY > high) {
    const round = (value) => Math.round(value * 100) / 100
    fail(
      at,
      `outside the live area: spans x ${round(minX)}–${round(maxX)}, y ${round(minY)}–${round(maxY)}; ` +
        `${inset ? 'stroked geometry' : 'a dot'} must stay within ${low}–${high}`,
    )
  }
}

function checkIconFile(file) {
  const where = `icons/${file}`
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*\.svg$/.test(file)) fail(where, 'file names are kebab-case: <name>.svg')
  const source = readFileSync(join(ICONS_DIR, file), 'utf8')
  checkColourText(source, where)
  const tags = parseTags(source, where)
  if (tags.length === 0) return
  checkRoot(tags[0], where)
  const last = tags.at(-1)
  if (!last.closing || last.name !== 'svg') fail(where, 'the file must end with </svg>')
  for (const tag of tags.slice(1, -1)) {
    if (!SHAPES.has(tag.name)) {
      if (!tag.closing) {
        fail(where, `<${tag.name}>: ${ELEMENT_REASONS[tag.name] ?? `only ${[...SHAPES].join(', ')} are allowed`}`)
      }
      continue
    }
    if (tag.closing) continue
    if (!tag.selfClosing) fail(where, `<${tag.name}> must be self-closing: <${tag.name} … />`)
    checkShape(tag, where)
  }
  if (tags.length < 3) fail(where, 'the icon draws nothing')
}

function readmeCatalogue() {
  const names = []
  if (!existsSync(README)) {
    fail('icons/README.md', 'missing: it holds the rules and the catalogue')
    return names
  }
  const source = readFileSync(README, 'utf8')
  for (const line of source.split('\n')) {
    const row = /^\|\s*<img src="([^"]+)\.svg"[^|]*\|\s*`([^`]+)`\s*\|/.exec(line)
    if (!row) continue
    const [, image, name] = row
    if (image !== name) fail('icons/README.md', `catalogue row \`${name}\` previews ${image}.svg`)
    names.push(name)
  }
  return names
}

function iconModuleNames() {
  const source = readFileSync(ICON_MODULE, 'utf8')
  const list = /export const ICON_NAMES = \[([\s\S]*?)\] as const/.exec(source)
  if (!list) {
    fail('ui/Icon.tsx', 'could not find `export const ICON_NAMES = [...] as const`')
    return []
  }
  return [...list[1].matchAll(/'([^']+)'|"([^"]+)"/g)].map((match) => match[1] ?? match[2])
}

function compare(expected, actual, what) {
  const actualSet = new Set(actual)
  const expectedSet = new Set(expected)
  for (const name of expected) if (!actualSet.has(name)) fail(what.missingWhere, `${name}: ${what.missing}`)
  for (const name of actual) if (!expectedSet.has(name)) fail(what.extraWhere, `${name}: ${what.extra}`)
  const duplicates = actual.filter((name, index) => actual.indexOf(name) !== index)
  for (const name of new Set(duplicates)) fail(what.extraWhere, `${name} is listed twice`)
}

const files = readdirSync(ICONS_DIR).filter((file) => file.endsWith('.svg')).sort()
for (const file of files) checkIconFile(file)

const fileNames = files.map((file) => file.slice(0, -'.svg'.length))
compare(fileNames, readmeCatalogue(), {
  missingWhere: 'icons/README.md',
  missing: 'has a file but no catalogue row',
  extraWhere: 'icons/README.md',
  extra: 'has a catalogue row but no file',
})
compare(fileNames, iconModuleNames(), {
  missingWhere: 'ui/Icon.tsx',
  missing: 'has a file but is missing from ICON_NAMES',
  extraWhere: 'ui/Icon.tsx',
  extra: 'is in ICON_NAMES but has no file',
})

if (errors.length > 0) {
  console.error(`Icon check failed (${errors.length}). The rules are in src/ui/icons/README.md.\n`)
  for (const error of errors) console.error(`  ${error}`)
  process.exit(1)
}
console.log(`Icon check passed: ${files.length} icons, catalogue and ICON_NAMES in step.`)
