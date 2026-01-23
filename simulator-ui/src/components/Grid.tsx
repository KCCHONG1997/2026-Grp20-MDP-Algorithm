import React from 'react'
import type { CellState, Direction, Obstacle } from '../types'

const CELL = 28
const PAD = 24
const WIDTH = 20
const HEIGHT = 20

function toCanvas(x: number, y: number) {
  const cx = PAD + x * CELL + CELL / 2
  const cy = PAD + (HEIGHT - 1 - y) * CELL + CELL / 2
  return { cx, cy }
}

function angleFor(d: Direction) {
  switch (d) {
    case 0: return -Math.PI / 2
    case 2: return 0
    case 4: return Math.PI / 2
    case 6: return Math.PI
    default: return 0
  }
}

export interface GridProps {
  obstacles: Obstacle[]
  path?: CellState[]
  highlightIndex?: number
}

export const Grid: React.FC<GridProps> = ({ obstacles, path, highlightIndex }) => {
  const w = PAD * 2 + WIDTH * CELL
  const h = PAD * 2 + HEIGHT * CELL

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <defs>
        <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0c141d" />
          <stop offset="100%" stopColor="#0a1118" />
        </linearGradient>
        <linearGradient id="pathGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#00d0ff" />
          <stop offset="100%" stopColor="#4ea1ff" />
        </linearGradient>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      {/* background */}
      <rect x={0} y={0} width={w} height={h} fill="url(#bgGrad)" stroke="#1f2833" />

      {/* grid lines */}
      {Array.from({ length: WIDTH + 1 }).map((_, i) => (
        <line key={`v${i}`} x1={PAD + i * CELL} y1={PAD} x2={PAD + i * CELL} y2={PAD + HEIGHT * CELL} stroke="#1f2833" />
      ))}
      {Array.from({ length: HEIGHT + 1 }).map((_, j) => (
        <line key={`h${j}`} x1={PAD} y1={PAD + j * CELL} x2={PAD + WIDTH * CELL} y2={PAD + j * CELL} stroke="#1f2833" />
      ))}

      {/* obstacles */}
      {obstacles.map((o) => {
        const { cx, cy } = toCanvas(o.x, o.y)
        const x0 = cx - CELL / 2
        const y0 = cy - CELL / 2
        const side = (
          o.d === 0 ? (<line x1={x0} y1={y0} x2={x0 + CELL} y2={y0} stroke="#6f42c1" strokeWidth={3} />) :
          o.d === 2 ? (<line x1={x0 + CELL} y1={y0} x2={x0 + CELL} y2={y0 + CELL} stroke="#6f42c1" strokeWidth={3} />) :
          o.d === 4 ? (<line x1={x0} y1={y0 + CELL} x2={x0 + CELL} y2={y0 + CELL} stroke="#6f42c1" strokeWidth={3} />) :
          o.d === 6 ? (<line x1={x0} y1={y0} x2={x0} y2={y0 + CELL} stroke="#6f42c1" strokeWidth={3} />) : null
        )
        const ang = angleFor(o.d)
        const s = CELL * 0.35
        const tip = { x: cx + Math.cos(ang) * s, y: cy + Math.sin(ang) * s }
        const left = { x: cx + Math.cos(ang + Math.PI * 0.75) * s * 0.6, y: cy + Math.sin(ang + Math.PI * 0.75) * s * 0.6 }
        const right = { x: cx + Math.cos(ang - Math.PI * 0.75) * s * 0.6, y: cy + Math.sin(ang - Math.PI * 0.75) * s * 0.6 }
        return (
          <g key={`ob-${o.id}`}>
            <rect x={x0} y={y0} width={CELL} height={CELL} fill="#d9534f" stroke="#a94442" />
            {side}
            <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle" fontSize={12} fill="#ffffff">{o.id}</text>
            {/* facing triangle */}
            <polygon points={`${tip.x},${tip.y} ${left.x},${left.y} ${right.x},${right.y}`} fill="#6f42c1" />
          </g>
        )
      })}

      {/* path polyline */}
      {path && path.length > 0 && (
        <>
          {/* outer glow */}
          <polyline
            fill="none"
            stroke="#00d0ff"
            strokeOpacity={0.35}
            strokeWidth={6}
            filter="url(#glow)"
            points={path.map(p => { const { cx, cy } = toCanvas(p.x, p.y); return `${cx},${cy}` }).join(' ')}
          />
          <polyline
            fill="none"
            stroke="url(#pathGrad)"
            strokeWidth={2.2}
            points={path.map(p => { const { cx, cy } = toCanvas(p.x, p.y); return `${cx},${cy}` }).join(' ')}
          />
        </>
      )}

      {/* headings along path */}
      {path && path.map((p, i) => {
        const { cx, cy } = toCanvas(p.x, p.y)
        const ang = angleFor(p.d)
        const s = CELL * 0.3
        const tip = { x: cx + Math.cos(ang) * s, y: cy + Math.sin(ang) * s }
        const left = { x: cx + Math.cos(ang + Math.PI * 0.75) * s * 0.6, y: cy + Math.sin(ang + Math.PI * 0.75) * s * 0.6 }
        const right = { x: cx + Math.cos(ang - Math.PI * 0.75) * s * 0.6, y: cy + Math.sin(ang - Math.PI * 0.75) * s * 0.6 }
        const fill = (highlightIndex === i) ? '#3fb950' : 'rgba(255,255,255,0.65)'
        return <polygon key={`hd-${i}`} points={`${tip.x},${tip.y} ${left.x},${left.y} ${right.x},${right.y}`} fill={fill} />
      })}

      {/* start/end markers */}
      {path && path.length > 0 && (() => {
        const s0 = toCanvas(path[0].x, path[0].y)
        const se = toCanvas(path[path.length - 1].x, path[path.length - 1].y)
        return (
          <g>
            <circle cx={s0.cx} cy={s0.cy} r={5} fill="#3fb950" />
            <circle cx={se.cx} cy={se.cy} r={5} fill="#ff9800" />
          </g>
        )
      })()}
    </svg>
  )
}
export default Grid
