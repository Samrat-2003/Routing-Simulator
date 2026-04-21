import time
import random
from collections import defaultdict

try:
    import pandas as pd
except ImportError:  # pragma: no cover - exercised only in lean environments
    pd = None

CONGESTION_PENALTY = 0.25
OVERLOAD_DROP_FACTOR = 0.35
MAX_OVERLOAD_DROP = 0.65


class PerformanceMetrics:
    def __init__(self, network, simulate_congestion=True, seed=None):
        self.network = network
        self.simulate_congestion = simulate_congestion
        self.metrics_history = []
        self.seed = seed
        self.random = random.Random(seed)

    def calculate_latency(self, path):
        if not path or len(path) < 2:
            return 0
        total = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if self.network.graph.has_edge(u, v):
                total += self.network.graph[u][v].get("weight", 1)
        return total

    def calculate_throughput(self, path, packet_size):
        latency = self.calculate_latency(path)
        return packet_size / latency if latency > 0 else 0

    def calculate_hop_count(self, path):
        return len(path) - 1 if path else 0

    def calculate_packet_delivery_ratio(self, successful, total):
        return successful / total if total > 0 else 0

    def calculate_load_distribution(self, paths):
        edge_usage = defaultdict(int)
        for path in paths:
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_usage[(min(u, v), max(u, v))] += 1
        return dict(edge_usage)

    def _save_weights(self):
        return {(u, v): dict(data) for u, v, data in self.network.graph.edges(data=True)}

    def _restore_weights(self, snapshot):
        for (u, v), data in snapshot.items():
            if self.network.graph.has_edge(u, v):
                self.network.graph[u][v].clear()
                self.network.graph[u][v].update(data)

    def _edge_key(self, u, v):
        return (min(u, v), max(u, v))

    def _capacity_drop_probability(self, load_ratio):
        if not self.simulate_congestion or load_ratio <= 1:
            return 0.0
        return min(MAX_OVERLOAD_DROP, (load_ratio - 1) * OVERLOAD_DROP_FACTOR)

    def _apply_flow_effects(self, path, packet_size, edge_usage, edge_volume):
        delivered = True
        drop_probability = 0.0

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = self.network.graph[u][v]
            key = self._edge_key(u, v)
            bandwidth = max(float(edge.get("bandwidth", 100)), 1.0)

            projected_load = edge_volume[key] + packet_size
            load_ratio = projected_load / bandwidth
            edge_volume[key] = projected_load
            edge_usage[key] += 1

            static_drop = max(
                float(edge.get("packet_loss", 0.0)),
                float(self.network.graph.nodes[u].get("packet_loss", 0.0)),
                float(self.network.graph.nodes[v].get("packet_loss", 0.0)),
            )
            drop_probability = max(drop_probability, static_drop, self._capacity_drop_probability(load_ratio))

            if self.simulate_congestion:
                edge["weight"] = float(edge.get("weight", 1.0)) * (1 + CONGESTION_PENALTY * max(load_ratio, 0.1))

        if drop_probability > 0 and self.random.random() < drop_probability:
            delivered = False

        return delivered, drop_probability

    def _serialise_edge_loads(self, edge_usage, edge_volume):
        edge_loads = {}
        for u, v, data in self.network.graph.edges(data=True):
            key = self._edge_key(u, v)
            load = edge_volume.get(key, 0.0)
            bandwidth = max(float(data.get("bandwidth", 100)), 1.0)
            edge_loads[f"{key[0]}-{key[1]}"] = {
                "u": key[0],
                "v": key[1],
                "load": round(load, 2),
                "packets": edge_usage.get(key, 0),
                "bandwidth": bandwidth,
                "load_ratio": round(load / bandwidth, 4),
                "weight": round(float(data.get("weight", 1.0)), 4),
                "packet_loss": round(float(data.get("packet_loss", 0.0)), 4),
            }
        return edge_loads

    def analyze_routing_performance(self, algorithm, traffic_flows):
        start_time = time.time()
        weight_snapshot = self._save_weights()

        paths = []
        latencies = []
        throughputs = []
        hop_counts = []
        successful_routes = 0
        dropped_flows = 0
        edge_usage = defaultdict(int)
        edge_volume = defaultdict(float)
        flow_details = []

        for flow in traffic_flows:
            if hasattr(algorithm, "_initialize_pheromones"):
                algorithm._initialize_pheromones()

            path = algorithm.route(flow.source, flow.destination)

            if not path:
                dropped_flows += 1
                latencies.append(None)
                throughputs.append(None)
                hop_counts.append(None)
                flow_details.append(
                    {
                        "source": flow.source,
                        "destination": flow.destination,
                        "packet_size": flow.size,
                        "path": None,
                        "latency": None,
                        "throughput": None,
                        "delivered": False,
                        "drop_probability": 0.0,
                    }
                )
                continue

            delivered, drop_probability = self._apply_flow_effects(path, flow.size, edge_usage, edge_volume)
            latency = self.calculate_latency(path)
            throughput = self.calculate_throughput(path, flow.size)
            hop_count = self.calculate_hop_count(path)

            if delivered:
                paths.append(path)
                successful_routes += 1
            else:
                dropped_flows += 1

            latencies.append(latency if delivered else None)
            throughputs.append(throughput if delivered else None)
            hop_counts.append(hop_count if delivered else None)
            flow_details.append(
                {
                    "source": flow.source,
                    "destination": flow.destination,
                    "packet_size": flow.size,
                    "path": path,
                    "latency": latency if delivered else None,
                    "throughput": throughput if delivered else None,
                    "delivered": delivered,
                    "drop_probability": round(drop_probability, 4),
                }
            )

            if hasattr(algorithm, "update_edge_load"):
                algorithm.update_edge_load(path)

        execution_time = time.time() - start_time
        edge_loads = self._serialise_edge_loads(edge_usage, edge_volume)
        self._restore_weights(weight_snapshot)

        valid_l = [l for l in latencies if l is not None]
        valid_t = [t for t in throughputs if t is not None]
        valid_h = [h for h in hop_counts if h is not None]
        load_ratios = [edge["load_ratio"] for edge in edge_loads.values()]

        metrics = {
            "algorithm": algorithm.__class__.__name__,
            "execution_time": execution_time,
            "successful_routes": successful_routes,
            "dropped_flows": dropped_flows,
            "total_flows": len(traffic_flows),
            "packet_delivery_ratio": self.calculate_packet_delivery_ratio(successful_routes, len(traffic_flows)),
            "average_latency": sum(valid_l) / len(valid_l) if valid_l else 0,
            "average_throughput": sum(valid_t) / len(valid_t) if valid_t else 0,
            "average_hop_count": sum(valid_h) / len(valid_h) if valid_h else 0,
            "average_utilization": sum(load_ratios) / len(load_ratios) if load_ratios else 0,
            "max_utilization": max(load_ratios) if load_ratios else 0,
            "congested_edges": sum(1 for ratio in load_ratios if ratio >= 0.85),
            "paths": paths,
            "latencies": latencies,
            "throughputs": throughputs,
            "hop_counts": hop_counts,
            "flow_details": flow_details,
            "edge_loads": edge_loads,
            "congestion_simulated": self.simulate_congestion,
        }

        self.metrics_history.append(metrics)
        return metrics

    def compare_algorithms(self, algorithms, traffic_flows):
        results = {}
        for name, algorithm in algorithms.items():
            snapshot = self._save_weights()
            metrics = self.analyze_routing_performance(algorithm, traffic_flows)
            self._restore_weights(snapshot)
            results[name] = metrics
        return results

    def get_metrics_dataframe(self):
        if pd is None:
            return list(self.metrics_history)
        return pd.DataFrame(self.metrics_history)
