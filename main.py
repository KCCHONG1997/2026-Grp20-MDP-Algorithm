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
<meta charset=\"utf-8\">
<title>MDP Path Viewer</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 16px; }
  #row { display: flex; gap: 16px; flex-wrap: wrap; }
  textarea { width: 420px; height: 220px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  canvas { border: 1px solid #999; image-rendering: pixelated; }
  pre { background: #f6f8fa; padding: 8px; max-height: 220px; overflow:auto; }
  button { padding: 6px 12px; }
</style>
<div id=\"row\">
  <div>
    <h3>Obstacles JSON</h3>
    <textarea id=\"obs\">{
  \"obstacles\": [
    {\"x\": 5,  \"y\": 10, \"id\": 1, \"d\": 2},
    {\"x\": 15, \"y\": 8,  \"id\": 2, \"d\": 0},
    {\"x\": 4,  \"y\": 14, \"id\": 3, \"d\": 6},
    {\"x\": 10, \"y\": 15, \"id\": 4, \"d\": 4},
    {\"x\": 12, \"y\": 5,  \"id\": 5, \"d\": 2}
  ],
  \"robot_x\": 1, \"robot_y\": 1, \"robot_dir\": 0,
  \"retrying\": false
}</textarea><br/>
    <button id=\"run\">Run /path</button>
    <h3>Commands</h3>
    <pre id=\"cmds\"></pre>
  </div>
  <div>
    <canvas id=\"c\" width=\"520\" height=\"520\"></canvas>
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

#model = load_model()
model = None
@app.route('/status', methods=['GET'])
def status():
    """
    This is a health check endpoint to check if the server is running
    :return: a json object with a key "result" and value "ok"
    """
    return jsonify({"result": "ok"})


@app.route('/path', methods=['POST'])
def path_finding():
    """
    This is the main endpoint for the path finding algorithm
    :return: a json object with a key "data" and value a dictionary with keys "distance", "path", and "commands"
    """
    # Get the json data from the request
    content = request.json

    # Get the obstacles, big_turn, retrying, robot_x, robot_y, and robot_direction from the json data
    obstacles = content['obstacles']
    # big_turn = int(content['big_turn'])
    retrying = content['retrying']
    robot_x, robot_y = content['robot_x'], content['robot_y']
    robot_direction = int(content['robot_dir'])

    # Initialize MazeSolver object with robot size of 20x20, bottom left corner of robot at (1,1), facing north, and whether to use a big turn or not.
    maze_solver = MazeSolver(20, 20, robot_x, robot_y, robot_direction, big_turn=None)

    # Add each obstacle into the MazeSolver. Each obstacle is defined by its x,y positions, its direction, and its id
    for ob in obstacles:
        maze_solver.add_obstacle(ob['x'], ob['y'], ob['d'], ob['id'])

    start = time.time()
    # Get shortest path
    optimal_path, distance = maze_solver.get_optimal_order_dp(retrying=retrying)
    print(f"Time taken to find shortest path using A* search: {time.time() - start}s")
    print(f"Distance to travel: {distance} units")
    
    # Based on the shortest path, generate commands for the robot
    commands = command_generator(optimal_path, obstacles)

    # Get the starting location and add it to path_results
    path_results = [optimal_path[0].get_dict()]
    # Process each command individually and append the location the robot should be after executing that command to path_results
    i = 0
    for command in commands:
        if command.startswith("SNAP"):
            continue
        if command.startswith("FIN"):
            continue
        elif command.startswith("FW") or command.startswith("FS"):
            i += int(command[2:]) // 10
        elif command.startswith("BW") or command.startswith("BS"):
            i += int(command[2:]) // 10
        else:
            i += 1
        path_results.append(optimal_path[i].get_dict())
    return jsonify({
        "data": {
            'distance': distance,
            'path': path_results,
            'commands': commands
        },
        "error": None
    })


@app.route('/image', methods=['POST'])
def image_predict():
    """
    This is the main endpoint for the image prediction algorithm
    :return: a json object with a key "result" and value a dictionary with keys "obstacle_id" and "image_id"
    """
    file = request.files['file']
    filename = file.filename
    file.save(os.path.join('uploads', filename))
    # filename format: "<timestamp>_<obstacle_id>_<signal>.jpeg"
    constituents = file.filename.split("_")
    obstacle_id = constituents[1]

    ## Week 8 ## 
    #signal = constituents[2].strip(".jpg")
    #image_id = predict_image(filename, model, signal)

    ## Week 9 ## 
    # We don't need to pass in the signal anymore
    image_id = predict_image_week_9(filename,model)

    # Return the obstacle_id and image_id
    result = {
        "obstacle_id": obstacle_id,
        "image_id": image_id
    }
    return jsonify(result)

@app.route('/stitch', methods=['GET'])
def stitch():
    """
    This is the main endpoint for the stitching command. Stitches the images using two different functions, in effect creating two stitches, just for redundancy purposes
    """
    img = stitch_image()
    img.show()
    img2 = stitch_image_own()
    img2.show()
    return jsonify({"result": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
