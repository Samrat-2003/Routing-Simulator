from src.metrics.analyzer import PerformanceMetrics
from src.traffic.generator import TrafficGenerator
from src.algorithms.routing import (
    DijkstraRouting,
    BellmanFordRouting,
    ACORouting,
    GARouting,
)

def comparison_scores(comparison):

    def normalise(values, lower_is_better=False):
        mn = min(values)
        mx = max(values)

        if mn == mx:
            return [1.0] * len(values)

        vals = [(v - mn) / (mx - mn) for v in values]

        return [1 - v for v in vals] if lower_is_better else vals

    names = list(comparison.keys())
    metrics = list(comparison.values())

    pdr = normalise(
        [m["packet_delivery_ratio"] for m in metrics]
    )

    latency = normalise(
        [m["average_latency"] for m in metrics],
        lower_is_better=True
    )

    throughput = normalise(
        [m["average_throughput"] for m in metrics]
    )

    util = normalise(
        [m["max_utilization"] for m in metrics],
        lower_is_better=True
    )

    weights = {
        "pdr": 0.38,
        "latency": 0.22,
        "throughput": 0.15,
        "util": 0.15,
    }

    scores = {}

    for i, name in enumerate(names):
        scores[name] = round(
            weights["pdr"] * pdr[i]
            + weights["latency"] * latency[i]
            + weights["throughput"] * throughput[i]
            + weights["util"] * util[i],
            4,
        )

    return scores

def compare_algorithms(
    network,
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

    algorithms = {
        "dijkstra": DijkstraRouting(network, seed=seed),
        "bellman_ford": BellmanFordRouting(network, seed=seed),
        "aco": ACORouting(network, seed=seed),
        "ga": GARouting(network, seed=seed),
    }

    comparison = analyzer.compare_algorithms(
        algorithms,
        flows,
    )

    return {
    "comparison": comparison,
    "scores": comparison_scores(comparison)
}

