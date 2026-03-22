import sys
import time
from data_loader import TrafficDataLoader
from simulator import TrafficSimulator
from routing import TrafficRouter

def traffic_update_handler(data):
    """
    Callback function to handle live traffic updates from simulator.
    This is where you'd integrate with other team members' components.
    """
    print(f"  → Traffic Update: Segment {data['segment_id']}, "
          f"Speed: {data['speed']} mph, Level: {data['traffic_level']}")

def main():
    """
    Main integration point for Data & Simulation Lead role.
    Demonstrates all three core responsibilities:
    1. Pandas CSV processing
    2. Threading simulation (5-second intervals)
    3. NetworkX A* routing
    """
    
    print("=" * 60)
    print("NYC TRAFFIC MANAGEMENT SYSTEM - DATA & SIMULATION BACKEND")
    print("=" * 60)
    
    csv_path = "data/nyc_traffic.csv"
    
    print("\n[1/5] LOADING NYC TRAFFIC DATA (Pandas)")
    print("-" * 60)
    loader = TrafficDataLoader(csv_path)
    
    if loader.load_data() is None:
        print(f"\n⚠ CSV file not found at: {csv_path}")
        print("Creating sample data for demonstration...")
        create_sample_data(csv_path)
        loader.load_data()
    
    loader.clean_data()
    segments = loader.get_road_segments()
    
    print(f"\n[2/5] BUILDING ROAD NETWORK GRAPH (NetworkX)")
    print("-" * 60)
    router = TrafficRouter()
    router.build_graph(segments)
    stats = router.get_graph_stats()
    print(f"Graph Stats: {stats}")
    
    print(f"\n[3/5] TESTING A* ROUTING ALGORITHM")
    print("-" * 60)
    
    nodes = list(router.graph.nodes())
    if len(nodes) >= 2:
        start = nodes[0]
        end = nodes[-1]
        
        print(f"\nFinding fastest route: {start} → {end}")
        route = router.find_fastest_route(start, end)
        
        if route:
            print(f"\n📍 Route Details:")
            for i, detail in enumerate(route['route_details'], 1):
                print(f"  {i}. {detail['name']} ({detail['from']} → {detail['to']})")
                print(f"     Time: {detail['time']:.1f} min, Distance: {detail['distance']:.1f} mi")
        
        print(f"\n🚧 Simulating incident on segment: {route['segments'][0]}")
        router.block_segment(route['segments'][0])
        
        print(f"\nRecalculating diversion route...")
        alt_route = router.find_fastest_route(start, end)
        
        if alt_route:
            time_diff = alt_route['total_time'] - route['total_time']
            print(f"⚠ Diversion adds {time_diff:.1f} minutes to journey")
    
    print(f"\n[4/5] INITIALIZING LIVE TRAFFIC SIMULATOR (Threading)")
    print("-" * 60)
    simulator = TrafficSimulator(loader, interval=5)
    simulator.register_callback(traffic_update_handler)
    
    print(f"\n[5/5] STARTING SIMULATION")
    print("-" * 60)
    print("Simulating live traffic feed at 5-second intervals...")
    print("Press Ctrl+C to stop\n")
    
    simulator.start()
    
    try:
        while simulator.is_running:
            time.sleep(1)
            status = simulator.get_status()
            if status['current_index'] % 5 == 0 and status['current_index'] > 0:
                print(f"\n📊 Progress: {status['progress']}")
    except KeyboardInterrupt:
        print("\n\n⚠ Stopping simulation...")
        simulator.stop()
    
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)

def create_sample_data(csv_path):
    """Create sample NYC traffic data if CSV doesn't exist."""
    import pandas as pd
    import os
    
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    sample_data = {
        'segment_id': ['SEG001', 'SEG002', 'SEG003', 'SEG004', 'SEG005', 
                       'SEG006', 'SEG007', 'SEG008', 'SEG009', 'SEG010'],
        'street_name': ['Broadway', '5th Avenue', 'Park Avenue', 'Madison Ave',
                       'Lexington Ave', '3rd Avenue', '2nd Avenue', '1st Avenue',
                       'York Avenue', 'FDR Drive'],
        'from_location': ['Times Square', 'Central Park', 'Grand Central', 'Empire State',
                         'Union Square', 'Washington Sq', 'Houston St', 'Canal St',
                         'Brooklyn Bridge', 'Wall Street'],
        'to_location': ['Central Park', 'Grand Central', 'Empire State', 'Union Square',
                       'Washington Sq', 'Houston St', 'Canal St', 'Brooklyn Bridge',
                       'Wall Street', 'Battery Park'],
        'speed': [25, 30, 20, 15, 35, 28, 32, 18, 22, 40],
        'timestamp': pd.date_range('2024-01-01 08:00:00', periods=10, freq='5S'),
        'traffic_level': ['moderate', 'light', 'heavy', 'heavy', 'light',
                         'moderate', 'light', 'heavy', 'moderate', 'light']
    }
    
    df = pd.DataFrame(sample_data)
    df.to_csv(csv_path, index=False)
    print(f"✓ Created sample data: {csv_path}")

if __name__ == "__main__":
    main()
