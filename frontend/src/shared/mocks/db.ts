import type { MockDatabase } from './dbTypes'
import { createSeedDatabase } from './seed'

const STORAGE_KEY = 'botforge.mock.database.v1'

let cache: MockDatabase | null = null

function readStorage(): MockDatabase | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as MockDatabase
  } catch {
    return null
  }
}

export function getDb(): MockDatabase {
  if (cache) return cache
  const stored = readStorage()
  if (stored) {
    cache = stored
    return stored
  }
  cache = createSeedDatabase()
  persistDb()
  return cache
}

export function persistDb() {
  if (typeof window === 'undefined' || !cache) return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cache))
  } catch {
    // Storage can be full or blocked; the in-memory DB still works.
  }
}

export function resetDb() {
  cache = createSeedDatabase()
  persistDb()
  return cache
}
