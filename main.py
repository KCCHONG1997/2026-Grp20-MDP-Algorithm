import time, os
from algo.algo import MazeSolver
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from model import load_model, predict_image, predict_image_week_9, stitch_image, stitch_image_own
from helper import command_generator

app = Flask(__name__)
CORS(app)

# Lightweight browser UI for visualizing /path
@app.route('/', methods=['GET'])
def ui():
    html = """
<!doctype html>
<meta charset=\\"utf-8\\">
<title>MDP Path Viewer</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 16px; }
  #row { display: flex; gap: 16px; flex-wrap: wrap; }
  textarea { width: 420px; height: 220px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  canvas { border: 1px solid #999; image-rendering: pixelated; }
  pre { background: #f6f8fa; padding: 8px; max-height: 220px; overflow:auto; }
  button { padding: 6px 12px; }
</style>
<div id=\\"row\\">
  <div>
    <h3>Obstacles JSON</h3>
    <textarea id=\\"obs\\">{
  \\"obstacles\\": [
    {\\"x\\": 5,  \\"y\\": 10, \\"id\\": 1, \\"d\\": 2},
    {\\"x\\": 15, \\"y\\": 8,  \\"id\\": 2, \\"d\\": 0},
    {\\"x\\": 4,  \\"y\\": 14, \\"id\\": 3, \\"d\\": 6},
    {\\"x\\": 10, \\"y\\": 15, \\"id\\": 4, \\"d\\": 4},
    {\\"x\\": 12, \\"y\\": 5,  \\"id\\": 5, \\"d\\": 2}
  ],
  \\"robot_x\\": 1, \\"robot_y\\": 1, \\"robot_dir\\": 0,
  \\"retrying\\": false
}</textarea><br/>
    <button id=\\"run\\">Run /path</button>
    <h3>Commands</h3>
    <pre id=\\"cmds\\"></pre>
  </div>
  <div>
    <canvas id=\\"c\\" width=\\"520\\" height=\\"520\\"></canvas>
    <div>20×20 grid (10 cm per cell)</div>
  </div>
</div>
<script>
const WIDTH=20, HEIGHT=20, CELL=24, PAD=20;
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
function drawGrid() {
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.fillStyle = '#fff'; ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle = '#ddd';
  for (let i=0;i<=WIDTH;i++) {
    ctx.beginPath(); ctx.moveTo(PAD+i*CELL, PAD); ctx.lineTo(PAD+i*CELL, PAD+HEIGHT*CELL); ctx.stroke();
  }
  for (let j=0;j<=HEIGHT;j++) {
    ctx.beginPath(); ctx.moveTo(PAD, PAD+j*CELL); ctx.lineTo(PAD+WIDTH*CELL, PAD+j*CELL); ctx.stroke();
  }
}
function toCanvas(x, y) { // grid origin bottom-left -> canvas origin top-left
  const cx = PAD + x*CELL + CELL/2;
  const cy = PAD + (HEIGHT-1 - y)*CELL + CELL/2;
  return [cx, cy];
}
function drawObstacles(obstacles){
  obstacles.forEach(o=>{
    const [cx,cy] = toCanvas(o.x, o.y);
    // draw cell
    ctx.fillStyle = '#d9534f';
    ctx.fillRect(cx-CELL/2, cy-CELL/2, CELL, CELL);
    ctx.strokeStyle = '#a94442';
    ctx.lineWidth = 1;
    ctx.strokeRect(cx-CELL/2, cy-CELL/2, CELL, CELL);
    // id label
    if (typeof o.id !== 'undefined') {
      ctx.fillStyle = '#ffffff';
      ctx.font = '12px ui-monospace, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(o.id), cx, cy);
    }
    // facing indicator: triangle + highlight on the facing side
    if (typeof o.d !== 'undefined' && o.d !== 8) {
      // triangle
      drawHeading(o.x, o.y, o.d, '#6f42c1');
      // side highlight
      const x0 = cx - CELL/2, y0 = cy - CELL/2;
      ctx.strokeStyle = '#6f42c1';
      ctx.lineWidth = 3;
      if (o.d === 0) { // NORTH
        ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0+CELL, y0); ctx.stroke();
      } else if (o.d === 2) { // EAST
        ctx.beginPath(); ctx.moveTo(x0+CELL, y0); ctx.lineTo(x0+CELL, y0+CELL); ctx.stroke();
      } else if (o.d === 4) { // SOUTH
        ctx.beginPath(); ctx.moveTo(x0, y0+CELL); ctx.lineTo(x0+CELL, y0+CELL); ctx.stroke();
      } else if (o.d === 6) { // WEST
        ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0, y0+CELL); ctx.stroke();
      }
      ctx.lineWidth = 1;
    }
  });
}
function angleFor(d){ // 0=N,2=E,4=S,6=W -> radians (triangle canonical points EAST)
  switch(d){
    case 0: return -Math.PI/2; // NORTH
    case 2: return 0;          // EAST
    case 4: return Math.PI/2;  // SOUTH
    case 6: return Math.PI;    // WEST
    default: return 0;
  }
}
function drawHeading(x,y,d,color='rgba(0,0,0,0.65)'){
  const [cx,cy] = toCanvas(x,y);
  const ang = angleFor(d);
  const s = CELL * 0.35; // triangle size
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(ang);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(s, 0);             // tip (points EAST before rotation)
  ctx.lineTo(-s*0.6, -s*0.5);   // back-top
  ctx.lineTo(-s*0.6,  s*0.5);   // back-bottom
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}
function drawPath(path){
  if (!path || path.length===0) return;
  ctx.strokeStyle = '#007bff'; ctx.lineWidth = 2;
  ctx.beginPath();
  let [sx,sy] = toCanvas(path[0].x, path[0].y);
  ctx.moveTo(sx,sy);
  for (let i=1;i<path.length;i++) {
    const [px,py] = toCanvas(path[i].x, path[i].y);
    ctx.lineTo(px,py);
  }
  ctx.stroke();
  // draw headings along the path (every step)
  for (let i=0;i<path.length;i++) {
    const st = path[i];
    if (typeof st.d !== 'undefined') drawHeading(st.x, st.y, st.d);
  }
  // start/end markers
  ctx.fillStyle = '#28a745';
  ctx.beginPath(); ctx.arc(sx,sy,5,0,Math.PI*2); ctx.fill();
  const [ex,ey] = toCanvas(path[path.length-1].x, path[path.length-1].y);
  ctx.fillStyle = '#ff9800';
  ctx.beginPath(); ctx.arc(ex,ey,5,0,Math.PI*2); ctx.fill();
}
async function run(){
  drawGrid();
  const payload = JSON.parse(document.getElementById('obs').value);
  const res = await fetch('/path', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  const json = await res.json();
  drawObstacles(payload.obstacles || []);
  drawPath(json.data?.path || []);
  document.getElementById('cmds').textContent = JSON.stringify(json.data?.commands || [], null, 2);
}
document.getElementById('run').onclick = run;
drawGrid();
</script>
"""
    return Response(html, mimetype="text/html")

# model = load_model()
model = None

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"result": "ok"})


# Incoming direction encoding (team):
#   1=NORTH, 2=EAST, 3=SOUTH, 4=WEST
# MazeSolver encoding (your code/UI):
#   0=NORTH, 2=EAST, 4=SOUTH, 6=WEST
DIR_1234_TO_0246 = {1: 0, 2: 2, 3: 4, 4: 6}

def map_dir_1234_to_0246(d, default=0):
    """
    Accepts:
      - team format: 1/2/3/4 -> map to 0/2/4/6
      - already-correct: 0/2/4/6 -> keep
    """
    try:
        d = int(d)
    except Exception:
        return default
    if d in (0, 2, 4, 6):
        return d
    return DIR_1234_TO_0246.get(d, default)


@app.route('/path', methods=['POST'])
def path_finding():
    content = request.get_json(silent=True) or {}
    print(content)

    obstacles = content.get('obstacles', [])
    retrying = bool(content.get('retrying', False))

    robot_x = int(content.get('robot_x', 1))
    robot_y = int(content.get('robot_y', 1))
    robot_direction = map_dir_1234_to_0246(content.get('robot_dir', 1))  # default 1(N) -> 0

    maze_solver = MazeSolver(20, 20, robot_x, robot_y, robot_direction, big_turn=None)

    normalized_obstacles = []
    for ob in obstacles:
        x = int(ob.get('x', 0))
        y = int(ob.get('y', 0))
        oid = int(ob.get('id', 0))
        d = map_dir_1234_to_0246(ob.get('d', 1))  # default 1(N)

        maze_solver.add_obstacle(x, y, d, oid)
        normalized_obstacles.append({"x": x, "y": y, "id": oid, "d": d})

    start = time.time()
    optimal_path, distance = maze_solver.get_optimal_order_dp(retrying=retrying)
    print(f"Time taken to find shortest path using A* search: {time.time() - start}s")
    print(f"Distance to travel: {distance} units")

    if not optimal_path:
        return jsonify({
            "data": {"distance": 0, "path": [], "commands": []},
            "error": "No path returned by solver"
        })

    commands = command_generator(optimal_path, normalized_obstacles)

    path_results = [optimal_path[0].get_dict()]
    i = 0
    for command in commands:
        if command.startswith("SNAP") or command.startswith("FIN"):
            continue
        elif command.startswith(("FW", "FS", "BW", "BS")):
            try:
                i += int(command[2:]) // 10
            except Exception:
                pass
        else:
            i += 1

        if 0 <= i < len(optimal_path):
            path_results.append(optimal_path[i].get_dict())
        else:
            break

    return jsonify({
        "data": {
            "distance": distance,
            "path": path_results,
            "commands": commands
        },
        "error": None
    })


@app.route('/image', methods=['POST'])
def image_predict():
    file = request.files['file']
    filename = file.filename
    file.save(os.path.join('uploads', filename))

    constituents = file.filename.split("_")
    obstacle_id = constituents[1]

    image_id = predict_image_week_9(filename, model)

    return jsonify({
        "obstacle_id": obstacle_id,
        "image_id": image_id
    })


@app.route('/stitch', methods=['GET'])
def stitch():
    img = stitch_image()
    img.show()
    img2 = stitch_image_own()
    img2.show()
    return jsonify({"result": "ok"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
