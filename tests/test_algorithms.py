import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.network.topology import NetworkTopology
from src.algorithms.routing import BellmanFordRouting, DijkstraRouting, GARouting, PCAMRRouting, create_routing_algorithm

class TestRoutingAlgorithms(unittest.TestCase):
    def setUp(self):
        self.network = NetworkTopology()
        self.network.create_mesh_topology(5)
    
    def test_dijkstra_routing(self):
        """Test Dijkstra routing algorithm"""
        dijkstra = DijkstraRouting(self.network)
        path = dijkstra.route(0, 4)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], 0)
        self.assertEqual(path[-1], 4)
    
    def test_bellman_ford_routing(self):
        """Test Bellman-Ford routing algorithm"""
        bellman_ford = BellmanFordRouting(self.network)
        path = bellman_ford.route(0, 4)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], 0)
        self.assertEqual(path[-1], 4)
    
    def test_same_results_dijkstra_bellman_ford(self):
        """Test that Dijkstra and Bellman-Ford produce same results for positive weights"""
        dijkstra = DijkstraRouting(self.network)
        bellman_ford = BellmanFordRouting(self.network)
        
        path_d = dijkstra.route(0, 4)
        path_b = bellman_ford.route(0, 4)
        
        # Both should find a path
        self.assertIsNotNone(path_d)
        self.assertIsNotNone(path_b)
        
        # Calculate path costs
        cost_d = sum(self.network.graph[path_d[i]][path_d[i+1]].get('weight', 1) 
                     for i in range(len(path_d)-1))
        cost_b = sum(self.network.graph[path_b[i]][path_b[i+1]].get('weight', 1) 
                     for i in range(len(path_b)-1))
        
        # Costs should be equal (both find shortest path)
        self.assertEqual(cost_d, cost_b)

    def test_ga_repairs_invalid_candidate_paths(self):
        """GA should repair broken paths into valid graph routes."""
        network = NetworkTopology(seed=11)
        network.create_ring_topology(6, seed=11)
        ga = GARouting(network, seed=11)

        repaired = ga._repair_path([0, 3, 5], 0, 4)

        self.assertIsNotNone(repaired)
        self.assertEqual(repaired[0], 0)
        self.assertEqual(repaired[-1], 4)
        for index in range(len(repaired) - 1):
            self.assertTrue(network.graph.has_edge(repaired[index], repaired[index + 1]))

    def test_pca_mr_avoids_short_unreliable_path(self):
        """PCA-MR should prefer reliable links over a lossy shortest path."""
        network = NetworkTopology(seed=3)
        network.load_from_data(
            nodes=[{"id": 0}, {"id": 1}, {"id": 2}],
            edges=[
                {"source": 0, "target": 1, "weight": 1, "bandwidth": 100, "packet_loss": 0.8},
                {"source": 1, "target": 2, "weight": 1, "bandwidth": 100, "packet_loss": 0.8},
                {"source": 0, "target": 2, "weight": 10, "bandwidth": 100, "packet_loss": 0.0},
            ],
        )

        dijkstra = DijkstraRouting(network)
        pca_mr = PCAMRRouting(network)

        self.assertEqual(dijkstra.route(0, 2), [0, 1, 2])
        self.assertEqual(pca_mr.route(0, 2), [0, 2])

    def test_factory_creates_pca_mr(self):
        """The proposed algorithm should be available through the public factory."""
        algorithm = create_routing_algorithm("pca_mr", self.network, seed=13)

        self.assertIsInstance(algorithm, PCAMRRouting)

    def test_pca_mr_adapts_weights_for_lossy_networks(self):
        """PCA-MR+ should increase reliability weight when loss is present."""
        network = NetworkTopology(seed=17)
        network.load_from_data(
            nodes=[{"id": 0}, {"id": 1}, {"id": 2}],
            edges=[
                {"source": 0, "target": 1, "weight": 1, "bandwidth": 100, "packet_loss": 0.0},
                {"source": 1, "target": 2, "weight": 1, "bandwidth": 100, "packet_loss": 0.0},
                {"source": 0, "target": 2, "weight": 3, "bandwidth": 100, "packet_loss": 0.0},
            ],
        )
        pca_mr = PCAMRRouting(network)
        _, clean_beta, _ = pca_mr._adaptive_weights()

        network.graph[0][1]["packet_loss"] = 0.4
        _, lossy_beta, _ = pca_mr._adaptive_weights()

        self.assertGreater(lossy_beta, clean_beta)

    def test_pca_mr_diverts_from_overloaded_bottleneck(self):
        """PCA-MR+ should use candidate paths to avoid a congested short route."""
        network = NetworkTopology(seed=19)
        network.load_from_data(
            nodes=[{"id": 0}, {"id": 1}, {"id": 2}, {"id": 3}],
            edges=[
                {"source": 0, "target": 1, "weight": 1, "bandwidth": 10, "packet_loss": 0.0},
                {"source": 1, "target": 3, "weight": 1, "bandwidth": 10, "packet_loss": 0.0},
                {"source": 0, "target": 2, "weight": 2, "bandwidth": 100, "packet_loss": 0.0},
                {"source": 2, "target": 3, "weight": 2, "bandwidth": 100, "packet_loss": 0.0},
            ],
        )
        pca_mr = PCAMRRouting(network)
        pca_mr.current_packet_size = 1
        pca_mr.edge_loads[(0, 1)] = 10

        self.assertEqual(pca_mr.route(0, 3), [0, 2, 3])

if __name__ == '__main__':
    unittest.main()
