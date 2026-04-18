import networkx as nx
import random
import json
import os

class NetworkTopology:
    def __init__(self, config_path=None):
        # Default config values used when the file is missing or not specified
        _defaults = {
            "network": {"node_count": 10, "edge_probability": 0.3},
            "traffic": {"low_intensity": 10, "medium_intensity": 20, "high_intensity": 40}
        }

        if config_path is None:
            # Always resolve relative to this file, not the working directory
            _here = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(_here, "..", "..", "config", "config.json")

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.config = _defaults

        self.graph = None
        
    def create_mesh_topology(self, n_nodes=10):
        """Create a mesh network topology"""
        self.graph = nx.complete_graph(n_nodes)
        self._assign_edge_weights()
        return self.graph
    
    def create_random_topology(self, n_nodes=10, p=0.3):
        """Create a random network topology using Erdos-Renyi model"""
        self.graph = nx.erdos_renyi_graph(n_nodes, p)
        # Ensure connectivity
        if not nx.is_connected(self.graph):
            self.graph = nx.connected_watts_strogatz_graph(n_nodes, 3, 0.3)
        self._assign_edge_weights()
        return self.graph
    
    def create_ring_topology(self, n_nodes=10):
        """Create a ring network topology"""
        self.graph = nx.cycle_graph(n_nodes)
        self._assign_edge_weights()
        return self.graph
    
    def create_star_topology(self, n_nodes=10):
        """Create a star network topology"""
        self.graph = nx.star_graph(n_nodes-1)
        self._assign_edge_weights()
        return self.graph
    
    def _assign_edge_weights(self):
        """Assign random weights to edges (representing delay/cost)"""
        for (u, v) in self.graph.edges():
            # Assign random weights between 1 and 10
            weight = random.randint(1, 10)
            self.graph[u][v]['weight'] = weight
            self.graph[u][v]['bandwidth'] = random.randint(10, 100)  # Mbps
    
    def get_shortest_path(self, source, target, weight='weight'):
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
            "is_connected": nx.is_connected(self.graph)
        }
        return info

# Example usage
if __name__ == "__main__":
    net = NetworkTopology()
    g = net.create_mesh_topology(5)
    print("Network Info:", net.get_network_info())
    print("Shortest path from 0 to 4:", net.get_shortest_path(0, 4))