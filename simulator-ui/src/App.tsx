import React, { useEffect, useMemo, useRef, useState } from 'react'
import './styles.css'
import { Grid } from './components/Grid'
import type { CellState, Direction, Obstacle } from './types'
import { getPath, getStatus } from './lib/api'

const defaultObstacles: Obstacle[] = [
  { x: 5, y: 10, id: 1, d: 2 },
  { x: 15, y: 8, id: 2, d: 0 },
  { x: 4, y: 14, id: 3, d: 6 },
  { x: 10, y: 15, id: 4, d: 4 },
  { x: 12, y: 5, id: 5, d: 2 },
]

const dirOptions: { value: Direction; label: string }[] = [
  { value: 0, label: 'NORTH (0)' },
  { value: 2, label: 'EAST (2)' },
  { value: 4, label: 'SOUTH (4)' },
  { value: 6, label: 'WEST (6)' },
]

export default function App() {
  const [serverUp, setServerUp] = useState<boolean | null>(null)
  const [obstacles, setObstacles] = useState<Obstacle[]>(defaultObstacles)
  const [robotX, setRobotX] = useState(1)
  const [robotY, setRobotY] = useState(1)
  const [robotDir, setRobotDir] = useState<Direction>(0)
  const [retrying, setRetrying] = useState(false)
  const [path, setPath] = useState<CellState[] | undefined>(undefined)
  const [commands, setCommands] = useState<string[]>([])
  const [distance, setDistance] = useState<number | null>(null)

  // animation
  const [playing, setPlaying] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [speedMs, setSpeedMs] = useState(120)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    ;(async () => setServerUp(await getStatus()))()
  }, [])

  useEffect(() => {
    if (!playing || !path || path.length === 0) return
    timer.current && window.clearInterval(timer.current)
    timer.current = window.setInterval(() => {
      setStepIdx((i) => {
        if (!path) return 0
        return (i + 1) % path.length
      })
    }, Math.max(30, speedMs))
    return () => { if (timer.current) window.clearInterval(timer.current) }
  }, [playing, path, speedMs])

  const obstaclesJson = useMemo(() => JSON.stringify(obstacles, null, 2), [obstacles])

  async function compute() {
    const res = await getPath({ obstacles, robot_x: robotX, robot_y: robotY, robot_dir: robotDir, retrying })
    setPath(res.data.path)
    setCommands(res.data.commands)
    setDistance(res.data.distance)
    setStepIdx(0)
  }

  function updateObstacle(idx: number, patch: Partial<Obstacle>) {
    setObstacles(list => list.map((o, i) => i === idx ? { ...o, ...patch } : o))
  }

  function addObstacle() {
    const nextId = (obstacles.reduce((m, o) => Math.max(m, o.id), 0) + 1) || 1
    setObstacles(list => [...list, { x: 2, y: 2, id: nextId, d: 2 }])
  }

  function removeObstacle(idx: number) {
    setObstacles(list => list.filter((_, i) => i !== idx))
  }

  return (
    <div className="app">
      <div className="panel controls">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div style={{letterSpacing: '0.08em'}}>MDP SIMULATOR</div>
          <div className={`status ${serverUp ? 'ok' : 'bad'}`}>
            <span className="led"/> {serverUp ? 'Server: OK' : 'Server: Down'}
          </div>
        </div>

        <div>
          <label>Robot start</label>
          <div className="row">
            <input type="number" min={1} max={18} value={robotX} onChange={e => setRobotX(+e.target.value)} />
            <input type="number" min={1} max={18} value={robotY} onChange={e => setRobotY(+e.target.value)} />
            <select value={robotDir} onChange={e => setRobotDir(+e.target.value as Direction)}>
              {dirOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="row">
            <label className="row"><input type="checkbox" checked={retrying} onChange={e => setRetrying(e.target.checked)} /> retrying</label>
          </div>
        </div>

        <div>
          <label>Obstacles</label>
          {obstacles.map((o, i) => (
            <div key={i} className="row">
              <input type="number" min={0} max={19} value={o.x} onChange={e => updateObstacle(i, { x: +e.target.value })} />
              <input type="number" min={0} max={19} value={o.y} onChange={e => updateObstacle(i, { y: +e.target.value })} />
              <input type="number" min={1} max={32} value={o.id} onChange={e => updateObstacle(i, { id: +e.target.value })} />
              <select value={o.d} onChange={e => updateObstacle(i, { d: +e.target.value as Direction })}>
                {dirOptions.map(o2 => <option key={o2.value} value={o2.value}>{o2.label}</option>)}
              </select>
              <button onClick={() => removeObstacle(i)}>x</button>
            </div>
          ))}
          <div className="row">
            <button onClick={addObstacle}>Add obstacle</button>
            <button className="primary" onClick={compute}>Compute /path</button>
          </div>
        </div>

        <div>
          <label>Playback speed ({speedMs} ms)</label>
          <input type="range" min={30} max={500} step={10} value={speedMs} onChange={e => setSpeedMs(+e.target.value)} />
        </div>

        <div>
          <label>Commands</label>
          <div className="commands">
            <pre style={{ margin: 0 }}>{commands.map((c, i) => (i === stepIdx ? '> ' : '  ') + c).join('\n')}</pre>
          </div>
          <div className="row">
            <button onClick={() => setPlaying(p => !p)}>{playing ? 'Pause' : 'Play'}</button>
            <button onClick={() => setStepIdx(i => Math.max(0, i - 1))}>Prev</button>
            <button onClick={() => setStepIdx(i => Math.min((path?.length ?? 1) - 1, i + 1))}>Next</button>
          </div>
          <div className="small">Obstacles JSON:</div>
          <textarea readOnly value={obstaclesJson} rows={6} />
        </div>
      </div>

      <div className="panel grid" style={{position:'relative'}}>
        <div className="hud">
          <div className="stat"><div className="k">Distance</div><div className="v">{distance ?? '-'} units</div></div>
          <div className="stat"><div className="k">Steps</div><div className="v">{path?.length ?? 0}</div></div>
          <div className="stat"><div className="k">Commands</div><div className="v">{commands.length}</div></div>
          <div className="stat"><div className="k">SNAP Count</div><div className="v">{commands.filter(c=>c.startsWith('SNAP')).length}</div></div>
        </div>
        <Grid obstacles={obstacles} path={path} highlightIndex={stepIdx} />
      </div>
    </div>
  )
}
