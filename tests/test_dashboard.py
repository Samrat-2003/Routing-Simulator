import json
import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.dashboard.app import (
    build_comparison_histograms,
    build_network,
    merge_failure_profiles,
    render_results,
    serialise_failure_profile,
)


def collect_component_text(component):
    if component is None:
        return []
    if isinstance(component, str):
        return [component]
    if isinstance(component, (int, float)):
        return [str(component)]
    if isinstance(component, (list, tuple)):
        values = []
        for child in component:
            values.extend(collect_component_text(child))
        return values
    return collect_component_text(getattr(component, "children", None))


class TestDashboardScenarioState(unittest.TestCase):
    def test_failure_profile_survives_dash_json_round_trip(self):
        """Stored dashboard failure profiles should rebuild and apply correctly."""
        profile = merge_failure_profiles(
            {
                "down_nodes": [4],
                "down_edges": [(0, 1)],
                "packet_loss_nodes": {2: 0.2},
                "packet_loss_edges": {(1, 2): 0.35},
                "maintenance_edges": {(2, 3): 1.8},
            }
        )
        stored_profile = json.loads(json.dumps(serialise_failure_profile(profile)))

        network = build_network("mesh", 5, 0.3, 7, failure_profile=stored_profile)

        self.assertEqual(network.graph.number_of_nodes(), 4)
        self.assertFalse(network.graph.has_node(4))
        self.assertFalse(network.graph.has_edge(0, 1))
        self.assertEqual(network.graph.nodes[2]["packet_loss"], 0.2)
        self.assertEqual(network.graph[1][2]["packet_loss"], 0.35)
        self.assertEqual(network.graph[2][3]["maintenance_factor"], 1.8)

    def test_failed_topology_rebuild_uses_requested_node_count(self):
        """A failed scenario should redraw from the original topology size."""
        stored_profile = json.loads(
            json.dumps(
                serialise_failure_profile(
                    {
                        "down_nodes": [4],
                        "down_edges": [],
                        "packet_loss_nodes": {},
                        "packet_loss_edges": {},
                        "maintenance_edges": {},
                    }
                )
            )
        )

        first = build_network("mesh", 5, 0.3, 11, failure_profile=stored_profile)
        second = build_network("mesh", 5, 0.3, 11, failure_profile=stored_profile)

        self.assertEqual(first.graph.number_of_nodes(), 4)
        self.assertEqual(second.graph.number_of_nodes(), 4)
        self.assertEqual(first.graph.number_of_edges(), second.graph.number_of_edges())

    def test_all_mode_replaces_single_run_panels(self):
        """ALL mode should show comparison headings instead of single-run panels."""
        simulation_state = {
            "mode": "all",
            "seed": 42,
            "scores": {"Dijkstra": 0.9, "Bellman-Ford": 0.7, "ACO": 0.2, "GA": 0.8},
            "comparison": {
                name: {
                    "packet_delivery_ratio": 0.8,
                    "average_latency": 10 + index,
                    "average_throughput": 20 - index,
                    "max_utilization": 0.5 + index,
                }
                for index, name in enumerate(["Dijkstra", "Bellman-Ford", "ACO", "GA"])
            },
        }

        rendered = render_results(simulation_state, {"failure_profile": {}}, None)
        text = " ".join(collect_component_text(rendered))

        self.assertIn("Algorithm Comparison", text)
        self.assertIn("Metric Histogram", text)
        self.assertIn("Ranking Summary", text)
        self.assertNotIn("Performance Readout", text)
        self.assertNotIn("Flow Narratives", text)

    def test_all_mode_uses_one_grouped_histogram(self):
        """The comparison metrics should be one grouped chart, not five charts."""
        simulation_state = {
            "scores": {"Dijkstra": 0.9, "Bellman-Ford": 0.7, "ACO": 0.2, "GA": 0.8},
            "comparison": {
                name: {
                    "packet_delivery_ratio": 0.8,
                    "average_latency": 10 + index,
                    "average_throughput": 20 - index,
                    "max_utilization": 0.5 + index,
                }
                for index, name in enumerate(["Dijkstra", "Bellman-Ford", "ACO", "GA"])
            },
        }

        graph = build_comparison_histograms(simulation_state)

        self.assertEqual(graph.__class__.__name__, "Graph")
        self.assertEqual(graph.figure.layout.barmode, "group")
        self.assertEqual([trace.name for trace in graph.figure.data], ["Dijkstra", "Bellman-Ford", "ACO", "GA"])


if __name__ == "__main__":
    unittest.main()
