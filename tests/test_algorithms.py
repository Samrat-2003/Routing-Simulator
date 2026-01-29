import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.network.topology import NetworkTopology
from src.algorithms.routing import DijkstraRouting, BellmanFordRouting

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

if __name__ == '__main__':
    unittest.main()
