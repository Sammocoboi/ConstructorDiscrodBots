import { execFileSync } from 'node:child_process'
import { mkdirSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

const envPath = resolve(process.cwd(), '.env')
if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/)
    if (match && !process.env[match[1]]) process.env[match[1]] = match[2].replace(/^"|"$/g, '')
  }
}

const schemaUrl =
  process.env.VITE_OPENAPI_URL ?? process.argv[2] ?? 'http://localhost:8000/api/schema/'
const output = resolve(process.cwd(), 'src/shared/api/schema.d.ts')

mkdirSync(dirname(output), { recursive: true })
console.log(`Generating API types from ${schemaUrl}…`)
execFileSync(
  process.platform === 'win32' ? 'npx.cmd' : 'npx',
  ['openapi-typescript', schemaUrl, '-o', output],
  { stdio: 'inherit' },
)
writeFileSync(
  resolve(process.cwd(), 'src/shared/api/schema.readme.md'),
  'Generated from OpenAPI by `npm run api:types`. Do not edit `schema.d.ts` manually.\n',
)
console.log(`Types written to ${output}`)
