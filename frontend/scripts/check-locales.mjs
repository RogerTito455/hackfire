// Fails when the locales drift apart: every src/locales/*.json must have exactly the keys of en.json
// (plural forms aside) with the same {placeholders}, and every key the code asks for must exist.
// Keys built at run time (t(`status.${status}`)) are checked by their fixed prefix.

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const ROOT = new URL('..', import.meta.url).pathname
const LOCALES = join(ROOT, 'src/locales')
const REFERENCE = 'en'
const PLURAL_FORMS = new Set(['zero', 'one', 'two', 'few', 'many', 'other'])

const problems = []

/** Leaf keys with their placeholders; a plural object counts as one leaf. */
function leaves(node, prefix = '', out = new Map()) {
  for (const [key, value] of Object.entries(node)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (path === '_meta') continue
    if (typeof value === 'string') out.set(path, placeholders(value))
    else if (Object.keys(value).every((form) => PLURAL_FORMS.has(form))) {
      if (!('other' in value)) problems.push(`${path}: a plural needs an "other" form`)
      out.set(path, placeholders(Object.values(value).join(' ')))
    } else leaves(value, path, out)
  }
  return out
}

function placeholders(text) {
  return [...new Set([...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]))].sort().join(',')
}

const catalogue = Object.fromEntries(
  readdirSync(LOCALES)
    .filter((file) => file.endsWith('.json'))
    .map((file) => [file.slice(0, -5), JSON.parse(readFileSync(join(LOCALES, file), 'utf8'))]),
)
const reference = leaves(catalogue[REFERENCE])

for (const [code, messages] of Object.entries(catalogue)) {
  if (!messages._meta?.name || !messages._meta?.intl) problems.push(`${code}.json: _meta needs "name" and "intl"`)
  if (code === REFERENCE) continue
  const keys = leaves(messages)
  for (const [key, vars] of reference) {
    if (!keys.has(key)) problems.push(`${code}.json: missing "${key}"`)
    else if (keys.get(key) !== vars) problems.push(`${code}.json: "${key}" uses {${keys.get(key)}}, en uses {${vars}}`)
  }
  for (const key of keys.keys()) if (!reference.has(key)) problems.push(`${code}.json: "${key}" is not in en.json`)
}

function sources(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return sources(path)
    return /\.tsx?$/.test(name) ? [path] : []
  })
}

const used = new Set()
const prefixes = new Set()
for (const file of sources(join(ROOT, 'src'))) {
  const code = readFileSync(file, 'utf8')
  for (const [, key] of code.matchAll(/\bt\(\s*'([\w.]+)'/g)) {
    used.add(key)
    if (!reference.has(key)) problems.push(`${relative(ROOT, file)}: t('${key}') is not in en.json`)
  }
  // Keys chosen with a ternary: t(cond ? 'a.b' : 'a.c', ...)
  for (const [, body] of code.matchAll(/\bt\(\s*([^()]*\?[^()]*?),\s*\{/g)) {
    for (const [, key] of body.matchAll(/'([\w]+\.[\w.]+)'/g)) {
      used.add(key)
      if (!reference.has(key)) problems.push(`${relative(ROOT, file)}: '${key}' is not in en.json`)
    }
  }
  for (const [, prefix] of code.matchAll(/\bt\(\s*`([\w.]+)\.\$\{/g)) {
    prefixes.add(prefix)
    if (![...reference.keys()].some((key) => key.startsWith(`${prefix}.`))) {
      problems.push(`${relative(ROOT, file)}: no keys under "${prefix}" in en.json`)
    }
  }
}

const unused = [...reference.keys()].filter(
  (key) => !used.has(key) && ![...prefixes].some((prefix) => key.startsWith(`${prefix}.`)),
)
for (const key of unused) problems.push(`en.json: "${key}" is never used`)

if (problems.length > 0) {
  console.error(`Locale check failed:\n  ${problems.join('\n  ')}`)
  process.exit(1)
}
console.log(`Locales OK: ${Object.keys(catalogue).sort().join(', ')}, ${reference.size} texts each.`)
