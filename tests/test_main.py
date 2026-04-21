import csv
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from main import build_network, export_results

TEST_OUTPUT_DIR = Path(__file__).resolve().parent / "_tmp"


class TestMainHelpers(unittest.TestCase):
    def setUp(self):
        TEST_OUTPUT_DIR.mkdir(exist_ok=True)

    def test_build_network_supports_mesh_topology(self):
        """CLI network builder should support non-random topologies."""
        network = build_network("mesh", 5, seed=7)
        self.assertEqual(network.graph.number_of_nodes(), 5)
        self.assertEqual(network.graph.number_of_edges(), 10)

    def test_export_single_result_to_json(self):
        """Single-run results should export as JSON."""
        results = {
            "algorithm": "DijkstraRouting",
            "execution_time": 0.01,
            "successful_routes": 4,
            "total_flows": 5,
            "packet_delivery_ratio": 0.8,
            "average_latency": 2.5,
            "average_throughput": 50.0,
            "average_hop_count": 2.0,
            "congestion_simulated": True,
            "paths": [[0, 1, 2]],
        }

        export_path = TEST_OUTPUT_DIR / "results.json"
        export_results(results, export_path)

        with open(export_path, "r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)

        self.assertEqual(payload["algorithm"], "DijkstraRouting")
        self.assertEqual(payload["paths"][0], [0, 1, 2])

    def test_export_comparison_to_csv(self):
        """Comparison results should export as CSV rows."""
        comparison = {
            "Dijkstra": {
                "algorithm": "DijkstraRouting",
                "execution_time": 0.01,
                "successful_routes": 4,
                "total_flows": 5,
                "packet_delivery_ratio": 0.8,
                "average_latency": 2.5,
                "average_throughput": 50.0,
                "average_hop_count": 2.0,
                "congestion_simulated": True,
            },
            "Bellman-Ford": {
                "algorithm": "BellmanFordRouting",
                "execution_time": 0.02,
                "successful_routes": 5,
                "total_flows": 5,
                "packet_delivery_ratio": 1.0,
                "average_latency": 3.0,
                "average_throughput": 40.0,
                "average_hop_count": 2.2,
                "congestion_simulated": True,
            },
        }

        export_path = TEST_OUTPUT_DIR / "comparison.csv"
        export_results(comparison, export_path)

        with open(export_path, "r", encoding="utf-8", newline="") as file_obj:
            rows = list(csv.DictReader(file_obj))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["algorithm_label"], "Dijkstra")
        self.assertIn("packet_delivery_ratio", rows[0])


if __name__ == "__main__":
    unittest.main()
