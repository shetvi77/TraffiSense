import threading
import time
from typing import Callable, Dict, Optional
from data_loader import TrafficDataLoader

class TrafficSimulator:
    """
    Simulates live traffic feed using Python threading.
    Replays CSV data at 5-second intervals to mimic real-time updates.
    """
    
    def __init__(self, data_loader: TrafficDataLoader, interval: int = 5):
        self.data_loader = data_loader
        self.interval = interval
        self.current_index = 0
        self.is_running = False
        self.thread = None
        self.callbacks = []
        self.lock = threading.Lock()
        
    def register_callback(self, callback: Callable[[Dict], None]):
        """
        Register a callback function to receive traffic updates.
        Callback receives: {segment_id, speed, timestamp, traffic_level}
        """
        with self.lock:
            self.callbacks.append(callback)
            print(f"✓ Registered callback: {callback.__name__}")
    
    def _emit_traffic_update(self, data: Dict):
        """Emit traffic data to all registered callbacks."""
        with self.lock:
            for callback in self.callbacks:
                try:
                    callback(data)
                except Exception as e:
                    print(f"✗ Callback error: {e}")
    
    def _simulation_loop(self):
        """
        Main simulation loop running in separate thread.
        Emits traffic data every 5 seconds.
        """
        total_records = self.data_loader.get_total_records()
        print(f"🚦 Simulation started: {total_records} records, {self.interval}s interval")
        
        while self.is_running and self.current_index < total_records:
            snapshot = self.data_loader.get_traffic_snapshot(self.current_index)
            
            if snapshot:
                self._emit_traffic_update(snapshot)
                print(f"📡 [{self.current_index}/{total_records}] Emitted: "
                      f"Segment {snapshot['segment_id']}, Speed: {snapshot['speed']} mph")
            
            self.current_index += 1
            time.sleep(self.interval)
        
        self.is_running = False
        print("🛑 Simulation completed")
    
    def start(self):
        """Start the traffic simulation in a separate thread."""
        if self.is_running:
            print("⚠ Simulation already running")
            return
        
        if self.data_loader.get_total_records() == 0:
            print("✗ No traffic data available. Load data first.")
            return
        
        self.is_running = True
        self.current_index = 0
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()
        print("✓ Simulation thread started")
    
    def stop(self):
        """Stop the traffic simulation."""
        if not self.is_running:
            print("⚠ Simulation not running")
            return
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=self.interval + 1)
        print("✓ Simulation stopped")
    
    def get_status(self) -> Dict:
        """Get current simulation status."""
        return {
            'running': self.is_running,
            'current_index': self.current_index,
            'total_records': self.data_loader.get_total_records(),
            'progress': f"{self.current_index}/{self.data_loader.get_total_records()}"
        }
    
    def reset(self):
        """Reset simulation to beginning."""
        was_running = self.is_running
        if was_running:
            self.stop()
        
        self.current_index = 0
        print("✓ Simulation reset to start")
        
        if was_running:
            self.start()
