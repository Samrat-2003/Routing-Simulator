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

if __name__ == '__main__':
    unittest.main()
