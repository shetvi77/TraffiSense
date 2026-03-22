import networkx as nx
from typing import Dict, List, Tuple, Optional
import numpy as np

class TrafficRouter:
    """
    Uses NetworkX and A* algorithm to calculate fastest diversion routes.
    Builds a graph from road segments and computes optimal paths when incidents occur.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.road_segments = {}
        self.blocked_segments = set()
        
    def build_graph(self, segments: Dict[str, Dict]):
        """
        Build NetworkX directed graph from road segments.
        Each segment becomes an edge with weight = travel_time (length/speed).
        
        Args:
            segments: {segment_id: {name, from, to, avg_speed, length}}
        """
        self.road_segments = segments
        self.graph.clear()
        
        for seg_id, data in segments.items():
            from_node = data['from']
            to_node = data['to']
            
            travel_time = (data['length'] / data['avg_speed']) * 60 if data['avg_speed'] > 0 else 999
            
            self.graph.add_edge(
                from_node,
                to_node,
                segment_id=seg_id,
                weight=travel_time,
                length=data['length'],
                speed=data['avg_speed'],
                name=data['name']
            )
        
        print(f"✓ Graph built: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")
    
    def block_segment(self, segment_id: str):
        """
        Block a road segment due to incident.
        Removes the edge from the graph to force rerouting.
        """
        if segment_id not in self.road_segments:
            print(f"⚠ Segment {segment_id} not found")
            return
        
        seg_data = self.road_segments[segment_id]
        from_node = seg_data['from']
        to_node = seg_data['to']
        
        if self.graph.has_edge(from_node, to_node):
            self.graph.remove_edge(from_node, to_node)
            self.blocked_segments.add(segment_id)
            print(f"🚧 Blocked segment: {segment_id} ({seg_data['name']})")
        else:
            print(f"⚠ Edge {from_node} -> {to_node} not in graph")
    
    def unblock_segment(self, segment_id: str):
        """
        Unblock a previously blocked segment.
        Restores the edge to the graph.
        """
        if segment_id not in self.blocked_segments:
            print(f"⚠ Segment {segment_id} was not blocked")
            return
        
        seg_data = self.road_segments[segment_id]
        from_node = seg_data['from']
        to_node = seg_data['to']
        travel_time = (seg_data['length'] / seg_data['avg_speed']) * 60
        
        self.graph.add_edge(
            from_node,
            to_node,
            segment_id=segment_id,
            weight=travel_time,
            length=seg_data['length'],
            speed=seg_data['avg_speed'],
            name=seg_data['name']
        )
        
        self.blocked_segments.remove(segment_id)
        print(f"✓ Unblocked segment: {segment_id}")
    
    def find_fastest_route(self, start: str, end: str) -> Optional[Dict]:
        """
        Calculate fastest route using A* algorithm (NetworkX implementation).
        
        Args:
            start: Starting location/node
            end: Destination location/node
            
        Returns:
            {
                'path': [node1, node2, ...],
                'segments': [seg_id1, seg_id2, ...],
                'total_time': minutes,
                'total_distance': miles,
                'route_details': [{segment_id, name, time, distance}, ...]
            }
        """
        if start not in self.graph.nodes:
            print(f"✗ Start node '{start}' not in graph")
            return None
        
        if end not in self.graph.nodes:
            print(f"✗ End node '{end}' not in graph")
            return None
        
        try:
            path = nx.astar_path(self.graph, start, end, weight='weight')
            
            total_time = 0
            total_distance = 0
            segments = []
            route_details = []
            
            for i in range(len(path) - 1):
                from_node = path[i]
                to_node = path[i + 1]
                edge_data = self.graph[from_node][to_node]
                
                segments.append(edge_data['segment_id'])
                total_time += edge_data['weight']
                total_distance += edge_data['length']
                
                route_details.append({
                    'segment_id': edge_data['segment_id'],
                    'name': edge_data['name'],
                    'from': from_node,
                    'to': to_node,
                    'time': round(edge_data['weight'], 2),
                    'distance': round(edge_data['length'], 2),
                    'speed': edge_data['speed']
                })
            
            result = {
                'path': path,
                'segments': segments,
                'total_time': round(total_time, 2),
                'total_distance': round(total_distance, 2),
                'route_details': route_details
            }
            
            print(f"✓ Route found: {start} → {end}")
            print(f"  Time: {result['total_time']:.1f} min, "
                  f"Distance: {result['total_distance']:.1f} mi, "
                  f"{len(segments)} segments")
            
            return result
            
        except nx.NetworkXNoPath:
            print(f"✗ No path found from {start} to {end}")
            return None
        except Exception as e:
            print(f"✗ Routing error: {e}")
            return None
    
    def find_alternative_routes(self, start: str, end: str, n_routes: int = 3) -> List[Dict]:
        """
        Find multiple alternative routes by temporarily blocking segments.
        
        Args:
            start: Starting location
            end: Destination
            n_routes: Number of alternative routes to find
            
        Returns:
            List of route dicts (same format as find_fastest_route)
        """
        routes = []
        temp_blocked = []
        
        for i in range(n_routes):
            route = self.find_fastest_route(start, end)
            
            if route is None:
                break
            
            routes.append(route)
            
            if i < n_routes - 1 and len(route['segments']) > 0:
                seg_to_block = route['segments'][len(route['segments']) // 2]
                self.block_segment(seg_to_block)
                temp_blocked.append(seg_to_block)
        
        for seg_id in temp_blocked:
            self.unblock_segment(seg_id)
        
        print(f"✓ Found {len(routes)} alternative routes")
        return routes
    
    def get_graph_stats(self) -> Dict:
        """Get statistics about the road network graph."""
        return {
            'nodes': self.graph.number_of_nodes(),
            'edges': self.graph.number_of_edges(),
            'blocked_segments': len(self.blocked_segments),
            'is_connected': nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
        }
