import json
import os
import random

import networkx as nx


class NetworkTopology:
    def __init__(self, config_path=None, seed=None):
        _defaults = {
            "network": {"node_count": 10, "edge_probability": 0.3},
            "traffic": {"low_intensity": 10, "medium_intensity": 20, "high_intensity": 40},
        }

        if config_path is None:
            _here = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(_here, "..", "..", "config", "config.json")

        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = _defaults

        self.seed = seed
        self.random = random.Random(seed)
        self.graph = None

    def set_seed(self, seed):
        """Reset the topology RNG so generated networks are reproducible."""
        self.seed = seed
        self.random = random.Random(seed)

    def _prepare_rng(self, seed=None):
        """Refresh the RNG for a topology build and return the effective seed."""
        effective_seed = self.seed if seed is None else seed
        self.set_seed(effective_seed)
        return effective_seed

    def create_mesh_topology(self, n_nodes=10, seed=None, bandwidth_range=(10, 100)):
        """Create a mesh network topology"""
        self._prepare_rng(seed)
        self.graph = nx.complete_graph(n_nodes)
        self._assign_edge_weights(bandwidth_range=bandwidth_range)
        return self.graph

    def create_random_topology(self, n_nodes=10, p=0.3, seed=None, bandwidth_range=(10, 100)):
        """Create a random network topology using Erdos-Renyi model"""
        effective_seed = self._prepare_rng(seed)
        self.graph = nx.erdos_renyi_graph(n_nodes, p, seed=effective_seed)
        # Ensure connectivity
        if not nx.is_connected(self.graph):
            fallback_seed = self.random.randint(0, 10**9)
            self.graph = nx.connected_watts_strogatz_graph(n_nodes, 3, 0.3, seed=fallback_seed)
        self._assign_edge_weights(bandwidth_range=bandwidth_range)
        return self.graph

    def create_ring_topology(self, n_nodes=10, seed=None, bandwidth_range=(10, 100)):
        """Create a ring network topology"""
        self._prepare_rng(seed)
        self.graph = nx.cycle_graph(n_nodes)
        self._assign_edge_weights(bandwidth_range=bandwidth_range)
        return self.graph

    def create_star_topology(self, n_nodes=10, seed=None, bandwidth_range=(10, 100)):
        """Create a star network topology"""
        self._prepare_rng(seed)
        self.graph = nx.star_graph(n_nodes - 1)
        self._assign_edge_weights(bandwidth_range=bandwidth_range)
        return self.graph

    def load_from_data(self, nodes=None, edges=None, seed=None):
        """Load a topology from explicit node and edge records."""
        self._prepare_rng(seed)
        self.graph = nx.Graph()

        normalised_nodes = nodes or []
        if not normalised_nodes and edges:
            seen = set()
            for edge in edges:
                seen.add(edge.get("source", edge.get("u")))
                seen.add(edge.get("target", edge.get("v")))
            normalised_nodes = [{"id": node_id} for node_id in sorted(seen)]

        for node in normalised_nodes:
            if isinstance(node, dict):
                node_id = node.get("id", node.get("node_id"))
                attrs = {k: v for k, v in node.items() if k not in {"id", "node_id"}}
            else:
                node_id = node
                attrs = {}
            self.graph.add_node(node_id, packet_loss=float(attrs.get("packet_loss", 0.0)), **attrs)

        for edge in edges or []:
            source = edge.get("source", edge.get("u"))
            target = edge.get("target", edge.get("v"))
            if source is None or target is None:
                continue
            attrs = {k: v for k, v in edge.items() if k not in {"source", "target", "u", "v"}}
            weight = float(attrs.pop("weight", 1))
            bandwidth = float(attrs.pop("bandwidth", 100))
            packet_loss = float(attrs.pop("packet_loss", 0.0))
            self.graph.add_edge(
                source,
                target,
                weight=weight,
                base_weight=weight,  # static distance, untouched by congestion
                bandwidth=bandwidth,
                packet_loss=packet_loss,
                maintenance_factor=float(attrs.pop("maintenance_factor", 1.0)),
                **attrs,
            )

        return self.graph

    def apply_failure_profile(self, profile=None):
        """Apply scenario modifications such as failures, packet loss, and maintenance."""
        profile = profile or {}
        if self.graph is None:
            raise ValueError("Graph has not been created yet.")

        for node in profile.get("down_nodes", []):
            if self.graph.has_node(node):
                self.graph.remove_node(node)

        for u, v in profile.get("down_edges", []):
            if self.graph.has_edge(u, v):
                self.graph.remove_edge(u, v)

        for node, probability in profile.get("packet_loss_nodes", {}).items():
            if self.graph.has_node(node):
                current = float(self.graph.nodes[node].get("packet_loss", 0.0))
                self.graph.nodes[node]["packet_loss"] = max(current, float(probability))

        for (u, v), probability in profile.get("packet_loss_edges", {}).items():
            if self.graph.has_edge(u, v):
                current = float(self.graph[u][v].get("packet_loss", 0.0))
                self.graph[u][v]["packet_loss"] = max(current, float(probability))

        for (u, v), factor in profile.get("maintenance_edges", {}).items():
            if self.graph.has_edge(u, v):
                # Maintenance is a persistent scenario condition, not transient
                # congestion, so it updates base_weight (the congestion-free
                # reference distance) as well as the live weight.
                pre_maintenance_weight = float(
                    self.graph[u][v].get("base_weight", self.graph[u][v].get("weight", 1))
                )
                multiplier = max(1.0, float(factor))
                self.graph[u][v]["maintenance_factor"] = multiplier
                self.graph[u][v]["base_weight"] = pre_maintenance_weight * multiplier
                self.graph[u][v]["weight"] = pre_maintenance_weight * multiplier

    def build_random_failure_profile(
        self,
        seed=None,
        down_node_count=0,
        down_edge_count=0,
        packet_loss_node_count=0,
        packet_loss_edge_count=0,
        maintenance_edge_count=0,
        packet_loss_range=(0.1, 0.35),
        maintenance_factor_range=(1.25, 2.0),
    ):
        """Create a reproducible random failure profile from the current graph."""
        if self.graph is None:
            raise ValueError("Graph has not been created yet.")

        rng = random.Random(self.seed if seed is None else seed)
        nodes = list(self.graph.nodes())
        edges = [(min(u, v), max(u, v)) for u, v in self.graph.edges()]

        def sample(items, count):
            return rng.sample(items, min(max(int(count or 0), 0), len(items))) if items else []

        def random_value(bounds):
            low, high = sorted((float(bounds[0]), float(bounds[1])))
            return round(rng.uniform(float(low), float(high)), 2)

        down_nodes = sample(nodes, down_node_count)
        remaining_edges = [edge for edge in edges if edge[0] not in down_nodes and edge[1] not in down_nodes]
        down_edges = sample(remaining_edges, down_edge_count)
        active_nodes = [node for node in nodes if node not in down_nodes]
        active_edges = [edge for edge in remaining_edges if edge not in down_edges]

        packet_loss_nodes = {node: random_value(packet_loss_range) for node in sample(active_nodes, packet_loss_node_count)}
        packet_loss_edges = {edge: random_value(packet_loss_range) for edge in sample(active_edges, packet_loss_edge_count)}
        maintenance_edges = {edge: random_value(maintenance_factor_range) for edge in sample(active_edges, maintenance_edge_count)}

        return {
            "down_nodes": down_nodes,
            "down_edges": down_edges,
            "packet_loss_nodes": packet_loss_nodes,
            "packet_loss_edges": packet_loss_edges,
            "maintenance_edges": maintenance_edges,
        }

    def _normalise_bandwidth_range(self, bandwidth_range):
        if not bandwidth_range:
            return 10, 100

        low, high = bandwidth_range
        low = max(1, int(float(low)))
        high = max(1, int(float(high)))
        if low > high:
            low, high = high, low
        return low, high

    def _assign_edge_weights(self, bandwidth_range=(10, 100)):
        """Assign random weights to edges (representing delay/cost)"""
        bandwidth_min, bandwidth_max = self._normalise_bandwidth_range(bandwidth_range)
        for (u, v) in self.graph.edges():
            weight = self.random.randint(1, 10)
            self.graph[u][v]["weight"] = weight
            self.graph[u][v]["base_weight"] = weight  # static distance, untouched by congestion
            self.graph[u][v]["bandwidth"] = self.random.randint(bandwidth_min, bandwidth_max)
            self.graph[u][v]["packet_loss"] = 0.0
            self.graph[u][v]["maintenance_factor"] = 1.0
        for node in self.graph.nodes():
            self.graph.nodes[node]["packet_loss"] = 0.0

    def get_shortest_path(self, source, target, weight="weight"):
        """Get shortest path between two nodes"""
        try:
            return nx.shortest_path(self.graph, source, target, weight=weight)
        except nx.NetworkXNoPath:
            return None

    def get_network_info(self):
        """Get basic network information"""
        info = {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "is_connected": nx.is_connected(self.graph) if self.graph.number_of_nodes() > 0 else False,
        }
        return info

# Example usage
if __name__ == "__main__":
    net = NetworkTopology()
    g = net.create_mesh_topology(5)
    print("Network Info:", net.get_network_info())
    print("Shortest path from 0 to 4:", net.get_shortest_path(0, 4))
