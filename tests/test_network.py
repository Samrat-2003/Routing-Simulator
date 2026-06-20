import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.network.topology import NetworkTopology

class TestNetworkTopology(unittest.TestCase):
    def setUp(self):
        self.network = NetworkTopology()
    
    def test_mesh_topology_creation(self):
        """Test creation of mesh topology"""
        graph = self.network.create_mesh_topology(5)
        self.assertEqual(graph.number_of_nodes(), 5)
        self.assertEqual(graph.number_of_edges(), 10)  # Complete graph: n*(n-1)/2
    
    def test_random_topology_creation(self):
        """Test creation of random topology"""
        graph = self.network.create_random_topology(10, 0.3)
        self.assertEqual(graph.number_of_nodes(), 10)
        self.assertTrue(graph.number_of_edges() >= 0)
    
    def test_ring_topology_creation(self):
        """Test creation of ring topology"""
        graph = self.network.create_ring_topology(5)
        self.assertEqual(graph.number_of_nodes(), 5)
        self.assertEqual(graph.number_of_edges(), 5)
    
    def test_star_topology_creation(self):
        """Test creation of star topology"""
        graph = self.network.create_star_topology(5)  # 5 nodes including center
        self.assertEqual(graph.number_of_nodes(), 5)
        self.assertEqual(graph.number_of_edges(), 4)
    
    def test_shortest_path(self):
        """Test shortest path calculation"""
        self.network.create_mesh_topology(5)
        path = self.network.get_shortest_path(0, 4)
        self.assertIsNotNone(path)
        self.assertIn(0, path)
        self.assertIn(4, path)

    def test_seeded_random_topology_is_reproducible(self):
        """Seeded random topologies should reproduce the same weighted graph."""
        first = NetworkTopology(seed=123)
        second = NetworkTopology(seed=123)

        graph_a = first.create_random_topology(10, 0.3, seed=123)
        graph_b = second.create_random_topology(10, 0.3, seed=123)

        self.assertEqual(sorted(graph_a.edges(data="weight")), sorted(graph_b.edges(data="weight")))

    def test_generated_topology_respects_bandwidth_range(self):
        """Generated links should use the user-selected bandwidth range."""
        network = NetworkTopology(seed=31)
        graph = network.create_mesh_topology(6, seed=31, bandwidth_range=(20, 25))

        bandwidths = [data["bandwidth"] for _, _, data in graph.edges(data=True)]
        self.assertTrue(bandwidths)
        self.assertGreaterEqual(min(bandwidths), 20)
        self.assertLessEqual(max(bandwidths), 25)

    def test_reversed_bandwidth_range_is_normalised(self):
        """Bandwidth inputs should be accepted even if the user swaps min and max."""
        network = NetworkTopology(seed=32)
        graph = network.create_ring_topology(5, seed=32, bandwidth_range=(40, 10))

        bandwidths = [data["bandwidth"] for _, _, data in graph.edges(data=True)]
        self.assertGreaterEqual(min(bandwidths), 10)
        self.assertLessEqual(max(bandwidths), 40)

    def test_imported_topology_and_failure_profile(self):
        """Imported topologies should accept explicit failure rules."""
        network = NetworkTopology(seed=12)
        network.load_from_data(
            nodes=[{"id": 1}, {"id": 2}, {"id": 3}],
            edges=[
                {"source": 1, "target": 2, "weight": 2, "bandwidth": 100},
                {"source": 2, "target": 3, "weight": 3, "bandwidth": 80},
            ],
        )

        network.apply_failure_profile(
            {
                "packet_loss_nodes": {1: 0.15},
                "maintenance_edges": {(1, 2): 2.0},
                "down_edges": [(2, 3)],
            }
        )

        self.assertTrue(network.graph.has_edge(1, 2))
        self.assertFalse(network.graph.has_edge(2, 3))
        self.assertEqual(network.graph[1][2]["weight"], 4.0)
        self.assertEqual(network.graph.nodes[1]["packet_loss"], 0.15)

    def test_random_failure_profile_is_reproducible(self):
        """Random failure profiles should be reproducible with the same seed."""
        network = NetworkTopology(seed=21)
        network.create_mesh_topology(6, seed=21)

        first = network.build_random_failure_profile(
            seed=99,
            down_node_count=1,
            down_edge_count=2,
            packet_loss_node_count=1,
            packet_loss_edge_count=2,
            maintenance_edge_count=2,
        )
        second = network.build_random_failure_profile(
            seed=99,
            down_node_count=1,
            down_edge_count=2,
            packet_loss_node_count=1,
            packet_loss_edge_count=2,
            maintenance_edge_count=2,
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first["down_nodes"]), 1)
        self.assertLessEqual(len(first["down_edges"]), 2)

if __name__ == '__main__':
    unittest.main()
