import json
import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.dashboard.app import (
    build_comparison_histograms,
    build_network,
    build_network_figure,
    merge_failure_profiles,
    render_results,
    serialise_failure_profile,
    update_network_state,
)
from backend.server import build_network_from_request


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
    def test_generate_network_callback_returns_scenario_state(self):
        """Generating a topology should return a usable network state."""
        status, network_state, report_state = update_network_state(
            1,
            "mesh",
            5,
            0.3,
            None,
            None,
            None,
            0,
            0,
            0,
            0,
            0,
            0.1,
            0.35,
            1.25,
            2.0,
            "",
            "",
            "",
            "",
            "",
        )

        self.assertIn("Mesh ready", status)
        self.assertEqual(network_state["scenario_id"], 1)
        self.assertEqual(network_state["active_node_count"], 5)
        self.assertEqual(network_state["active_edge_count"], 10)
        self.assertIsNone(report_state)

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

    def test_backend_applies_failure_profile_from_dashboard_payload(self):
        """Backend simulations should use the same packet-loss scenario as the graph."""
        stored_profile = json.loads(
            json.dumps(
                serialise_failure_profile(
                    {
                        "down_nodes": [],
                        "down_edges": [],
                        "packet_loss_nodes": {},
                        "packet_loss_edges": {(1, 2): 0.35},
                        "maintenance_edges": {},
                    }
                )
            )
        )

        network = build_network_from_request(
            {
                "topology": "mesh",
                "nodes": 4,
                "edge_prob": 0.3,
                "seed": 3,
                "failure_profile": stored_profile,
            }
        )

        self.assertEqual(network.graph[1][2]["packet_loss"], 0.35)

    def test_edge_hover_prefers_simulation_packet_loss(self):
        """Hovered edge labels should show runtime packet-loss risk when available."""
        network = build_network("mesh", 3, 0.3, 5)

        figure = build_network_figure(
            network,
            "Scenario",
            3,
            {"mode": "single", "edge_loads": {"0-1": {"load_ratio": 1.2, "bandwidth": 50, "packet_loss": 0.42}}},
        )
        hover_texts = []
        for trace in figure.data:
            hover_texts.extend(list(trace.text or []))

        self.assertTrue(any("Edge 0-1" in text and "Packet loss: 0.42" in text for text in hover_texts))

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

    def test_stale_comparison_is_hidden_after_new_scenario(self):
        """Old comparison state should not render after a new network is generated."""
        simulation_state = {
            "mode": "all",
            "scenario_id": 1,
            "seed": 42,
            "scores": {"dijkstra": 0.9},
            "comparison": {
                "dijkstra": {
                    "packet_delivery_ratio": 0.8,
                    "average_latency": 10,
                    "average_throughput": 20,
                    "max_utilization": 0.5,
                }
            },
        }

        rendered = render_results(simulation_state, {"scenario_id": 2, "failure_profile": {}}, None)
        text = " ".join(collect_component_text(rendered))

        self.assertIn("Run a simulation to populate the readout.", text)
        self.assertNotIn("Best overall", text)

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
