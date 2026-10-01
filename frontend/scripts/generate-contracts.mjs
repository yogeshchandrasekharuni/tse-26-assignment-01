import { compileFromFile } from 'json-schema-to-typescript'
import { readFile, writeFile, mkdir } from 'node:fs/promises'

const result = await compileFromFile('../schemas/client.schema.json', {
  bannerComment: '/* Generated from strict Python models by make contracts. Do not edit. */',
  unknownAny: true,
  additionalProperties: false,
  unreachableDefinitions: true,
  style: { singleQuote: true, semi: false },
})
if (process.argv.includes('--check')) {
  if (await readFile('src/generated/contracts.ts', 'utf8') !== result) throw new Error('Stale browser types; run make contracts')
} else {
  await mkdir('src/generated', { recursive: true })
  await writeFile('src/generated/contracts.ts', result)
}
