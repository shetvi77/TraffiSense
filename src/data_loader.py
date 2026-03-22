import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class TrafficDataLoader:
    """
    Loads and processes NYC traffic CSV data using pandas.
    Handles data cleaning, validation, and preparation for simulation.
    """
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.traffic_data = None
        self.road_segments = {}
        
    def load_data(self) -> pd.DataFrame:
        """
        Load NYC traffic CSV data using pandas.
        Expected columns: segment_id, street_name, from_location, to_location, 
                         speed, timestamp, traffic_level
        """
        try:
            self.traffic_data = pd.read_csv(self.csv_path)
            print(f"✓ Loaded {len(self.traffic_data)} traffic records from CSV")
            return self.traffic_data
        except FileNotFoundError:
            print(f"✗ Error: CSV file not found at {self.csv_path}")
            return None
        except Exception as e:
            print(f"✗ Error loading CSV: {e}")
            return None
    
    def clean_data(self) -> pd.DataFrame:
        """
        Clean and validate traffic data:
        - Remove null values
        - Validate speed ranges (0-80 mph for NYC)
        - Convert timestamps to datetime
        """
        if self.traffic_data is None:
            print("✗ No data loaded. Call load_data() first.")
            return None
        
        initial_count = len(self.traffic_data)
        
        self.traffic_data = self.traffic_data.dropna()
        
        self.traffic_data = self.traffic_data[
            (self.traffic_data['speed'] >= 0) & 
            (self.traffic_data['speed'] <= 80)
        ]
        
        if 'timestamp' in self.traffic_data.columns:
            self.traffic_data['timestamp'] = pd.to_datetime(
                self.traffic_data['timestamp'], 
                errors='coerce'
            )
        
        cleaned_count = len(self.traffic_data)
        removed = initial_count - cleaned_count
        
        print(f"✓ Data cleaned: {cleaned_count} records kept, {removed} removed")
        return self.traffic_data
    
    def get_road_segments(self) -> Dict[str, Dict]:
        """
        Extract unique road segments for NetworkX graph construction.
        Returns dict: {segment_id: {name, from, to, avg_speed, length}}
        """
        if self.traffic_data is None or len(self.traffic_data) == 0:
            print("✗ No data available")
            return {}
        
        segments = self.traffic_data.groupby('segment_id').agg({
            'street_name': 'first',
            'from_location': 'first',
            'to_location': 'first',
            'speed': 'mean'
        }).reset_index()
        
        for _, row in segments.iterrows():
            seg_id = row['segment_id']
            self.road_segments[seg_id] = {
                'name': row['street_name'],
                'from': row['from_location'],
                'to': row['to_location'],
                'avg_speed': round(row['speed'], 2),
                'length': np.random.uniform(0.1, 2.0)
            }
        
        print(f"✓ Extracted {len(self.road_segments)} road segments")
        return self.road_segments
    
    def get_traffic_snapshot(self, index: int) -> Dict:
        """
        Get a single traffic snapshot by index for simulation replay.
        Used by the threading simulator to emit data every 5 seconds.
        """
        if self.traffic_data is None or index >= len(self.traffic_data):
            return None
        
        row = self.traffic_data.iloc[index]
        return {
            'segment_id': row['segment_id'],
            'speed': row['speed'],
            'timestamp': row.get('timestamp', None),
            'traffic_level': row.get('traffic_level', 'normal')
        }
    
    def get_total_records(self) -> int:
        """Return total number of traffic records available."""
        return len(self.traffic_data) if self.traffic_data is not None else 0
