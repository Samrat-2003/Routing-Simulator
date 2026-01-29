import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.network.topology import NetworkTopology
from src.algorithms.routing import DijkstraRouting
from src.traffic.generator import TrafficGenerator
from src.metrics.analyzer import PerformanceMetrics

class TestPerformanceMetrics(unittest.TestCase):
    def setUp(self):
        self.network = NetworkTopology()
        self.network.create_mesh_topology(5)
        self.metrics = PerformanceMetrics(self.network)
    
    def test_latency_calculation(self):
        """Test latency calculation"""
        path = [0, 1, 2, 4]
        latency = self.metrics.calculate_latency(path)
        self.assertGreaterEqual(latency, 0)
    
    def test_hop_count_calculation(self):
        """Test hop count calculation"""
        path = [0, 1, 2, 4]
        hop_count = self.metrics.calculate_hop_count(path)
        self.assertEqual(hop_count, 3)
    
    def test_packet_delivery_ratio(self):
        """Test packet delivery ratio calculation"""
        pdr = self.metrics.calculate_packet_delivery_ratio(8, 10)
        self.assertEqual(pdr, 0.8)
    
    def test_complete_analysis(self):
        """Test complete performance analysis"""
        dijkstra = DijkstraRouting(self.network)
        traffic = TrafficGenerator(self.network, "low")
        flows = traffic.generate_flows(5)
        
        results = self.metrics.analyze_routing_performance(dijkstra, flows)
        
        self.assertIn("algorithm", results)
        self.assertIn("execution_time", results)
        self.assertIn("packet_delivery_ratio", results)
        self.assertGreaterEqual(results["packet_delivery_ratio"], 0)

if __name__ == '__main__':
    unittest.main()
