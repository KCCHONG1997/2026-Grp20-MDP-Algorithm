# MDP Algorithm Architecture

## Codebase Structure

```
CZ3004-SC2079-MDP-Algorithm/
├── main.py                 # Flask API server (entry point)
├── consts.py               # Global constants and configurations
├── helper.py               # Command generation utilities
├── model.py                # YOLO image recognition inference
├── hubconf.py              # PyTorch Hub config for YOLO
│
├── algo/
│   └── algo.py             # Core pathfinding algorithm (A* + TSP)
│
├── entities/
│   ├── Entity.py           # Grid, Obstacle, CellState classes
│   ├── Robot.py            # Robot state representation
│   └── __init__.py
│
├── utils/                  # YOLOv5 inference utilities
│   ├── general.py
│   ├── augmentations.py
│   ├── torch_utils.py
│   └── ...
│
├── models/                 # YOLO model architecture definitions
├── images/                 # Static images for documentation
├── uploads/                # Uploaded images from Raspberry Pi (runtime)
├── runs/                   # YOLO inference results (runtime)
├── own_results/            # Annotated images (runtime)
│
├── Week_8.pt               # Pre-trained YOLO model (Task 1)
├── Week_9.pt               # Pre-trained YOLO model (Task 2)
└── requirements.txt
```

## Component Responsibilities

| Component | File(s) | Purpose |
|-----------|---------|---------|
| **API Server** | `main.py` | Flask server exposing REST endpoints |
| **Pathfinding** | `algo/algo.py` | A* search + TSP dynamic programming |
| **Entities** | `entities/` | Data models for Robot, Grid, Obstacles |
| **Command Gen** | `helper.py` | Convert path states → robot commands |
| **Image Recognition** | `model.py` | YOLO inference for symbol detection |
| **Constants** | `consts.py` | Grid size, costs, direction enums |

---

## System Flow

### Overall Architecture

```
┌─────────────────┐      HTTP/JSON       ┌─────────────────┐
│  Raspberry Pi   │ ◄──────────────────► │   Algorithm     │
│  (Robot)        │                      │   Server        │
└─────────────────┘                      │   (Flask)       │
                                         └────────┬────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    │                             │                             │
                    ▼                             ▼                             ▼
            ┌───────────────┐           ┌─────────────────┐           ┌─────────────────┐
            │  /path        │           │  /image         │           │  /stitch        │
            │  Pathfinding  │           │  Recognition    │           │  Image Stitch   │
            └───────────────┘           └─────────────────┘           └─────────────────┘
```

### Sequence of Operations

```
1. STARTUP
   └── Raspberry Pi boots → connects to Algorithm Server

2. PATH PLANNING (called once at start)
   └── Pi sends obstacle positions → Server returns optimal path + commands

3. EXECUTION LOOP (repeated for each obstacle)
   ├── Robot executes movement commands (FW, BW, FR, FL, BR, BL)
   ├── Robot reaches viewing position
   ├── Robot sends SNAP command
   ├── Pi captures image → sends to /image endpoint
   ├── Server runs YOLO inference → returns detected symbol ID
   └── Robot continues to next obstacle

4. COMPLETION
   └── Pi calls /stitch → Server stitches all images into summary
```

---

## API Endpoints

### 1. POST `/path` - Path Planning

**When called:** Once at the start, after obstacles are placed on the arena.

**Request:**
```json
{
    "obstacles": [
        {"x": 5, "y": 10, "id": 1, "d": 2},
        {"x": 15, "y": 8, "id": 2, "d": 0}
    ],
    "robot_x": 1,
    "robot_y": 1,
    "robot_dir": 0,
    "retrying": false
}
```

| Field | Description |
|-------|-------------|
| `x`, `y` | Obstacle position (0-19) |
| `id` | Unique obstacle identifier |
| `d` | Direction obstacle faces: 0=North, 2=East, 4=South, 6=West |
| `robot_x/y` | Robot starting position |
| `robot_dir` | Robot starting direction |
| `retrying` | If true, uses farther viewing positions |

**Response:**
```json
{
    "data": {
        "distance": 46.0,
        "path": [
            {"x": 1, "y": 1, "d": 0, "s": -1},
            {"x": 5, "y": 3, "d": 2, "s": 1}
        ],
        "commands": ["FR00", "FW30", "SNAP1_C", "FL00", "FW20", "SNAP2_L", "FIN"]
    },
    "error": null
}
```

**Command Format:**
| Command | Meaning |
|---------|---------|
| `FW10` | Forward 10cm |
| `BW20` | Backward 20cm |
| `FR00` | Forward Right turn |
| `FL00` | Forward Left turn |
| `BR00` | Backward Right turn |
| `BL00` | Backward Left turn |
| `SNAP1_C` | Take photo of obstacle 1 (Center aligned) |
| `SNAP2_L` | Take photo of obstacle 2 (Left aligned) |
| `FIN` | Finished |

---

### 2. POST `/image` - Image Recognition

**When called:** After robot reaches viewing position and captures image.

**Request:** Multipart form with image file
```python
# From Raspberry Pi
response = requests.post(url, files={"file": (filename, image_data)})
```

Filename format: `<timestamp>_<obstacle_id>_<signal>.jpg`

**Response:**
```json
{
    "obstacle_id": "1",
    "image_id": "20"
}
```

| image_id | Symbol |
|----------|--------|
| 11-19 | Numbers 1-9 |
| 20-35 | Letters A-H, S-Z |
| 36-39 | Arrows (Up, Down, Right, Left) |
| 40 | Stop |
| NA | Not detected |

---

### 3. GET `/stitch` - Stitch Images

**When called:** After all obstacles have been photographed.

**Response:**
```json
{"result": "ok"}
```

Creates stitched summary images in `runs/` and `own_results/` folders.

---

### 4. GET `/status` - Health Check

**Response:**
```json
{"result": "ok"}
```

---

## Internal Flow Details

### Path Planning Flow (`/path`)

```
Request arrives
    │
    ▼
┌─────────────────────────────────┐
│ MazeSolver.__init__()           │
│ - Create Grid(20, 20)           │
│ - Create Robot at start pos     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ add_obstacle() for each         │
│ - Add to grid.obstacles list    │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ get_optimal_order_dp()          │
│ 1. Get viewing positions for    │
│    each obstacle                │
│ 2. Run A* between all pairs     │
│ 3. Build cost matrix            │
│ 4. Solve TSP for optimal order  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ command_generator()             │
│ - Convert path states to        │
│   robot commands                │
│ - Compress consecutive moves    │
└─────────────────────────────────┘
    │
    ▼
Return JSON response
```

### Image Recognition Flow (`/image`)

```
Image file arrives
    │
    ▼
┌─────────────────────────────────┐
│ Save to uploads/ folder         │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ predict_image_week_9()          │
│ 1. Load image with PIL          │
│ 2. Run YOLO model inference     │
│ 3. Filter by confidence > 0.5   │
│ 4. Select largest bounding box  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ draw_own_bbox()                 │
│ - Save annotated image          │
└─────────────────────────────────┘
    │
    ▼
Return {obstacle_id, image_id}
```

---

## Calling the API

### From Raspberry Pi (Python)

```python
import requests

SERVER_URL = "http://<laptop-ip>:5000"

# 1. Get path
obstacles = [
    {"x": 5, "y": 10, "id": 1, "d": 2},
    {"x": 15, "y": 8, "id": 2, "d": 0}
]
response = requests.post(f"{SERVER_URL}/path", json={
    "obstacles": obstacles,
    "robot_x": 1,
    "robot_y": 1,
    "robot_dir": 0,
    "retrying": False
})
commands = response.json()["data"]["commands"]

# 2. Execute commands and capture images
for cmd in commands:
    if cmd.startswith("SNAP"):
        # Capture image
        image_data = camera.capture()
        filename = f"{time.time()}_{obstacle_id}.jpg"
        
        # Send for recognition
        response = requests.post(
            f"{SERVER_URL}/image",
            files={"file": (filename, image_data)}
        )
        result = response.json()
        print(f"Detected: {result['image_id']}")
    elif cmd == "FIN":
        break
    else:
        robot.execute(cmd)

# 3. Stitch final images
requests.get(f"{SERVER_URL}/stitch")
```

### Testing with cURL

```bash
# Health check
curl http://localhost:5000/status

# Path planning
curl -X POST http://localhost:5000/path \
  -H "Content-Type: application/json" \
  -d '{"obstacles":[{"x":5,"y":10,"id":1,"d":2}],"robot_x":1,"robot_y":1,"robot_dir":0,"retrying":false}'

# Image recognition
curl -X POST http://localhost:5000/image \
  -F "file=@test_image.jpg"

# Stitch images
curl http://localhost:5000/stitch
```

---

## Starting the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

Server runs on `http://0.0.0.0:5000` (accessible from any device on the network).
