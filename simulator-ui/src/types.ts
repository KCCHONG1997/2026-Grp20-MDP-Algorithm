export type Direction = 0 | 2 | 4 | 6 | 8;

export interface Obstacle {
  x: number;
  y: number;
  id: number;
  d: Direction; // 0=N,2=E,4=S,6=W, 8=SKIP
}

export interface CellState {
  x: number;
  y: number;
  d: Direction;
  s: number; // screenshot id (or -1)
}

export interface PathResponse {
  data: {
    distance: number;
    path: CellState[];
    commands: string[];
  };
  error: any;
}
