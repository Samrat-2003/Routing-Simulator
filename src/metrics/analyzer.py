import time
import pandas as pd
from collections import defaultdict

class PerformanceMetrics:
    def __init__(self, network):
        self.network = network
        self.metrics_history = []
        
    def calculate_latency(self, path):
        """Calculate total latency for a path"""
        if not path or len(path) < 2:
            return 0
        
        total_latency = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            if self.network.graph.has_edge(u, v):
                total_latency += self.network.graph[u][v].get('weight', 1)
        return total_latency
    
    def calculate_throughput(self, path, packet_size):
        """Calculate throughput for a path (simplified model)"""
        latency = self.calculate_latency(path)
        if latency == 0:
            return 0
        # Simplified: throughput = packet_size / latency (KB per unit time)
        return packet_size / latency if latency > 0 else 0
    
    def calculate_hop_count(self, path):
        """Calculate number of hops in a path"""
        return len(path) - 1 if path else 0
    
    def calculate_packet_delivery_ratio(self, successful_paths, total_flows):
        """Calculate packet delivery ratio"""
        if total_flows == 0:
            return 0
        return successful_paths / total_flows
    
    def calculate_load_distribution(self, paths):
        """Calculate how load is distributed across network edges"""
        edge_usage = defaultdict(int)
        
        for path in paths:
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                edge_usage[(min(u,v), max(u,v))] += 1  # Undirected graph
        
        return dict(edge_usage)
    
    def analyze_routing_performance(self, algorithm, traffic_flows):
        """Analyze performance of a routing algorithm with given traffic"""
        start_time = time.time()
        
        paths = []
        latencies = []
        throughputs = []
        hop_counts = []
        successful_routes = 0
        
        for flow in traffic_flows:
            path = algorithm.route(flow.source, flow.destination)
            if path:
                paths.append(path)
                latency = self.calculate_latency(path)
                throughput = self.calculate_throughput(path, flow.size)
                hop_count = self.calculate_hop_count(path)
                
                latencies.append(latency)
                throughputs.append(throughput)
                hop_counts.append(hop_count)
                successful_routes += 1
            else:
                # Failed to find path
                latencies.append(None)
                throughputs.append(None)
                hop_counts.append(None)
        
        execution_time = time.time() - start_time
        
        # Calculate aggregate metrics
        avg_latency = sum([l for l in latencies if l is not None]) / len([l for l in latencies if l is not None]) if any(l is not None for l in latencies) else 0
        avg_throughput = sum([t for t in throughputs if t is not None]) / len([t for t in throughputs if t is not None]) if any(t is not None for t in throughputs) else 0
        avg_hop_count = sum([h for h in hop_counts if h is not None]) / len([h for h in hop_counts if h is not None]) if any(h is not None for h in hop_counts) else 0
        pdr = self.calculate_packet_delivery_ratio(successful_routes, len(traffic_flows))
        
        metrics = {
            "algorithm": algorithm.__class__.__name__,
            "execution_time": execution_time,
            "successful_routes": successful_routes,
            "total_flows": len(traffic_flows),
            "packet_delivery_ratio": pdr,
            "average_latency": avg_latency,
            "average_throughput": avg_throughput,
            "average_hop_count": avg_hop_count,
            "paths": paths,
            "latencies": latencies,
            "throughputs": throughputs,
            "hop_counts": hop_counts
        }
        
        self.metrics_history.append(metrics)
        return metrics
    
    def compare_algorithms(self, algorithms, traffic_flows):
        """Compare multiple algorithms"""
        comparison_results = {}
        
        for name, algorithm in algorithms.items():
            metrics = self.analyze_routing_performance(algorithm, traffic_flows)
            comparison_results[name] = metrics
        
        return comparison_results
    
    def get_metrics_dataframe(self):
        """Return metrics history as DataFrame"""
        return pd.DataFrame(self.metrics_history)

# Example usage
if __name__ == "__main__":
    from src.network.topology import NetworkTopology
    from src.algorithms.routing import DijkstraRouting
    from src.traffic.generator import TrafficGenerator
    
    # Setup
    net = NetworkTopology()
    net.create_mesh_topology(5)
    
    dijkstra = DijkstraRouting(net)
    traffic = TrafficGenerator(net, "medium")
    flows = traffic.generate_flows(10)
    
    # Analyze performance
    metrics = PerformanceMetrics(net)
    results = metrics.analyze_routing_performance(dijkstra, flows)
    
    print("Performance Metrics:")
    for key, value in results.items():
        if key not in ['paths', 'latencies', 'throughputs', 'hop_counts']:
            print(f"  {key}: {value}")
