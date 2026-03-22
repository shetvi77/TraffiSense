# NYC Traffic Management System - Data & Simulation Lead

**Role:** Backend/Data Engineer  
**Team Member:** Data & Simulation Lead  
**Primary Tools:** Pandas, Python Threading, NetworkX

---

## 🎯 Your Responsibilities

As the Data & Simulation Lead, you manage the "live heartbeat" of the system:

1. **Process NYC traffic CSV data** using pandas
2. **Implement Python threading** to replay traffic speeds at 5-second intervals (simulate live feed)
3. **Use NetworkX A* routing** to calculate fastest diversion routes when incidents occur

---

## 📁 Project Structure

```
windsurf-project/
├── src/
│   ├── data_loader.py      # Pandas CSV processing
│   ├── simulator.py         # Threading-based live simulation
│   ├── routing.py           # NetworkX A* routing algorithm
│   └── main.py              # Integration & demo
├── data/
│   └── nyc_traffic.csv      # Traffic data (auto-generated if missing)
├── requirements.txt         # Dependencies
└── README.md               # This file
```

---

## 🚀 Quick Start Guide

### Step 1: Activate Your Virtual Environment

Your `.venv` is already created. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in your terminal.

### Step 2: Verify Dependencies

Dependencies are already installed. Verify:

```powershell
pip list | Select-String "pandas|networkx|numpy"
```

Should show:
- pandas 2.2.0
- networkx 3.2.1
- numpy 1.26.3

### Step 3: Run the Complete Demo

```powershell
python src/main.py
```

This demonstrates all three core responsibilities:
- ✅ Pandas CSV loading & cleaning
- ✅ NetworkX graph building & A* routing
- ✅ Threading simulation (5-second intervals)

**To stop:** Press `Ctrl+C`

---

## 📚 Component Details

### 1️⃣ Data Loader (`data_loader.py`)

**Purpose:** Load and process NYC traffic CSV using pandas

**Key Methods:**
```python
from src.data_loader import TrafficDataLoader

loader = TrafficDataLoader("data/nyc_traffic.csv")
loader.load_data()           # Load CSV with pandas
loader.clean_data()          # Remove nulls, validate speeds
segments = loader.get_road_segments()  # Extract unique road segments
```

**CSV Format Expected:**
```csv
segment_id,street_name,from_location,to_location,speed,timestamp,traffic_level
SEG001,Broadway,Times Square,Central Park,25,2024-01-01 08:00:00,moderate
```

**What it does:**
- Loads CSV using `pd.read_csv()`
- Cleans data (removes nulls, validates speed 0-80 mph)
- Converts timestamps to datetime
- Groups by segment_id to extract unique road segments

---

### 2️⃣ Traffic Simulator (`simulator.py`)

**Purpose:** Simulate live traffic feed using Python threading

**Key Methods:**
```python
from src.simulator import TrafficSimulator

simulator = TrafficSimulator(loader, interval=5)  # 5-second intervals

# Register callback to receive updates
def my_callback(data):
    print(f"Speed update: {data['speed']} mph")

simulator.register_callback(my_callback)
simulator.start()   # Starts background thread
simulator.stop()    # Stops simulation
```

**How it works:**
- Runs in separate thread (non-blocking)
- Emits traffic snapshots every 5 seconds
- Calls registered callbacks with: `{segment_id, speed, timestamp, traffic_level}`
- Thread-safe using `threading.Lock()`

**Integration Point:**
This is where you connect to other team members' components (frontend, incident manager, etc.)

---

### 3️⃣ Traffic Router (`routing.py`)

**Purpose:** Calculate fastest routes using NetworkX A* algorithm

**Key Methods:**
```python
from src.routing import TrafficRouter

router = TrafficRouter()
router.build_graph(segments)  # Build NetworkX graph

# Find fastest route using A*
route = router.find_fastest_route("Times Square", "Battery Park")
print(route['total_time'])      # Minutes
print(route['total_distance'])  # Miles
print(route['path'])            # List of nodes

# Simulate incident - block a segment
router.block_segment("SEG001")

# Recalculate diversion route
alt_route = router.find_fastest_route("Times Square", "Battery Park")
```

**How it works:**
- Builds directed graph: nodes = locations, edges = road segments
- Edge weight = travel time (length / speed * 60)
- Uses `nx.astar_path()` for optimal routing
- Can block/unblock segments to simulate incidents
- Automatically finds alternative routes

---

## 🔧 How to Integrate with Team Members

### For Frontend Developer:
```python
# In simulator callback, send data to frontend
def send_to_frontend(traffic_data):
    # Send via WebSocket, REST API, or shared queue
    websocket.send(json.dumps(traffic_data))

simulator.register_callback(send_to_frontend)
```

### For Incident Manager:
```python
# When incident detected, block segment and reroute
def handle_incident(segment_id):
    router.block_segment(segment_id)
    alt_route = router.find_fastest_route(start, end)
    return alt_route  # Send to frontend/alerts
```

### For Database/API Developer:
```python
# Store traffic updates in database
def save_to_db(traffic_data):
    db.insert('traffic_updates', traffic_data)

simulator.register_callback(save_to_db)
```

---

## 🧪 Testing Individual Components

### Test Data Loader Only:
```powershell
python -c "from src.data_loader import TrafficDataLoader; loader = TrafficDataLoader('data/nyc_traffic.csv'); loader.load_data(); loader.clean_data(); print(loader.get_road_segments())"
```

### Test Simulator Only:
```powershell
python -c "from src.data_loader import TrafficDataLoader; from src.simulator import TrafficSimulator; loader = TrafficDataLoader('data/nyc_traffic.csv'); loader.load_data(); sim = TrafficSimulator(loader, 2); sim.register_callback(lambda x: print(x)); sim.start(); import time; time.sleep(10); sim.stop()"
```

### Test Router Only:
```powershell
python -c "from src.data_loader import TrafficDataLoader; from src.routing import TrafficRouter; loader = TrafficDataLoader('data/nyc_traffic.csv'); loader.load_data(); loader.clean_data(); router = TrafficRouter(); router.build_graph(loader.get_road_segments()); print(router.find_fastest_route('Times Square', 'Battery Park'))"
```

---

## 📊 Sample Output

When you run `python src/main.py`, you'll see:

```
============================================================
NYC TRAFFIC MANAGEMENT SYSTEM - DATA & SIMULATION BACKEND
============================================================

[1/5] LOADING NYC TRAFFIC DATA (Pandas)
------------------------------------------------------------
✓ Loaded 10 traffic records from CSV
✓ Data cleaned: 10 records kept, 0 removed
✓ Extracted 10 road segments

[2/5] BUILDING ROAD NETWORK GRAPH (NetworkX)
------------------------------------------------------------
✓ Graph built: 11 nodes, 10 edges

[3/5] TESTING A* ROUTING ALGORITHM
------------------------------------------------------------
✓ Route found: Times Square → Battery Park
  Time: 26.9 min, Distance: 10.7 mi, 10 segments

[4/5] INITIALIZING LIVE TRAFFIC SIMULATOR (Threading)
------------------------------------------------------------
✓ Registered callback: traffic_update_handler

[5/5] STARTING SIMULATION
------------------------------------------------------------
🚦 Simulation started: 10 records, 5s interval
📡 [0/10] Emitted: Segment SEG001, Speed: 25 mph
📡 [1/10] Emitted: Segment SEG002, Speed: 30 mph
...
```

---

## 🎓 Key Concepts to Explain in Presentation

### 1. Pandas Data Processing
- **Why pandas?** Efficient CSV handling, data cleaning, grouping operations
- **Key operations:** `read_csv()`, `dropna()`, `groupby()`, datetime conversion
- **Performance:** Can handle millions of rows efficiently

### 2. Python Threading
- **Why threading?** Simulate real-time data without blocking main program
- **Thread safety:** Using `threading.Lock()` to prevent race conditions
- **Daemon threads:** Background threads that don't prevent program exit
- **Callbacks:** Event-driven architecture for real-time updates

### 3. NetworkX A* Algorithm
- **Why A*?** Optimal pathfinding - guaranteed shortest path
- **Graph structure:** Directed graph with weighted edges (travel time)
- **Dynamic rerouting:** Remove blocked edges, recalculate instantly
- **Real-world application:** Google Maps, Waze use similar algorithms

---

## 🐛 Troubleshooting

### Issue: "No module named 'pandas'"
**Solution:**
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: CSV file not found
**Solution:** The system auto-generates sample data. Or create your own CSV with required columns.

### Issue: Simulation not starting
**Solution:** Check that data is loaded first:
```python
print(loader.get_total_records())  # Should be > 0
```

### Issue: No path found in routing
**Solution:** Graph might be disconnected. Check:
```python
print(router.get_graph_stats())
```

---

## 📝 Next Steps for Your Team Project

1. **Get real NYC traffic data:**
   - NYC Open Data: https://data.cityofnewyork.us/
   - Look for "Real-Time Traffic Speed Data"

2. **Expand the simulation:**
   - Add more realistic traffic patterns (rush hour, accidents)
   - Implement traffic congestion propagation
   - Add weather effects on speed

3. **Integrate with teammates:**
   - Connect simulator to frontend via WebSocket
   - Link routing to incident management system
   - Store historical data in database

4. **Performance optimization:**
   - Use `multiprocessing` for larger datasets
   - Implement caching for frequently requested routes
   - Optimize graph updates (incremental vs. full rebuild)

---

## 📞 Integration Checklist

- [ ] CSV data source confirmed (real or sample)
- [ ] Simulator callback connected to frontend/API
- [ ] Router integrated with incident detection system
- [ ] Thread safety verified for concurrent access
- [ ] Error handling added for production use
- [ ] Logging configured for debugging
- [ ] Performance tested with realistic data volume

---

## 🎉 You're Ready!

You now have a complete backend system demonstrating:
- ✅ **Pandas** for data processing
- ✅ **Threading** for live simulation
- ✅ **NetworkX A* routing** for optimal pathfinding

Run `python src/main.py` to see everything in action!

**Questions?** Check the inline code comments in each module.
