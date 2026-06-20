"""
Network Routing Simulation Project
Main execution script with interactive CLI
"""

import argparse
import csv
import json
from pathlib import Path

from src.network.topology import NetworkTopology
from src.algorithms.routing import create_routing_algorithm
from src.traffic.generator import TrafficGenerator
from src.metrics.analyzer import PerformanceMetrics


def load_config(config_path="config/config.json"):
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)


def get_int_input(prompt, min_val, max_val):
    """Prompt user for an integer within a range, re-asking on invalid input."""
    while True:
        try:
            value = int(input(prompt))
            if min_val <= value <= max_val:
                return value
            print(f"  Please enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("  Invalid input. Please enter a whole number.")


def get_float_input(prompt, min_val, max_val):
    """Prompt user for a float within a range, re-asking on invalid input."""
    while True:
        try:
            value = float(input(prompt))
            if min_val <= value <= max_val:
                return value
            print(f"  Please enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("  Invalid input. Please enter a decimal number.")


def get_network_config():
    """Interactively collect network configuration from user."""
    print("\n=== NETWORK CONFIGURATION ===")
    topology_type = get_topology_choice()
    node_count = get_int_input("Enter number of nodes (10-200): ", 10, 200)
    edge_prob = None
    if topology_type == "random":
        edge_prob = get_float_input("Enter edge probability (0.1-0.8): ", 0.1, 0.8)
    bandwidth_min = get_int_input("Enter minimum link bandwidth (1-1000): ", 1, 1000)
    bandwidth_max = get_int_input("Enter maximum link bandwidth (1-1000): ", 1, 1000)
    if bandwidth_min > bandwidth_max:
        bandwidth_min, bandwidth_max = bandwidth_max, bandwidth_min
    return topology_type, node_count, edge_prob, (bandwidth_min, bandwidth_max)


def get_topology_choice():
    """Interactively collect topology selection from user."""
    print("\nAvailable topology types:")
    print("  1. Random")
    print("  2. Mesh")
    print("  3. Ring")
    print("  4. Star")
    choice = get_int_input("Select topology (1-4): ", 1, 4)

    topology_map = {
        1: "random",
        2: "mesh",
        3: "ring",
        4: "star",
    }
    return topology_map[choice]


def get_algorithm_choice():
    """Interactively collect algorithm selection from user."""
    print("\nAvailable routing algorithms:")
    print("  1. Dijkstra (shortest path)")
    print("  2. Bellman-Ford (distributed shortest path)")
    print("  3. PCA-MR (proposed congestion-aware routing)")
    print("  4. ACO (Ant Colony Optimization)")
    print("  5. GA (Genetic Algorithm)")
    print("  6. ALL (compare all algorithms)")
    choice = get_int_input("Select algorithm (1-6): ", 1, 6)

    algo_map = {
        1: "dijkstra",
        2: "bellman_ford",
        3: "pca_mr",
        4: "aco",
        5: "ga",
        6: "all",
    }
    return algo_map[choice]


def get_traffic_config():
    """Interactively collect traffic configuration from user."""
    print("\nTraffic intensity options:")
    print("  1. Low (10 flows)")
    print("  2. Medium (20 flows)")
    print("  3. High (40 flows)")
    print("  4. Custom (specify number of flows)")
    choice = get_int_input("Select traffic intensity (1-4): ", 1, 4)

    if choice == 1:
        return "low", 10
    elif choice == 2:
        return "medium", 20
    elif choice == 3:
        return "high", 40
    else:
        flow_count = get_int_input("Enter number of flows (1-100): ", 1, 100)
        return "custom", flow_count


def build_network(topology_type, node_count, edge_prob=None, seed=None, bandwidth_range=(10, 100)):
    """Create and return the selected network topology."""
    network = NetworkTopology(seed=seed)
    if topology_type == "random":
        network.create_random_topology(node_count, edge_prob or 0.3, seed=seed, bandwidth_range=bandwidth_range)
    elif topology_type == "mesh":
        network.create_mesh_topology(node_count, seed=seed, bandwidth_range=bandwidth_range)
    elif topology_type == "ring":
        network.create_ring_topology(node_count, seed=seed, bandwidth_range=bandwidth_range)
    elif topology_type == "star":
        network.create_star_topology(node_count, seed=seed, bandwidth_range=bandwidth_range)
    else:
        raise ValueError(f"Unknown topology type: {topology_type}")

    print(f"\nNetwork created with {network.graph.number_of_nodes()} nodes "
          f"and {network.graph.number_of_edges()} edges.")
    return network


def serialize_results(results):
    """Prepare simulation results for JSON export."""
    serializable = dict(results)
    if "paths" in serializable:
        serializable["paths"] = [list(path) for path in serializable["paths"]]
    return serializable


def flatten_results_for_csv(results):
    """Flatten a single simulation result into one CSV row."""
    return {
        "algorithm": results["algorithm"],
        "execution_time": results["execution_time"],
        "successful_routes": results["successful_routes"],
        "total_flows": results["total_flows"],
        "packet_delivery_ratio": results["packet_delivery_ratio"],
        "average_latency": results["average_latency"],
        "average_throughput": results["average_throughput"],
        "average_hop_count": results["average_hop_count"],
        "congestion_simulated": results.get("congestion_simulated"),
    }


def export_results(results, export_path):
    """Export results as JSON or CSV based on file extension."""
    if not export_path:
        return

    path = Path(export_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()

    if isinstance(results, dict) and "algorithm" in results:
        rows = [flatten_results_for_csv(results)]
        json_payload = serialize_results(results)
    else:
        rows = []
        json_payload = {}
        for algorithm_name, metrics in results.items():
            row = flatten_results_for_csv(metrics)
            row["algorithm_label"] = algorithm_name
            rows.append(row)
            json_payload[algorithm_name] = serialize_results(metrics)

    if suffix == ".json":
        with path.open("w", encoding="utf-8") as file_obj:
            json.dump(json_payload, file_obj, indent=2)
    elif suffix == ".csv":
        fieldnames = list(rows[0].keys()) if rows else []
        with path.open("w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        raise ValueError("Export path must end with .json or .csv")

    print(f"Results exported to {path}")


def print_results(results):
    """Pretty-print single-algorithm results."""
    print("\n=== PERFORMANCE RESULTS ===")
    print(f"  Algorithm            : {results['algorithm']}")
    print(f"  Execution Time       : {results['execution_time']:.4f} seconds")
    print(f"  Successful Routes    : {results['successful_routes']}/{results['total_flows']}")
    print(f"  Packet Delivery Ratio: {results['packet_delivery_ratio']:.2%}")
    print(f"  Average Latency      : {results['average_latency']:.2f} units")
    print(f"  Average Throughput   : {results['average_throughput']:.2f} KB/unit")
    print(f"  Average Hop Count    : {results['average_hop_count']:.2f}")


def print_comparison(comparison):
    """Pretty-print comparison table for all algorithms."""
    print("\n=== ALGORITHM COMPARISON ===")
    header = f"{'Algorithm':<16} {'Time(s)':<10} {'PDR':<8} {'Latency':<10} {'Throughput':<12} {'Hops':<6}"
    print(header)
    print("-" * len(header))
    for alg_name, metrics in comparison.items():
        print(
            f"{alg_name:<16} "
            f"{metrics['execution_time']:<10.4f} "
            f"{metrics['packet_delivery_ratio']:<8.2%} "
            f"{metrics['average_latency']:<10.2f} "
            f"{metrics['average_throughput']:<12.2f} "
            f"{metrics['average_hop_count']:<6.2f}"
        )


def run_single_simulation(network, algorithm_name, flows, seed=None):
    """Run simulation for a single algorithm and print results."""
    algorithm = create_routing_algorithm(algorithm_name, network, seed=seed)
    metrics_analyzer = PerformanceMetrics(network, seed=seed)
    results = metrics_analyzer.analyze_routing_performance(algorithm, flows)
    print_results(results)
    return results


def run_comparison(network, flows, seed=None):
    """Run and compare all available algorithms."""
    algorithms = {
        "Dijkstra":    create_routing_algorithm("dijkstra", network, seed=seed),
        "Bellman-Ford": create_routing_algorithm("bellman_ford", network, seed=None if seed is None else seed + 1),
        "PCA-MR":      create_routing_algorithm("pca_mr", network, seed=None if seed is None else seed + 2),
        "ACO":         create_routing_algorithm("aco", network, seed=None if seed is None else seed + 3),
        "GA":          create_routing_algorithm("ga", network, seed=None if seed is None else seed + 4),
    }
    metrics_analyzer = PerformanceMetrics(network, seed=None if seed is None else seed + 10)
    comparison = metrics_analyzer.compare_algorithms(algorithms, flows)
    print_comparison(comparison)
    return comparison


def interactive_mode(seed=None, export_path=None):
    """Full interactive CLI session."""
    print("=" * 55)
    print("      NETWORK ROUTING SIMULATION")
    print("=" * 55)

    # Collect inputs
    topology_type, node_count, edge_prob, bandwidth_range = get_network_config()
    algorithm_name        = get_algorithm_choice()
    intensity, flow_count = get_traffic_config()

    # Build network & traffic
    network     = build_network(topology_type, node_count, edge_prob=edge_prob, seed=seed, bandwidth_range=bandwidth_range)
    traffic_gen = TrafficGenerator(network, intensity, seed=None if seed is None else seed + 20)
    flows       = traffic_gen.generate_flows(flow_count)
    print(f"Generated {len(flows)} traffic flows.")
    if seed is not None:
        print(f"Using reproducible seed: {seed}")

    # Run simulation
    if algorithm_name == "all":
        results = run_comparison(network, flows, seed=seed)
    else:
        results = run_single_simulation(network, algorithm_name, flows, seed=seed)

    export_results(results, export_path)

    print("\nSimulation complete.")


def main():
    parser = argparse.ArgumentParser(description="Network Routing Simulation")
    parser.add_argument(
        "--mode",
        choices=["interactive", "dashboard"],
        default="interactive",
        help="Execution mode: interactive CLI (default) or web dashboard",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible simulations",
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Optional results export path ending in .json or .csv",
    )
    args = parser.parse_args()

    if args.mode == "dashboard":
        from src.dashboard.app import run_dashboard
        print("Starting dashboard server at http://localhost:8050")
        run_dashboard()
    else:
        interactive_mode(seed=args.seed, export_path=args.export)


if __name__ == "__main__":
    main()
