import random
import pandas as pd
from collections import namedtuple

Flow = namedtuple('Flow', ['source', 'destination', 'size', 'timestamp'])

class TrafficGenerator:
    def __init__(self, network, intensity="medium"):
        self.network = network
        self.intensity = intensity
        self.flows = []
        
    def generate_flows(self, count=None):
        """Generate network traffic flows"""
        if count is None:
            intensity_map = {"low": 5, "medium": 20, "high": 50}
            count = intensity_map.get(self.intensity, 20)
        
        nodes = list(self.network.graph.nodes())
        self.flows = []
        
        for i in range(count):
            # Random source and destination
            source = random.choice(nodes)
            destination = random.choice([n for n in nodes if n != source])
            
            # Random packet size (in KB)
            size = random.randint(1, 1000)
            
            # Timestamp
            timestamp = i
            
            flow = Flow(source, destination, size, timestamp)
            self.flows.append(flow)
        
        return self.flows
    
    def get_flow_stats(self):
        """Get statistics about generated flows"""
        if not self.flows:
            return {}
        
        sources = [flow.source for flow in self.flows]
        destinations = [flow.destination for flow in self.flows]
        sizes = [flow.size for flow in self.flows]
        
        stats = {
            "total_flows": len(self.flows),
            "unique_sources": len(set(sources)),
            "unique_destinations": len(set(destinations)),
            "avg_packet_size": sum(sizes) / len(sizes),
            "total_data_volume": sum(sizes)
        }
        
        return stats
    
    def get_traffic_matrix(self):
        """Get traffic matrix showing flow counts between node pairs"""
        matrix = {}
        for flow in self.flows:
            pair = (flow.source, flow.destination)
            if pair not in matrix:
                matrix[pair] = 0
            matrix[pair] += 1
        return matrix

# Example usage
if __name__ == "__main__":
    from src.network.topology import NetworkTopology
    
    net = NetworkTopology()
    net.create_mesh_topology(5)
    
    traffic = TrafficGenerator(net, "medium")
    flows = traffic.generate_flows(10)
    
    print("Generated flows:")
    for flow in flows[:5]:  # Show first 5 flows
        print(f"  {flow}")
    
    print("\nTraffic stats:", traffic.get_flow_stats())
