"""
Network Routing Simulation Project
Main execution script with interactive CLI
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
    node_count = get_int_input("Enter number of nodes (10-200): ", 10, 200)
    edge_prob  = get_float_input("Enter edge probability (0.1-0.8): ", 0.1, 0.8)
    return node_count, edge_prob


def get_algorithm_choice():
    """Interactively collect algorithm selection from user."""
    print("\nAvailable routing algorithms:")
    print("  1. Dijkstra (shortest path)")
    print("  2. Bellman-Ford (distributed shortest path)")
    print("  3. ACO (Ant Colony Optimization)")
    print("  4. GA (Genetic Algorithm)")
    print("  5. ALL (compare all algorithms)")
    choice = get_int_input("Select algorithm (1-5): ", 1, 5)

    algo_map = {
        1: "dijkstra",
        2: "bellman_ford",
        3: "aco",
        4: "ga",
        5: "all",
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


def build_network(node_count, edge_prob):
    """Create and return a random (connected) network topology."""
    network = NetworkTopology()
    network.create_random_topology(node_count, edge_prob)
    print(f"\nNetwork created with {network.graph.number_of_nodes()} nodes "
          f"and {network.graph.number_of_edges()} edges.")
    return network


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


def run_single_simulation(network, algorithm_name, flows):
    """Run simulation for a single algorithm and print results."""
    algorithm = create_routing_algorithm(algorithm_name, network)
    metrics_analyzer = PerformanceMetrics(network)
    results = metrics_analyzer.analyze_routing_performance(algorithm, flows)
    print_results(results)
    return results


def run_comparison(network, flows):
    """Run and compare all four algorithms."""
    algorithms = {
        "Dijkstra":    create_routing_algorithm("dijkstra",    network),
        "Bellman-Ford": create_routing_algorithm("bellman_ford", network),
        "ACO":         create_routing_algorithm("aco",         network),
        "GA":          create_routing_algorithm("ga",          network),
    }
    metrics_analyzer = PerformanceMetrics(network)
    comparison = metrics_analyzer.compare_algorithms(algorithms, flows)
    print_comparison(comparison)
    return comparison


def interactive_mode():
    """Full interactive CLI session."""
    print("=" * 55)
    print("      NETWORK ROUTING SIMULATION")
    print("=" * 55)

    # Collect inputs
    node_count, edge_prob = get_network_config()
    algorithm_name        = get_algorithm_choice()
    intensity, flow_count = get_traffic_config()

    # Build network & traffic
    network     = build_network(node_count, edge_prob)
    traffic_gen = TrafficGenerator(network, intensity)
    flows       = traffic_gen.generate_flows(flow_count)
    print(f"Generated {len(flows)} traffic flows.")

    # Run simulation
    if algorithm_name == "all":
        run_comparison(network, flows)
    else:
        run_single_simulation(network, algorithm_name, flows)

    print("\nSimulation complete.")


def main():
    parser = argparse.ArgumentParser(description="Network Routing Simulation")
    parser.add_argument(
        "--mode",
        choices=["interactive", "dashboard"],
        default="interactive",
        help="Execution mode: interactive CLI (default) or web dashboard",
    )
    args = parser.parse_args()

    if args.mode == "dashboard":
        from src.dashboard.app import run_dashboard
        print("Starting dashboard server at http://localhost:8050")
        run_dashboard()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()