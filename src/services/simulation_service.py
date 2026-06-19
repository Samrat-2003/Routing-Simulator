

from src.algorithms.routing import create_routing_algorithm
from src.metrics.analyzer import PerformanceMetrics
from src.traffic.generator import TrafficGenerator
from src.network.topology import NetworkTopology
from src.planning.recommendations import build_recommendations
from src.reporting.exporter import export_simulation_bundle


def simulate_network(
    network,
    algorithm_type,
    traffic_intensity="medium",
    flow_count=20,
    seed=None,
):
    traffic_gen = TrafficGenerator(
        network,
        traffic_intensity,
        seed=seed,
    )

    flows = traffic_gen.generate_flows(flow_count)

    analyzer = PerformanceMetrics(
        network,
        seed=seed,
    )

    algorithm = create_routing_algorithm(
        algorithm_type,
        network,
        seed=seed,
    )

    results = analyzer.analyze_routing_performance(
        algorithm,
        flows,
    )

    return results