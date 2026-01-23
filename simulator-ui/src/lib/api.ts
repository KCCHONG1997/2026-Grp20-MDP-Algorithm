import type { PathResponse, Direction, Obstacle } from '../types'

const BASE = '/api'

export async function getStatus(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/status`)
    if (!r.ok) return false
    const j = await r.json()
    return j?.result === 'ok'
  } catch {
    return false
  }
}

export interface PathBody {
  obstacles: Obstacle[]
  robot_x: number
  robot_y: number
  robot_dir: Direction
  retrying: boolean
}

export async function getPath(body: PathBody): Promise<PathResponse> {
  const r = await fetch(`${BASE}/path`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`/path ${r.status}`)
  return r.json()
}
