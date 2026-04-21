import random
from collections import namedtuple

Flow = namedtuple("Flow", ["source", "destination", "size", "timestamp"])


class TrafficGenerator:
    def __init__(self, network, intensity="medium", seed=None):
        self.network = network
        self.intensity = intensity
        self.seed = seed
        self.random = random.Random(seed)
        self.flows = []

    def set_seed(self, seed):
        """Reset the traffic RNG so the same seed reproduces the same flows."""
        self.seed = seed
        self.random = random.Random(seed)

    def generate_flows(self, count=None):
        """Generate network traffic flows"""
        if count is None:
            intensity_map = {"low": 5, "medium": 20, "high": 50}
            count = intensity_map.get(self.intensity, 20)

        nodes = list(self.network.graph.nodes())
        self.flows = []

        for i in range(count):
            # Random source and destination
            source = self.random.choice(nodes)
            destination = self.random.choice([n for n in nodes if n != source])

            # Random packet size (in KB)
            size = self.random.randint(1, 1000)

            # Timestamp
            timestamp = i

            flow = Flow(source, destination, size, timestamp)
            self.flows.append(flow)

        return self.flows

    def load_flows(self, records):
        """Load traffic from explicit records or traffic-matrix entries."""
        loaded = []
        timestamp = 0
        for record in records:
            source = record.get("source")
            destination = record.get("destination")
            if source is None or destination is None or source == destination:
                continue

            copies = int(record.get("demand", record.get("count", 1)) or 1)
            packet_size = int(record.get("size", record.get("packet_size", 100)))
            for _ in range(max(1, copies)):
                loaded.append(Flow(source, destination, packet_size, timestamp))
                timestamp += 1

        self.flows = loaded
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
