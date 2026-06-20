import unittest
import sys
import os
from collections import namedtuple
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.network.topology import NetworkTopology
from src.algorithms.routing import DijkstraRouting
from src.traffic.generator import TrafficGenerator
from src.metrics.analyzer import PerformanceMetrics
from src.planning.recommendations import build_recommendations
from src.reporting.exporter import export_simulation_bundle

Flow = namedtuple("Flow", ["source", "destination", "size", "timestamp"])

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

    def test_seeded_traffic_generation_is_reproducible(self):
        """Traffic generation should be reproducible when a seed is provided."""
        first = TrafficGenerator(self.network, "low", seed=99)
        second = TrafficGenerator(self.network, "low", seed=99)

        self.assertEqual(first.generate_flows(5), second.generate_flows(5))

    def test_metrics_history_falls_back_without_pandas(self):
        """Metrics history export should still work if pandas is unavailable."""
        self.metrics.metrics_history.append({"algorithm": "Dijkstra"})
        dataframe_or_history = self.metrics.get_metrics_dataframe()

        if isinstance(dataframe_or_history, list):
            self.assertEqual(dataframe_or_history[0]["algorithm"], "Dijkstra")
        else:
            self.assertEqual(dataframe_or_history.iloc[0]["algorithm"], "Dijkstra")

    def test_congestion_increases_latency_and_reduces_delivery(self):
        """Load on a low-bandwidth path should worsen metrics under congestion."""
        network = NetworkTopology(seed=5)
        network.create_ring_topology(4, seed=5)

        for u, v in network.graph.edges():
            network.graph[u][v]["weight"] = 1
            network.graph[u][v]["base_weight"] = 1
            network.graph[u][v]["bandwidth"] = 100

        network.graph[0][1]["bandwidth"] = 5
        network.graph[1][2]["bandwidth"] = 5

        flows = [
            Flow(0, 2, 4, 0),
            Flow(0, 2, 4, 1),
            Flow(0, 2, 4, 2),
            Flow(0, 2, 4, 3),
        ]

        static_metrics = PerformanceMetrics(network, simulate_congestion=False, seed=7)
        congested_metrics = PerformanceMetrics(network, simulate_congestion=True, seed=7)
        algorithm = DijkstraRouting(network)

        static_results = static_metrics.analyze_routing_performance(algorithm, flows)
        congested_results = congested_metrics.analyze_routing_performance(algorithm, flows)

        self.assertGreater(congested_results["average_latency"], static_results["average_latency"])
        self.assertLessEqual(congested_results["packet_delivery_ratio"], static_results["packet_delivery_ratio"])
        self.assertTrue(congested_results["edge_loads"])
        self.assertEqual(len(congested_results["flow_details"]), len(flows))
        self.assertIn("load_ratio", next(iter(congested_results["edge_loads"].values())))

    def test_edge_loads_include_congestion_packet_loss(self):
        """Serialized edge loads should expose runtime overload drop risk."""
        network = NetworkTopology(seed=5)
        network.create_ring_topology(3, seed=5)

        for u, v in network.graph.edges():
            network.graph[u][v]["weight"] = 100
            network.graph[u][v]["base_weight"] = 100
            network.graph[u][v]["bandwidth"] = 100

        network.graph[0][1]["weight"] = 1
        network.graph[0][1]["base_weight"] = 1
        network.graph[0][1]["bandwidth"] = 5

        flows = [Flow(0, 1, 10, 0)]
        results = PerformanceMetrics(network, simulate_congestion=True, seed=7).analyze_routing_performance(
            DijkstraRouting(network),
            flows,
        )

        self.assertGreater(results["edge_loads"]["0-1"]["packet_loss"], 0)

    def test_loaded_traffic_matrix_creates_multiple_flows(self):
        """Traffic generator should expand demand records into flows."""
        traffic = TrafficGenerator(self.network, "low")
        flows = traffic.load_flows([{"source": 0, "destination": 4, "size": 25, "demand": 3}])

        self.assertEqual(len(flows), 3)
        self.assertEqual(flows[0].size, 25)

    def test_recommendations_prioritise_hot_links(self):
        """Recommendations should flag overloaded links for upgrade."""
        simulation_state = {
            "mode": "single",
            "results": {
                "packet_delivery_ratio": 0.82,
                "congested_edges": 2,
                "average_latency": 12.5,
                "edge_loads": {
                    "1-2": {"u": 1, "v": 2, "bandwidth": 100, "load_ratio": 1.6},
                    "2-3": {"u": 2, "v": 3, "bandwidth": 100, "load_ratio": 0.9},
                },
            },
        }
        network_state = {"failure_profile": {"down_edges": [(1, 4)]}}

        recommendations = build_recommendations(network_state, simulation_state)

        self.assertTrue(any("Upgrade edge 1-2" in item["title"] for item in recommendations))
        self.assertTrue(any("resilience" in item["detail"].lower() for item in recommendations))

    def test_report_export_writes_csv_and_pdf(self):
        """Exporter should create both machine-readable and presentation-friendly reports."""
        output_dir = os.path.join(os.path.dirname(__file__), "tmp_reports")
        simulation_state = {
            "mode": "single",
            "results": {
                "algorithm": "DijkstraRouting",
                "execution_time": 0.1,
                "successful_routes": 4,
                "dropped_flows": 1,
                "total_flows": 5,
                "packet_delivery_ratio": 0.8,
                "average_latency": 3.2,
                "average_throughput": 22.0,
                "average_hop_count": 1.4,
                "average_utilization": 0.55,
                "max_utilization": 1.1,
                "congested_edges": 1,
                "edge_loads": {"0-1": {"u": 0, "v": 1, "load": 110, "bandwidth": 100, "load_ratio": 1.1}},
            },
        }

        bundle = export_simulation_bundle({"source_label": "Imported scenario", "failure_profile": {}}, simulation_state, [], output_dir=output_dir)

        self.assertTrue(os.path.exists(bundle["csv_path"]))
        self.assertTrue(os.path.exists(bundle["pdf_path"]))

if __name__ == '__main__':
    unittest.main()
