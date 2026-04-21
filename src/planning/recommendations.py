UPGRADE_STEPS = [50, 100, 250, 500, 1000, 2500, 5000, 10000]


def _next_bandwidth(current_bandwidth):
    for step in UPGRADE_STEPS:
        if current_bandwidth < step:
            return step
    return current_bandwidth * 2


def build_recommendations(network_state, simulation_state):
    recommendations = []
    failure_profile = (network_state or {}).get("failure_profile", {})

    if not simulation_state:
        return recommendations

    if simulation_state.get("mode") == "all":
        scores = simulation_state.get("scores", {})
        comparison = simulation_state.get("comparison", {})
        if scores:
            ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            best_name, best_score = ranked[0]
            recommendations.append(
                {
                    "priority": "high",
                    "title": f"Default to {best_name} for this scenario",
                    "detail": f"It delivered the highest composite score ({best_score:.4f}) for the current topology, traffic, and failure profile.",
                }
            )
        if comparison:
            weakest_name, weakest_metrics = min(
                comparison.items(),
                key=lambda item: (item[1]["packet_delivery_ratio"], -item[1]["average_latency"]),
            )
            recommendations.append(
                {
                    "priority": "medium",
                    "title": f"Avoid {weakest_name} for stressed conditions",
                    "detail": f"It was the weakest option in this run with packet delivery ratio {weakest_metrics['packet_delivery_ratio']:.0%}.",
                }
            )
    else:
        results = simulation_state.get("results", {})
        edge_loads = sorted(results.get("edge_loads", {}).values(), key=lambda item: item["load_ratio"], reverse=True)
        for edge in edge_loads[:3]:
            if edge["load_ratio"] < 0.85:
                break
            target_bandwidth = _next_bandwidth(edge["bandwidth"] * max(1, int(edge["load_ratio"]) + 1))
            recommendations.append(
                {
                    "priority": "high" if edge["load_ratio"] >= 1 else "medium",
                    "title": f"Upgrade edge {edge['u']}-{edge['v']}",
                    "detail": f"Current utilization is {edge['load_ratio']:.2f} on {edge['bandwidth']:.0f} Mbps. Move this link toward {target_bandwidth:.0f} Mbps or split traffic across another path.",
                }
            )

        if results.get("packet_delivery_ratio", 1) < 0.95:
            recommendations.append(
                {
                    "priority": "high",
                    "title": "Reduce packet loss before production rollout",
                    "detail": f"Packet delivery ratio is {results['packet_delivery_ratio']:.0%}. Add capacity, reduce packet-loss zones, or switch to an algorithm that performs better under load.",
                }
            )

        if results.get("congested_edges", 0) == 0 and results.get("average_latency", 0) > 0:
            recommendations.append(
                {
                    "priority": "low",
                    "title": "Preserve headroom with the current topology",
                    "detail": "The run stayed below the congestion threshold, so the current network shape appears healthy for this traffic profile.",
                }
            )

    if failure_profile.get("down_nodes") or failure_profile.get("down_edges"):
        recommendations.append(
            {
                "priority": "medium",
                "title": "Add resilience around failed components",
                "detail": f"Scenario includes {len(failure_profile.get('down_nodes', []))} node failures and {len(failure_profile.get('down_edges', []))} link failures. Add resilience with redundant paths or spare capacity around those assets.",
            }
        )

    if failure_profile.get("maintenance_edges"):
        recommendations.append(
            {
                "priority": "medium",
                "title": "Schedule maintenance with reroute capacity in mind",
                "detail": "Maintenance multipliers are increasing path cost on selected links. Keep alternate paths warm before planned work windows.",
            }
        )

    if failure_profile.get("packet_loss_nodes") or failure_profile.get("packet_loss_edges"):
        recommendations.append(
            {
                "priority": "medium",
                "title": "Target packet-loss zones for remediation",
                "detail": "Packet-loss rules are materially affecting delivery. Inspect hardware health, radio quality, or queue management on those hot spots.",
            }
        )

    return recommendations
