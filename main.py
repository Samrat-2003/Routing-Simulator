"""
Network Routing Simulation Project
Main execution script
"""

import argparse
import json
from src.network.topology import NetworkTopology
from src.algorithms.routing import create_routing_algorithm
from src.traffic.generator import TrafficGenerator
from src.metrics.analyzer import PerformanceMetrics

def load_config(config_path="config/config.json"):
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)

def run_single_simulation(config, topology_type, algorithm_name, traffic_intensity):
    """Run a single simulation scenario"""
    print(f"Running simulation: {topology_type} topology, {algorithm_name} algorithm, {traffic_intensity} traffic")
    
    # Create network
    network = NetworkTopology()
    node_count = config['network']['node_count']
    
    if topology_type == "mesh":
        network.create_mesh_topology(node_count)
    elif topology_type == "random":
        network.create_random_topology(node_count, config['network']['edge_probability'])
    elif topology_type == "ring":
        network.create_ring_topology(node_count)
    elif topology_type == "star":
        network.create_star_topology(node_count)
    
    print(f"Network created with {network.graph.number_of_nodes()} nodes and {network.graph.number_of_edges()} edges")
    
    # Generate traffic
    traffic_gen = TrafficGenerator(network, traffic_intensity)
    flow_count = config['traffic'][f"{traffic_intensity}_intensity"]
    flows = traffic_gen.generate_flows(flow_count)
    print(f"Generated {len(flows)} traffic flows")
    
    # Create routing algorithm
    algorithm = create_routing_algorithm(algorithm_name, network)
    
    # Analyze performance
    metrics_analyzer = PerformanceMetrics(network)
    results = metrics_analyzer.analyze_routing_performance(algorithm, flows)
    
    # Print results
    print("\n=== PERFORMANCE RESULTS ===")
    print(f"Algorithm: {results['algorithm']}")
    print(f"Execution Time: {results['execution_time']:.4f} seconds")
    print(f"Successful Routes: {results['successful_routes']}/{results['total_flows']}")
    print(f"Packet Delivery Ratio: {results['packet_delivery_ratio']:.2%}")
    print(f"Average Latency: {results['average_latency']:.2f} units")
    print(f"Average Throughput: {results['average_throughput']:.2f} KB/unit")
    print(f"Average Hop Count: {results['average_hop_count']:.2f}")
    
    return results

def run_comparison(config):
    """Run comparison of all algorithms"""
    print("Running comparison of all algorithms...")
    
    # Create network
    network = NetworkTopology()
    network.create_mesh_topology(config['network']['node_count'])
    
    # Generate traffic
    traffic_gen = TrafficGenerator(network, "medium")
    flows = traffic_gen.generate_flows(20)
    
    # Create all algorithms
    algorithms = {
        'Dijkstra': create_routing_algorithm('dijkstra', network),
        'Bellman-Ford': create_routing_algorithm('bellman_ford', network),
        'ACO': create_routing_algorithm('aco', network),
        'GA': create_routing_algorithm('ga', network)
    }
    
    # Analyze performance
    metrics_analyzer = PerformanceMetrics(network)
    comparison = metrics_analyzer.compare_algorithms(algorithms, flows)
    
    # Print comparison results
    print("\n=== ALGORITHM COMPARISON ===")
    print(f"{'Algorithm':<15} {'Time(s)':<10} {'PDR':<8} {'Latency':<10} {'Throughput':<12} {'Hops':<8}")
    print("-" * 65)
    
    for alg_name, metrics in comparison.items():
        print(f"{alg_name:<15} {metrics['execution_time']:<10.4f} {metrics['packet_delivery_ratio']:<8.2%} "
              f"{metrics['average_latency']:<10.2f} {metrics['average_throughput']:<12.2f} {metrics['average_hop_count']:<8.2f}")
    
    return comparison

def main():
    parser = argparse.ArgumentParser(description="Network Routing Simulation")
    parser.add_argument('--mode', choices=['single', 'compare', 'dashboard'], default='single',
                        help='Execution mode: single simulation, comparison, or dashboard')
    parser.add_argument('--topology', choices=['mesh', 'random', 'ring', 'star'], default='mesh',
                        help='Network topology type')
    parser.add_argument('--algorithm', choices=['dijkstra', 'bellman_ford', 'aco', 'ga'], default='dijkstra',
                        help='Routing algorithm')
    parser.add_argument('--traffic', choices=['low', 'medium', 'high'], default='medium',
                        help='Traffic intensity')
    
    args = parser.parse_args()
    config = load_config()
    
    if args.mode == 'single':
        run_single_simulation(config, args.topology, args.algorithm, args.traffic)
    elif args.mode == 'compare':
        run_comparison(config)
    elif args.mode == 'dashboard':
        from src.dashboard.app import run_dashboard
        print("Starting dashboard server at http://localhost:8050")
        run_dashboard()

if __name__ == "__main__":
    main()
