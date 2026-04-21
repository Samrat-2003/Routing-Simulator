import time
import pandas as pd
from collections import defaultdict

CONGESTION_PENALTY   = 0.25
CONGESTION_THRESHOLD = 3
DROP_PROBABILITY     = 0.30

class PerformanceMetrics:
    def __init__(self, network, simulate_congestion=True):
        self.network              = network
        self.simulate_congestion  = simulate_congestion
        self.metrics_history      = []

    def calculate_latency(self, path):
        if not path or len(path) < 2:
            return 0
        total = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if self.network.graph.has_edge(u, v):
                total += self.network.graph[u][v].get('weight', 1)
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
        return {(u, v): dict(data)
                for u, v, data in self.network.graph.edges(data=True)}

    def _restore_weights(self, snapshot):
        for (u, v), data in snapshot.items():
            if self.network.graph.has_edge(u, v):
                self.network.graph[u][v].update(data)

    def _apply_congestion(self, path, edge_usage):
        import random as _random
        delivered = True
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            key  = (min(u, v), max(u, v))
            usage = edge_usage.get(key, 0)
            if usage >= CONGESTION_THRESHOLD:
                if _random.random() < DROP_PROBABILITY:
                    delivered = False
            if self.network.graph.has_edge(u, v):
                old_w = self.network.graph[u][v].get('weight', 1)
                self.network.graph[u][v]['weight'] = old_w * (1 + CONGESTION_PENALTY)
            edge_usage[key] = usage + 1
        return delivered

    def analyze_routing_performance(self, algorithm, traffic_flows):
        start_time      = time.time()
        weight_snapshot = self._save_weights()

        paths             = []
        latencies         = []
        throughputs       = []
        hop_counts        = []
        successful_routes = 0
        edge_usage        = defaultdict(int)

        for flow in traffic_flows:
            # For ACO: reset pheromones each flow so it adapts to current congested weights
            if hasattr(algorithm, '_initialize_pheromones'):
                algorithm._initialize_pheromones()

            path = algorithm.route(flow.source, flow.destination)

            if path:
                hop_count = self.calculate_hop_count(path)

                if self.simulate_congestion:
                    delivered = self._apply_congestion(path, edge_usage)
                else:
                    delivered = True

                # FIX: measure latency AFTER congestion so degraded weights are captured
                latency    = self.calculate_latency(path)
                throughput = self.calculate_throughput(path, flow.size)

                # FIX: tell ACO/GA about this flow so they route around congestion
                if hasattr(algorithm, 'update_edge_load'):
                    algorithm.update_edge_load(path)

                if delivered:
                    paths.append(path)
                    latencies.append(latency)
                    throughputs.append(throughput)
                    hop_counts.append(hop_count)
                    successful_routes += 1
                else:
                    latencies.append(None)
                    throughputs.append(None)
                    hop_counts.append(None)
            else:
                latencies.append(None)
                throughputs.append(None)
                hop_counts.append(None)

        execution_time = time.time() - start_time
        self._restore_weights(weight_snapshot)

        valid_l = [l for l in latencies   if l is not None]
        valid_t = [t for t in throughputs if t is not None]
        valid_h = [h for h in hop_counts  if h is not None]

        metrics = {
            "algorithm":             algorithm.__class__.__name__,
            "execution_time":        execution_time,
            "successful_routes":     successful_routes,
            "total_flows":           len(traffic_flows),
            "packet_delivery_ratio": self.calculate_packet_delivery_ratio(
                                         successful_routes, len(traffic_flows)),
            "average_latency":       sum(valid_l) / len(valid_l) if valid_l else 0,
            "average_throughput":    sum(valid_t) / len(valid_t) if valid_t else 0,
            "average_hop_count":     sum(valid_h) / len(valid_h) if valid_h else 0,
            "paths":                 paths,
            "latencies":             latencies,
            "throughputs":           throughputs,
            "hop_counts":            hop_counts,
            "congestion_simulated":  self.simulate_congestion,
        }

        self.metrics_history.append(metrics)
        return metrics

    def compare_algorithms(self, algorithms, traffic_flows):
        results = {}
        for name, algorithm in algorithms.items():
            snapshot = self._save_weights()
            metrics  = self.analyze_routing_performance(algorithm, traffic_flows)
            self._restore_weights(snapshot)
            results[name] = metrics
        return results

    def get_metrics_dataframe(self):
        return pd.DataFrame(self.metrics_history)