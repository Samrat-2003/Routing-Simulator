import base64
import json
import math
import os
import sys
import types
from importlib import metadata
import requests

try:
    import pkg_resources  # noqa: F401
except ModuleNotFoundError:
    from packaging.version import parse as parse_version

    pkg_resources = types.ModuleType("pkg_resources")

    class _Distribution:
        def __init__(self, version):
            self.version = version

    def get_distribution(package_name):
        return _Distribution(metadata.version(package_name))

    pkg_resources.get_distribution = get_distribution
    pkg_resources.parse_version = parse_version
    sys.modules["pkg_resources"] = pkg_resources

import dash
from dash import Input, Output, State, dcc, html
import networkx as nx
import plotly.graph_objs as go

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from src.network.topology import NetworkTopology
from src.planning.recommendations import build_recommendations
from src.reporting.exporter import export_simulation_bundle
from src.dashboard.api_client import simulate,compare,report
from src.dashboard.api_client import recommendations as recommendation_api



app = dash.Dash(__name__)

COLORS = {
    "bg": "#f4efe5",
    "bg_accent": "#efe5d3",
    "surface": "#fffaf2",
    "surface_alt": "#f8f1e4",
    "ink": "#1f2933",
    "muted": "#62707c",
    "line": "#d8c7ab",
    "primary": "#0e7490",
    "primary_dark": "#155e75",
    "success": "#2e7d32",
    "warning": "#f59e0b",
    "danger": "#c2410c",
    "danger_dark": "#9a3412",
    "low": "#a8b5c2",
    "medium": "#f2c14e",
    "heavy": "#f08c2e",
    "overload": "#c2410c",
}

FONT_STACK = "Georgia, Cambria, 'Times New Roman', serif"
SANS_STACK = "'Trebuchet MS', 'Segoe UI', sans-serif"

CARD = {
    "background": COLORS["surface"],
    "border": f"1px solid {COLORS['line']}",
    "borderRadius": "22px",
    "padding": "20px",
    "boxShadow": "0 14px 34px rgba(120, 90, 40, 0.08)",
}
LABEL = {
    "fontWeight": "bold",
    "marginTop": "12px",
    "display": "block",
    "fontFamily": SANS_STACK,
    "fontSize": "13px",
    "letterSpacing": "0.04em",
    "textTransform": "uppercase",
    "color": COLORS["muted"],
}
INPUT_STYLE = {
    "width": "100%",
    "padding": "10px 12px",
    "boxSizing": "border-box",
    "marginTop": "6px",
    "borderRadius": "12px",
    "border": f"1px solid {COLORS['line']}",
    "background": "white",
    "color": COLORS["ink"],
}
BUTTON_STYLE = {
    "marginTop": "16px",
    "width": "100%",
    "padding": "12px 14px",
    "background": f"linear-gradient(135deg, {COLORS['primary']}, {COLORS['primary_dark']})",
    "color": "white",
    "border": "none",
    "borderRadius": "999px",
    "cursor": "pointer",
    "fontWeight": "bold",
    "fontSize": "14px",
    "letterSpacing": "0.02em",
    "boxShadow": "0 10px 24px rgba(14, 116, 144, 0.22)",
}
TH = {
    "borderBottom": f"1px solid {COLORS['line']}",
    "padding": "10px 8px",
    "background": COLORS["surface_alt"],
    "textAlign": "left",
    "fontFamily": SANS_STACK,
    "fontSize": "12px",
    "textTransform": "uppercase",
    "letterSpacing": "0.04em",
    "color": COLORS["muted"],
}
TD = {
    "borderBottom": f"1px solid rgba(216, 199, 171, 0.55)",
    "padding": "10px 8px",
    "color": COLORS["ink"],
}


def _offset_seed(seed, offset):
    return None if seed is None else seed + offset


def metric_chip(title, value, accent):
    return html.Div(
        style={
            "background": "white",
            "border": f"1px solid {COLORS['line']}",
            "borderTop": f"4px solid {accent}",
            "borderRadius": "16px",
            "padding": "12px 14px",
            "minWidth": "120px",
        },
        children=[
            html.Div(title, style={"fontFamily": SANS_STACK, "fontSize": "11px", "color": COLORS["muted"], "textTransform": "uppercase", "letterSpacing": "0.05em"}),
            html.Div(value, style={"fontFamily": FONT_STACK, "fontSize": "24px", "color": COLORS["ink"], "marginTop": "6px", "fontWeight": "bold"}),
        ],
    )


def panel_heading(title, subtitle=None):
    children = [
        html.H3(title, style={"margin": "0", "fontFamily": FONT_STACK, "fontSize": "28px", "color": COLORS["ink"]}),
    ]
    if subtitle:
        children.append(html.P(subtitle, style={"margin": "6px 0 0", "color": COLORS["muted"], "fontFamily": SANS_STACK, "fontSize": "14px"}))
    return html.Div(children=children, style={"marginBottom": "14px"})


def empty_figure(message="Generate or import a network to begin"):
    return go.Figure(
        layout=go.Layout(
            title=dict(text=message, font=dict(family=FONT_STACK, size=22, color=COLORS["ink"])),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(b=10, l=5, r=5, t=60),
        )
    )


def edge_style(stress_score):
    if stress_score >= 0.85:
        return COLORS["overload"], 5.2
    if stress_score >= 0.6:
        return COLORS["heavy"], 4.3
    if stress_score >= 0.3:
        return COLORS["medium"], 3.2
    return COLORS["low"], 1.8


def display_stress_score(load_ratio, max_load_ratio):
    if load_ratio <= 0:
        return 0.0

    capped_max = max(1.0, float(max_load_ratio or 0.0))
    # Compress very large overload values so the graph shows a useful spread
    # instead of collapsing into only gray and red.
    return min(1.0, math.log1p(load_ratio) / math.log1p(capped_max))


def parse_number(value):
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return value


def parse_node_list(text):
    nodes = []
    for chunk in (text or "").split(","):
        item = chunk.strip()
        if not item:
            continue
        nodes.append(parse_number(item))
    return nodes


def parse_edge_pairs(text):
    edges = []
    for chunk in (text or "").split(","):
        item = chunk.strip()
        if "-" not in item:
            continue
        left, right = [part.strip() for part in item.split("-", 1)]
        edges.append((parse_number(left), parse_number(right)))
    return edges


def edge_storage_key(edge):
    u, v = edge
    return json.dumps([u, v], separators=(",", ":"))


def edge_from_storage_key(key):
    if isinstance(key, (list, tuple)) and len(key) == 2:
        return key[0], key[1]
    if isinstance(key, str):
        try:
            decoded = json.loads(key)
            if isinstance(decoded, list) and len(decoded) == 2:
                return decoded[0], decoded[1]
        except json.JSONDecodeError:
            pass
        if "-" in key:
            left, right = [part.strip() for part in key.split("-", 1)]
            return parse_number(left), parse_number(right)
    return key


def normalise_edge_map(edge_map):
    normalised = {}
    for edge, value in (edge_map or {}).items():
        normalised[edge_from_storage_key(edge)] = value
    return normalised


def normalise_node_map(node_map):
    normalised = {}
    for node, value in (node_map or {}).items():
        normalised[parse_number(node)] = value
    return normalised


def serialise_failure_profile(profile):
    profile = profile or {}
    return {
        "down_nodes": list(profile.get("down_nodes", [])),
        "down_edges": [list(edge_from_storage_key(edge)) for edge in profile.get("down_edges", [])],
        "packet_loss_nodes": profile.get("packet_loss_nodes", {}),
        "packet_loss_edges": {edge_storage_key(edge_from_storage_key(edge)): value for edge, value in (profile.get("packet_loss_edges") or {}).items()},
        "maintenance_edges": {edge_storage_key(edge_from_storage_key(edge)): value for edge, value in (profile.get("maintenance_edges") or {}).items()},
    }


def deserialise_failure_profile(profile):
    profile = profile or {}
    return {
        "down_nodes": list(profile.get("down_nodes", [])),
        "down_edges": [edge_from_storage_key(edge) for edge in profile.get("down_edges", [])],
        "packet_loss_nodes": normalise_node_map(profile.get("packet_loss_nodes")),
        "packet_loss_edges": normalise_edge_map(profile.get("packet_loss_edges")),
        "maintenance_edges": normalise_edge_map(profile.get("maintenance_edges")),
    }


def parse_scored_edges(text):
    values = {}
    for chunk in (text or "").split(","):
        item = chunk.strip()
        if ":" not in item or "-" not in item:
            continue
        edge_text, value_text = [part.strip() for part in item.split(":", 1)]
        left, right = [part.strip() for part in edge_text.split("-", 1)]
        try:
            values[(parse_number(left), parse_number(right))] = float(value_text)
        except ValueError:
            continue
    return values


def parse_node_scores(text):
    values = {}
    for chunk in (text or "").split(","):
        item = chunk.strip()
        if ":" not in item:
            continue
        node_text, value_text = [part.strip() for part in item.split(":", 1)]
        try:
            values[parse_number(node_text)] = float(value_text)
        except ValueError:
            continue
    return values


def build_manual_failure_profile(down_nodes, down_edges, packet_loss_edges, packet_loss_nodes, maintenance_edges):
    return {
        "down_nodes": parse_node_list(down_nodes),
        "down_edges": parse_edge_pairs(down_edges),
        "packet_loss_edges": parse_scored_edges(packet_loss_edges),
        "packet_loss_nodes": parse_node_scores(packet_loss_nodes),
        "maintenance_edges": parse_scored_edges(maintenance_edges),
    }


def _decode_upload(contents):
    _, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)
    return decoded.decode("utf-8")


def _csv_records(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = [item.strip() for item in lines[0].split(",")]
    records = []
    for line in lines[1:]:
        parts = [item.strip() for item in line.split(",")]
        records.append(dict(zip(header, parts)))
    return records


def merge_import_records(files):
    merged = {"nodes": [], "edges": [], "flows": []}
    notes = []

    for file_name, contents in files:
        text = _decode_upload(contents)
        lower_name = file_name.lower()
        if lower_name.endswith(".json"):
            payload = json.loads(text)
            merged["nodes"].extend(payload.get("nodes", []))
            merged["edges"].extend(payload.get("edges", []))
            merged["flows"].extend(payload.get("flows", payload.get("traffic_matrix", [])))
            notes.append(f"{file_name}: JSON scenario loaded")
            continue

        records = _csv_records(text)
        if not records:
            continue
        columns = set(records[0].keys())
        if {"source", "target"} <= columns:
            merged["edges"].extend(records)
            notes.append(f"{file_name}: edge list loaded")
        elif {"source", "destination"} <= columns:
            merged["flows"].extend(records)
            notes.append(f"{file_name}: traffic data loaded")
        elif {"id"} <= columns or {"node_id"} <= columns:
            merged["nodes"].extend(records)
            notes.append(f"{file_name}: node list loaded")

    return merged, notes


def build_network(topology_type, node_count, edge_prob, seed, import_data=None, failure_profile=None):
    network = NetworkTopology(seed=seed)
    if import_data and import_data.get("edges"):
        network.load_from_data(import_data.get("nodes"), import_data.get("edges"), seed=seed)
    else:
        builders = {
            "mesh": lambda: network.create_mesh_topology(node_count, seed=seed),
            "random": lambda: network.create_random_topology(node_count, edge_prob, seed=seed),
            "ring": lambda: network.create_ring_topology(node_count, seed=seed),
            "star": lambda: network.create_star_topology(node_count, seed=seed),
        }
        builders[topology_type]()

    network.apply_failure_profile(deserialise_failure_profile(failure_profile))
    return network


def merge_failure_profiles(*profiles):
    merged = {
        "down_nodes": [],
        "down_edges": [],
        "packet_loss_nodes": {},
        "packet_loss_edges": {},
        "maintenance_edges": {},
    }

    for profile in profiles:
        if not profile:
            continue
        normalised = deserialise_failure_profile(profile)
        merged["down_nodes"].extend(normalised.get("down_nodes", []))
        merged["down_edges"].extend(normalised.get("down_edges", []))
        merged["packet_loss_nodes"].update(normalised.get("packet_loss_nodes", {}))
        merged["packet_loss_edges"].update(normalised.get("packet_loss_edges", {}))
        merged["maintenance_edges"].update(normalised.get("maintenance_edges", {}))

    merged["down_nodes"] = list(dict.fromkeys(merged["down_nodes"]))
    merged["down_edges"] = list(dict.fromkeys(edge_from_storage_key(edge) for edge in merged["down_edges"]))
    return merged


def get_recommendations(network_state, simulation_state):
    payload = {
        "network_state": network_state,
        "simulation_state": simulation_state,
    }
    try:
        return recommendation_api(payload)
    except requests.RequestException:
        return build_recommendations(network_state, simulation_state)


def is_simulation_current(network_state, simulation_state):
    if not network_state or not simulation_state:
        return False

    network_scenario = network_state.get("scenario_id")
    simulation_scenario = simulation_state.get("scenario_id")
    if network_scenario is None or simulation_scenario is None:
        return True

    return network_scenario == simulation_scenario

def build_network_figure(network, title_label, node_count, simulation_state=None):
    if network is None or network.graph.number_of_nodes() == 0:
        return empty_figure()

    graph = network.graph
    pos = nx.spring_layout(graph, seed=42)
    edge_loads = simulation_state.get("edge_loads", {}) if simulation_state else {}
    max_load_ratio = max(
        (edge.get("load_ratio", 0) for edge in edge_loads.values()),
        default=0,
    )
    traces = []
    hover_x = []
    hover_y = []
    hover_texts = []

    for u, v in graph.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_key = f"{min(u, v)}-{max(u, v)}"
        edge_data = edge_loads.get(edge_key, {})
        load_ratio = edge_data.get("load_ratio", 0)
        bandwidth = edge_data.get("bandwidth", graph[u][v].get("bandwidth", 0))
        packet_loss = edge_data.get("packet_loss", graph[u][v].get("packet_loss", 0))
        stress_score = display_stress_score(load_ratio, max_load_ratio)
        color, width = edge_style(stress_score)
        hover_text = (
            f"<b>Edge {u}-{v}</b><br>"
            f"Current weight: {graph[u][v].get('weight', 1):.2f}<br>"
            f"Bandwidth: {bandwidth}<br>"
            f"Load ratio: {load_ratio:.2f}<br>"
            f"Display stress: {stress_score:.2f}<br>"
            f"Packet loss: {packet_loss:.2f}"
        )
        traces.append(
            go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(width=width, color=color),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        hover_x.append((x0 + x1) / 2)
        hover_y.append((y0 + y1) / 2)
        hover_texts.append(hover_text)

    traces.append(
        go.Scatter(
            x=hover_x,
            y=hover_y,
            mode="markers",
            marker=dict(size=18, color="rgba(0,0,0,0)"),
            hovertemplate="%{text}<extra></extra>",
            text=hover_texts,
            showlegend=False,
        )
    )

    show_labels = node_count <= 30
    traces.append(
        go.Scatter(
            x=[pos[node][0] for node in graph.nodes()],
            y=[pos[node][1] for node in graph.nodes()],
            mode="markers+text" if show_labels else "markers",
            text=[f"{node}" for node in graph.nodes()],
            textposition="middle center",
            hovertemplate="Node %{text}<extra></extra>",
            marker=dict(
                size=18 if show_labels else 10,
                color=COLORS["primary"],
                line=dict(width=2, color=COLORS["primary_dark"]),
            ),
            textfont=dict(family=SANS_STACK, color="white", size=11),
            showlegend=False,
        )
    )

    title = title_label
    if simulation_state and simulation_state.get("mode") == "single":
        title += f" | {simulation_state.get('algorithm_label', 'Simulation')} overlay"
    elif simulation_state and simulation_state.get("mode") == "all":
        title += " | comparison mode"

    return go.Figure(
        data=traces,
        layout=go.Layout(
            title=dict(text=title, font=dict(family=FONT_STACK, size=24, color=COLORS["ink"])),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=10, l=5, r=5, t=60),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )


def build_link_stress_legend():
    items = [
        ("Lowest stress in this run stays gray", COLORS["low"]),
        ("Moderate stress turns yellow", COLORS["medium"]),
        ("Heavy stress turns orange", COLORS["heavy"]),
        ("Highest stress turns red", COLORS["overload"]),
    ]
    return html.Div(
        style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(170px, 1fr))", "gap": "10px", "marginTop": "10px"},
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "background": "white", "border": f"1px solid {COLORS['line']}", "borderRadius": "999px", "padding": "8px 12px"},
                children=[
                    html.Span(style={"display": "inline-block", "width": "18px", "height": "6px", "borderRadius": "999px", "background": color}),
                    html.Span(label, style={"fontFamily": SANS_STACK, "fontSize": "12px", "color": COLORS["muted"]}),
                ],
            )
            for label, color in items
        ],
    )


def build_edge_load_panel(simulation_state):
    edge_loads = simulation_state.get("edge_loads", {})
    if not edge_loads:
        return html.P("Run a single algorithm to inspect stressed links.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK})

    sorted_edges = sorted(edge_loads.values(), key=lambda item: item["load_ratio"], reverse=True)[:8]
    header = html.Thead(html.Tr([html.Th(col, style=TH) for col in ["Edge", "Load", "Bandwidth", "Load Ratio", "Weight"]]))
    rows = []
    for edge in sorted_edges:
        row_style = {**TD}
        if edge["load_ratio"] >= 1.0:
            row_style = {**TD, "background": "#fff1ea"}
        elif edge["load_ratio"] >= 0.75:
            row_style = {**TD, "background": "#fff6e5"}
        rows.append(
            html.Tr(
                [
                    html.Td(f"{edge['u']} - {edge['v']}", style=row_style),
                    html.Td(f"{edge['load']}", style=row_style),
                    html.Td(f"{edge['bandwidth']}", style=row_style),
                    html.Td(f"{edge['load_ratio']:.2f}", style=row_style),
                    html.Td(f"{edge['weight']:.2f}", style=row_style),
                ]
            )
        )

    return html.Div(
        children=[
            html.Div("Hot Links", style={"fontFamily": FONT_STACK, "fontSize": "24px", "margin": "20px 0 8px", "color": COLORS["ink"]}),
            html.Table([header, html.Tbody(rows)], style={"width": "100%", "borderCollapse": "collapse", "background": "white", "borderRadius": "14px", "overflow": "hidden"}),
        ]
    )


def build_flow_details_panel(flow_details):
    if not flow_details:
        return html.P("No flow details available yet.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK})

    header = html.Thead(html.Tr([html.Th(col, style=TH) for col in ["Flow", "Size", "Status", "Latency", "Throughput", "Path"]]))
    rows = []
    for flow in flow_details[:8]:
        status_style = {**TD, "background": "#edf8ed", "color": COLORS["success"], "fontWeight": "bold"} if flow["delivered"] else {**TD, "background": "#fff1ea", "color": COLORS["danger_dark"], "fontWeight": "bold"}
        path_text = " -> ".join(map(str, flow["path"])) if flow["path"] else "No path"
        rows.append(
            html.Tr(
                [
                    html.Td(f"{flow['source']} to {flow['destination']}", style=TD),
                    html.Td(f"{flow['packet_size']} KB", style=TD),
                    html.Td("Delivered" if flow["delivered"] else "Dropped", style=status_style),
                    html.Td("-" if flow["latency"] is None else f"{flow['latency']:.2f}", style=TD),
                    html.Td("-" if flow["throughput"] is None else f"{flow['throughput']:.2f}", style=TD),
                    html.Td(path_text, style=TD),
                ]
            )
        )

    return html.Div(
        children=[
            html.P(f"Showing the first {min(8, len(flow_details))} of {len(flow_details)} traffic flows.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK, "fontSize": "13px"}),
            html.Table([header, html.Tbody(rows)], style={"width": "100%", "borderCollapse": "collapse", "background": "white", "borderRadius": "14px", "overflow": "hidden"}),
        ]
    )


def build_metrics_panel(results, seed):
    return html.Div(
        children=[
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(120px, 1fr))", "gap": "12px", "marginBottom": "16px"},
                children=[
                    metric_chip("Algorithm", results["algorithm"].replace("Routing", ""), COLORS["primary"]),
                    metric_chip("PDR", f"{results['packet_delivery_ratio']:.0%}", COLORS["success"]),
                    metric_chip("Latency", f"{results['average_latency']:.2f}", COLORS["warning"]),
                    metric_chip("Max Util", f"{results['max_utilization']:.2f}", COLORS["danger"]),
                ],
            ),
            html.Table(
                [html.Tbody([
                    html.Tr([html.Td("Execution Time", style=TH), html.Td(f"{results['execution_time']:.4f} s", style=TD)]),
                    html.Tr([html.Td("Successful Routes", style=TH), html.Td(f"{results['successful_routes']} / {results['total_flows']}", style=TD)]),
                    html.Tr([html.Td("Dropped Flows", style=TH), html.Td(f"{results['dropped_flows']}", style=TD)]),
                    html.Tr([html.Td("Average Throughput", style=TH), html.Td(f"{results['average_throughput']:.2f}", style=TD)]),
                    html.Tr([html.Td("Average Hop Count", style=TH), html.Td(f"{results['average_hop_count']:.2f}", style=TD)]),
                    html.Tr([html.Td("Congested Edges", style=TH), html.Td(f"{results['congested_edges']}", style=TD)]),
                    html.Tr([html.Td("Seed", style=TH), html.Td(seed if seed is not None else "random", style=TD)]),
                ])],
                style={"width": "100%", "borderCollapse": "collapse", "background": "white", "borderRadius": "14px", "overflow": "hidden"},
            ),
        ]
    )


def build_comparison_panel(simulation_state):
    comparison = simulation_state.get("comparison", {})
    scores = simulation_state.get("scores", {})
    if not comparison:
        return html.P("Select ALL to compare every algorithm.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK})

    ranking = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_name = ranking[0][0]
    header = html.Thead(html.Tr([html.Th(column, style=TH) for column in ["Algorithm", "Score", "PDR", "Latency", "Throughput", "Max Util"]]))
    rows = []
    for name, score in ranking:
        metrics = comparison[name]
        style = {**TD}
        if name == best_name:
            style = {**TD, "background": "#edf8ed", "fontWeight": "bold"}
        rows.append(
            html.Tr(
                [
                    html.Td(name, style=style),
                    html.Td(f"{score:.4f}", style=style),
                    html.Td(f"{metrics['packet_delivery_ratio']:.2%}", style=style),
                    html.Td(f"{metrics['average_latency']:.2f}", style=style),
                    html.Td(f"{metrics['average_throughput']:.2f}", style=style),
                    html.Td(f"{metrics['max_utilization']:.2f}", style=style),
                ]
            )
        )

    return html.Div(
        children=[
            html.Div(
                style={"display": "inline-block", "padding": "10px 14px", "borderRadius": "999px", "background": "#edf8ed", "color": COLORS["success"], "fontFamily": SANS_STACK, "fontWeight": "bold", "marginBottom": "12px"},
                children=f"Best overall: {best_name} ({scores[best_name]:.4f})",
            ),
            html.Table([header, html.Tbody(rows)], style={"width": "100%", "borderCollapse": "collapse", "background": "white", "borderRadius": "14px", "overflow": "hidden"}),
        ]
    )


def build_comparison_histograms(simulation_state):
    comparison = simulation_state.get("comparison", {})
    scores = simulation_state.get("scores", {})
    if not comparison:
        return html.P("Run ALL mode to plot comparison metrics.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK})

    names = list(comparison.keys())
    metrics = ["Score", "PDR", "Latency", "Throughput", "Max Util"]
    colors = [COLORS["primary"], COLORS["success"], COLORS["warning"], COLORS["danger"]]

    figure = go.Figure()
    for index, name in enumerate(names):
        values = [
            scores.get(name, 0),
            comparison[name]["packet_delivery_ratio"] * 100,
            comparison[name]["average_latency"],
            comparison[name]["average_throughput"],
            comparison[name]["max_utilization"],
        ]
        figure.add_trace(
            go.Bar(
                name=name,
                x=metrics,
                y=values,
                marker=dict(color=colors[index % len(colors)]),
                text=values,
                texttemplate="%{text:.2f}",
                textposition="outside",
                hovertemplate="%{x}: %{y:.2f}<extra>" + name + "</extra>",
            )
        )

    figure.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        margin=dict(l=44, r=16, t=18, b=58),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0, font=dict(family=SANS_STACK, size=11)),
        xaxis=dict(tickfont=dict(family=SANS_STACK, size=11), fixedrange=True),
        yaxis=dict(tickfont=dict(family=SANS_STACK, size=10), fixedrange=True, rangemode="tozero", title=dict(text="Metric value", font=dict(family=SANS_STACK, size=11))),
        uniformtext=dict(mode="hide", minsize=9),
    )

    return dcc.Graph(
        figure=figure,
        config={"displayModeBar": False},
        style={"height": "430px", "minWidth": "0"},
    )


def build_comparison_summary_panel(simulation_state):
    scores = simulation_state.get("scores", {})
    if not scores:
        return html.P("Run ALL mode to see the best scoring algorithm.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK})

    ranking = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return html.Div(
        children=[
            metric_chip("Leader", ranking[0][0], COLORS["success"]),
            html.Div(
                style={"marginTop": "12px", "display": "grid", "gap": "8px"},
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "gap": "12px", "background": "white", "border": f"1px solid {COLORS['line']}", "borderRadius": "14px", "padding": "10px 12px", "fontFamily": SANS_STACK},
                        children=[
                            html.Span(f"{index + 1}. {name}", style={"fontWeight": "bold", "color": COLORS["ink"]}),
                            html.Span(f"{score:.4f}", style={"color": COLORS["muted"]}),
                        ],
                    )
                    for index, (name, score) in enumerate(ranking)
                ],
            ),
        ]
    )


def build_recommendations_panel(recommendations, report_state):
    if not recommendations:
        recommendations = [{"priority": "low", "title": "Run a scenario", "detail": "Recommendations appear after you simulate a real or generated network."}]

    cards = []
    for item in recommendations:
        border = COLORS["success"] if item["priority"] == "low" else COLORS["warning"] if item["priority"] == "medium" else COLORS["danger"]
        cards.append(
            html.Div(
                style={"background": "white", "borderLeft": f"4px solid {border}", "borderRadius": "14px", "padding": "12px 14px", "marginBottom": "10px"},
                children=[
                    html.Div(item["title"], style={"fontFamily": SANS_STACK, "fontWeight": "bold", "color": COLORS["ink"]}),
                    html.P(item["detail"], style={"margin": "6px 0 0", "fontFamily": SANS_STACK, "fontSize": "13px", "color": COLORS["muted"]}),
                ],
            )
        )

    export_note = html.P("Export a report after running a scenario.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK, "fontSize": "13px"})
    if report_state:
        export_note = html.Div(
            [
                html.Div("Reports written to:", style={"fontFamily": SANS_STACK, "fontWeight": "bold", "marginBottom": "6px"}),
                html.Div(report_state["csv_path"], style={"fontFamily": SANS_STACK, "fontSize": "12px"}),
                html.Div(report_state["pdf_path"], style={"fontFamily": SANS_STACK, "fontSize": "12px"}),
            ],
            style={"background": "#eef9fc", "borderRadius": "14px", "padding": "12px 14px", "marginTop": "12px", "color": COLORS["primary_dark"]},
        )

    return html.Div(cards + [export_note])


app.layout = html.Div(
    style={
        "background": f"radial-gradient(circle at top left, {COLORS['bg_accent']} 0%, {COLORS['bg']} 42%, #f7f2ea 100%)",
        "minHeight": "100vh",
        "padding": "24px",
        "color": COLORS["ink"],
    },
    children=[
        dcc.Store(id="import-state"),
        dcc.Store(id="network-state"),
        dcc.Store(id="simulation-state"),
        dcc.Store(id="report-state"),
        html.Div(
            style={"maxWidth": "1520px", "margin": "0 auto"},
            children=[
                html.Div(
                    style={**CARD, "padding": "28px 28px 22px", "background": "linear-gradient(135deg, #fff8ee 0%, #f8efdf 100%)", "marginBottom": "18px"},
                    children=[
                        html.Div("Routing Simulator", style={"fontFamily": SANS_STACK, "fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.16em", "color": COLORS["primary"]}),
                        html.H1("Network Routing Command Deck", style={"fontFamily": FONT_STACK, "fontSize": "48px", "lineHeight": "1", "margin": "10px 0 10px", "color": COLORS["ink"]}),
                        html.P(
                            "Import a real scenario or generate one, inject failures, inspect capacity stress, and export a planning report.",
                            style={"fontFamily": SANS_STACK, "fontSize": "17px", "color": COLORS["muted"], "maxWidth": "820px", "margin": "0"},
                        ),
                    ],
                ),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))", "gap": "16px", "marginBottom": "18px"},
                    children=[
                        html.Div(
                            style=CARD,
                            children=[
                                panel_heading("Topology", "Upload a scenario or generate one from scratch."),
                                dcc.Upload(
                                    id="scenario-upload",
                                    children=html.Div("Drop JSON/CSV files here or click to upload"),
                                    multiple=True,
                                    style={"width": "100%", "padding": "18px", "borderRadius": "16px", "border": f"2px dashed {COLORS['line']}", "textAlign": "center", "fontFamily": SANS_STACK, "color": COLORS["muted"], "background": "white"},
                                ),
                                html.Div(id="import-status", style={"marginTop": "10px", "fontFamily": SANS_STACK, "fontSize": "13px", "color": COLORS["muted"]}),
                                html.Label("Topology Type", style=LABEL),
                                dcc.Dropdown(
                                    id="topology-type",
                                    options=[
                                        {"label": "Mesh (fully connected)", "value": "mesh"},
                                        {"label": "Random (Erdos-Renyi)", "value": "random"},
                                        {"label": "Ring", "value": "ring"},
                                        {"label": "Star", "value": "star"},
                                    ],
                                    value="random",
                                    clearable=False,
                                    style={"marginTop": "6px"},
                                ),
                                html.Label("Number of Nodes", style=LABEL),
                                dcc.Input(id="node-count", type="number", value=20, min=2, max=200, step=1, style=INPUT_STYLE),
                                html.Div(
                                    id="edge-prob-container",
                                    children=[
                                        html.Label("Edge Probability", style=LABEL),
                                        dcc.Input(id="edge-prob", type="number", value=0.3, min=0.1, max=0.8, step=0.05, style=INPUT_STYLE),
                                    ],
                                ),
                                html.Label("Random Seed", style=LABEL),
                                dcc.Input(id="random-seed", type="number", value=42, step=1, style=INPUT_STYLE),
                                html.Button("Build Scenario", id="generate-network", n_clicks=0, style=BUTTON_STYLE),
                                html.Div(id="network-status", style={"marginTop": "12px", "fontFamily": SANS_STACK, "fontSize": "13px", "color": COLORS["muted"]}),
                            ],
                        ),
                        html.Div(
                            style=CARD,
                            children=[
                                panel_heading("Failures", "Model outages, packet-loss zones, and maintenance penalties."),
                                html.Label("Failure Mode", style=LABEL),
                                dcc.Checklist(
                                    id="random-failure-mode",
                                    options=[{"label": "Randomize failures from the current topology", "value": "on"}],
                                    value=[],
                                    style={"marginTop": "8px", "fontFamily": SANS_STACK, "color": COLORS["ink"]},
                                ),
                                html.Div(
                                    id="random-failure-container",
                                    style={"display": "none", "marginBottom": "12px"},
                                    children=[
                                        html.Label("Random Down Nodes", style=LABEL),
                                        dcc.Input(id="random-down-node-count", type="number", value=0, min=0, step=1, style=INPUT_STYLE),
                                        html.Label("Random Down Edges", style=LABEL),
                                        dcc.Input(id="random-down-edge-count", type="number", value=0, min=0, step=1, style=INPUT_STYLE),
                                        html.Label("Random Packet Loss Nodes", style=LABEL),
                                        dcc.Input(id="random-loss-node-count", type="number", value=0, min=0, step=1, style=INPUT_STYLE),
                                        html.Label("Random Packet Loss Edges", style=LABEL),
                                        dcc.Input(id="random-loss-edge-count", type="number", value=0, min=0, step=1, style=INPUT_STYLE),
                                        html.Label("Random Maintenance Edges", style=LABEL),
                                        dcc.Input(id="random-maintenance-edge-count", type="number", value=0, min=0, step=1, style=INPUT_STYLE),
                                        html.Label("Random Packet Loss Range", style=LABEL),
                                        html.Div(
                                            style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "10px"},
                                            children=[
                                                dcc.Input(id="random-loss-min", type="number", value=0.1, min=0, max=1, step=0.05, style=INPUT_STYLE),
                                                dcc.Input(id="random-loss-max", type="number", value=0.35, min=0, max=1, step=0.05, style=INPUT_STYLE),
                                            ],
                                        ),
                                        html.Label("Random Maintenance Range", style=LABEL),
                                        html.Div(
                                            style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "10px"},
                                            children=[
                                                dcc.Input(id="random-maintenance-min", type="number", value=1.25, min=1, step=0.05, style=INPUT_STYLE),
                                                dcc.Input(id="random-maintenance-max", type="number", value=2.0, min=1, step=0.05, style=INPUT_STYLE),
                                            ],
                                        ),
                                    ],
                                ),
                                html.Label("Down Nodes", style=LABEL),
                                dcc.Input(id="down-nodes", type="text", placeholder="e.g. 3, 7", style=INPUT_STYLE),
                                html.Label("Down Edges", style=LABEL),
                                dcc.Input(id="down-edges", type="text", placeholder="e.g. 1-2, 3-4", style=INPUT_STYLE),
                                html.Label("Packet Loss Edges", style=LABEL),
                                dcc.Input(id="packet-loss-edges", type="text", placeholder="e.g. 2-4:0.25, 4-6:0.4", style=INPUT_STYLE),
                                html.Label("Packet Loss Nodes", style=LABEL),
                                dcc.Input(id="packet-loss-nodes", type="text", placeholder="e.g. 5:0.1, 8:0.2", style=INPUT_STYLE),
                                html.Label("Maintenance Edges", style=LABEL),
                                dcc.Input(id="maintenance-edges", type="text", placeholder="e.g. 1-3:1.8, 2-5:1.4", style=INPUT_STYLE),
                            ],
                        ),
                        html.Div(
                            style=CARD,
                            children=[
                                panel_heading("Traffic", "Tune traffic pressure and capacity-aware congestion behavior."),
                                html.Label("Traffic Intensity", style=LABEL),
                                dcc.Dropdown(
                                    id="traffic-intensity",
                                    options=[
                                        {"label": "Low (10 flows)", "value": "low"},
                                        {"label": "Medium (20 flows)", "value": "medium"},
                                        {"label": "High (40 flows)", "value": "high"},
                                        {"label": "Custom", "value": "custom"},
                                    ],
                                    value="medium",
                                    clearable=False,
                                    style={"marginTop": "6px"},
                                ),
                                html.Div(
                                    id="custom-flow-container",
                                    style={"display": "none"},
                                    children=[
                                        html.Label("Number of Flows", style=LABEL),
                                        dcc.Input(id="flow-count", type="number", value=20, min=1, max=1000, step=1, style=INPUT_STYLE),
                                    ],
                                ),
                                html.Label("Congestion Simulation", style=LABEL),
                                html.Div(
                                    style={"display": "flex", "alignItems": "center", "gap": "10px", "marginTop": "8px"},
                                    children=[
                                        dcc.Checklist(
                                            id="congestion-mode",
                                            options=[{"label": "", "value": "on"}],
                                            value=["on"],
                                            inputStyle={"width": "38px", "height": "22px", "cursor": "pointer", "accentColor": COLORS["primary"]},
                                        ),
                                        html.Span(id="congestion-toggle-label", style={"fontFamily": SANS_STACK, "fontSize": "13px", "fontWeight": "bold", "color": COLORS["primary"]}, children="ON"),
                                    ],
                                ),
                                html.Div(
                                    id="congestion-info",
                                    style={"fontSize": "12px", "color": COLORS["primary_dark"], "marginTop": "10px", "fontFamily": SANS_STACK, "padding": "10px 12px", "background": "#eef9fc", "borderRadius": "14px", "borderLeft": f"4px solid {COLORS['primary']}"},
                                    children="Active: link delay and drop risk scale with load relative to bandwidth, plus any packet-loss profile you apply.",
                                ),
                            ],
                        ),
                        html.Div(
                            style=CARD,
                            children=[
                                panel_heading("Algorithms", "Run one strategy or compare the full set."),
                                html.Label("Algorithm", style=LABEL),
                                dcc.Dropdown(
                                    id="algorithm-type",
                                    options=[
                                        {"label": "Dijkstra (shortest path)", "value": "dijkstra"},
                                        {"label": "Bellman-Ford (distributed SP)", "value": "bellman_ford"},
                                        {"label": "PCA-MR (proposed congestion-aware)", "value": "pca_mr"},
                                        {"label": "ACO (Ant Colony Optimization)", "value": "aco"},
                                        {"label": "GA (Genetic Algorithm)", "value": "ga"},
                                        {"label": "ALL - compare every algorithm", "value": "all"},
                                    ],
                                    value="dijkstra",
                                    clearable=False,
                                    style={"marginTop": "6px"},
                                ),
                                html.Div(
                                    style={"display": "grid", "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "gap": "10px", "marginTop": "16px"},
                                    children=[
                                        metric_chip("Import", "JSON / CSV", COLORS["warning"]),
                                        metric_chip("Export", "PDF / CSV", COLORS["primary"]),
                                    ],
                                ),
                                html.Button("Run Simulation", id="run-simulation", n_clicks=0, style={**BUTTON_STYLE, "marginTop": "18px"}),
                                html.Button("Export Report", id="export-report", n_clicks=0, style={**BUTTON_STYLE, "marginTop": "10px", "background": f"linear-gradient(135deg, {COLORS['danger']}, {COLORS['danger_dark']})"}),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "minmax(0, 1.35fr) minmax(340px, 0.9fr)", "gap": "16px", "marginBottom": "18px"},
                    children=[
                        html.Div(
                            style={**CARD, "overflow": "hidden"},
                            children=[
                                panel_heading("Live Topology", "After a single algorithm run, the graph scales link stress from gray through red so overloaded runs still show useful differences."),
                                dcc.Graph(id="network-graph", figure=empty_figure(), style={"height": "520px"}, config={"displayModeBar": False}),
                                build_link_stress_legend(),
                            ],
                        ),
                        html.Div(
                            style=CARD,
                            children=[
                                html.Div(id="metrics-panel-heading", children=panel_heading("Performance Readout", "The metrics update after each simulation run.")),
                                html.Div(id="metrics-display", style={"fontSize": "14px"}),
                                html.Div(id="edge-load-display", style={"fontSize": "13px"}),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={"display": "grid", "gridTemplateColumns": "repeat(3, minmax(0, 1fr))", "gap": "16px"},
                    children=[
                        html.Div(
                            style=CARD,
                            children=[
                                html.Div(id="paths-panel-heading", children=panel_heading("Flow Narratives", "Inspect the first few traffic flows to see who gets through and who gets dropped.")),
                                html.Div(id="paths-display", style={"fontSize": "13px"}),
                            ],
                        ),
                        html.Div(
                            style=CARD,
                            children=[
                                html.Div(id="comparison-panel-heading", children=panel_heading("Algorithm Comparison", "Use ALL mode to rank the routing strategies.")),
                                html.Div(id="comparison-results", style={"fontSize": "14px"}),
                            ],
                        ),
                        html.Div(
                            style=CARD,
                            children=[
                                panel_heading("Recommendations", "Turn raw metrics into practical next steps."),
                                html.Div(id="recommendations-display", style={"fontSize": "14px"}),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("import-status", "children"),
    Output("import-state", "data"),
    Input("scenario-upload", "filename"),
    Input("scenario-upload", "contents"),
    prevent_initial_call=True,
)
def load_imported_scenario(file_names, file_contents):
    if not file_names or not file_contents:
        return "No scenario uploaded yet.", None

    merged, notes = merge_import_records(zip(file_names, file_contents))
    summary = (
        f"Loaded {len(merged['nodes'])} nodes, {len(merged['edges'])} edges, "
        f"and {len(merged['flows'])} traffic records. " + " | ".join(notes)
    )
    return summary, merged


@app.callback(Output("edge-prob-container", "style"), Input("topology-type", "value"))
def toggle_edge_prob(topology):
    return {"display": "block"} if topology == "random" else {"display": "none"}


@app.callback(Output("custom-flow-container", "style"), Input("traffic-intensity", "value"))
def toggle_custom_flows(intensity):
    return {"display": "block"} if intensity == "custom" else {"display": "none"}


@app.callback(Output("random-failure-container", "style"), Input("random-failure-mode", "value"))
def toggle_random_failures(value):
    return {"display": "block", "marginBottom": "12px"} if value else {"display": "none", "marginBottom": "12px"}


@app.callback(
    Output("congestion-toggle-label", "children"),
    Output("congestion-toggle-label", "style"),
    Output("congestion-info", "children"),
    Output("congestion-info", "style"),
    Input("congestion-mode", "value"),
)
def update_congestion_ui(value):
    is_on = bool(value)
    if is_on:
        return (
            "ON",
            {"fontFamily": SANS_STACK, "fontSize": "13px", "fontWeight": "bold", "color": COLORS["primary"]},
            "Active: link delay and packet-drop risk scale with link load relative to bandwidth.",
            {"fontSize": "12px", "color": COLORS["primary_dark"], "marginTop": "10px", "fontFamily": SANS_STACK, "padding": "10px 12px", "background": "#eef9fc", "borderRadius": "14px", "borderLeft": f"4px solid {COLORS['primary']}"},
        )

    return (
        "OFF",
        {"fontFamily": SANS_STACK, "fontSize": "13px", "fontWeight": "bold", "color": COLORS["muted"]},
        "Disabled: static routing using the base edge weights only.",
        {"fontSize": "12px", "color": COLORS["muted"], "marginTop": "10px", "fontFamily": SANS_STACK, "padding": "10px 12px", "background": "#f4f1ec", "borderRadius": "14px", "borderLeft": f"4px solid {COLORS['line']}"},
    )


@app.callback(
    Output("network-status", "children"),
    Output("network-state", "data"),
    Output("report-state", "data"),
    Input("generate-network", "n_clicks"),
    State("topology-type", "value"),
    State("node-count", "value"),
    State("edge-prob", "value"),
    State("random-seed", "value"),
    State("import-state", "data"),
    State("random-failure-mode", "value"),
    State("random-down-node-count", "value"),
    State("random-down-edge-count", "value"),
    State("random-loss-node-count", "value"),
    State("random-loss-edge-count", "value"),
    State("random-maintenance-edge-count", "value"),
    State("random-loss-min", "value"),
    State("random-loss-max", "value"),
    State("random-maintenance-min", "value"),
    State("random-maintenance-max", "value"),
    State("down-nodes", "value"),
    State("down-edges", "value"),
    State("packet-loss-edges", "value"),
    State("packet-loss-nodes", "value"),
    State("maintenance-edges", "value"),
    prevent_initial_call=True,
)
def update_network_state(
    n_clicks,
    topology_type,
    node_count,
    edge_prob,
    random_seed,
    import_state,
    random_failure_mode,
    random_down_node_count,
    random_down_edge_count,
    random_loss_node_count,
    random_loss_edge_count,
    random_maintenance_edge_count,
    random_loss_min,
    random_loss_max,
    random_maintenance_min,
    random_maintenance_max,
    down_nodes,
    down_edges,
    packet_loss_edges,
    packet_loss_nodes,
    maintenance_edges,
):
    node_count = int(node_count or 20)
    edge_prob = float(edge_prob or 0.3)
    seed = None if random_seed in (None, "") else int(random_seed)

    manual_failure_profile = build_manual_failure_profile(
        down_nodes,
        down_edges,
        packet_loss_edges,
        packet_loss_nodes,
        maintenance_edges,
    )

    preview_network = build_network(topology_type, node_count, edge_prob, seed, import_state, None)
    random_failure_profile = {}
    if random_failure_mode:
        random_failure_profile = preview_network.build_random_failure_profile(
            seed=_offset_seed(seed, 90),
            down_node_count=int(random_down_node_count or 0),
            down_edge_count=int(random_down_edge_count or 0),
            packet_loss_node_count=int(random_loss_node_count or 0),
            packet_loss_edge_count=int(random_loss_edge_count or 0),
            maintenance_edge_count=int(random_maintenance_edge_count or 0),
            packet_loss_range=(float(random_loss_min or 0.1), float(random_loss_max or 0.35)),
            maintenance_factor_range=(float(random_maintenance_min or 1.25), float(random_maintenance_max or 2.0)),
        )

    failure_profile = merge_failure_profiles(manual_failure_profile, random_failure_profile)

    network = build_network(topology_type, node_count, edge_prob, seed, import_state, failure_profile)
    source_label = "Imported scenario" if import_state and import_state.get("edges") else topology_type.capitalize()
    status = (
        f"{source_label} ready with {network.graph.number_of_nodes()} nodes and {network.graph.number_of_edges()} edges. "
        f"Failures: {len(failure_profile['down_nodes'])} node-down, {len(failure_profile['down_edges'])} link-down, "
        f"{len(failure_profile['maintenance_edges'])} maintenance overrides."
    )
    if random_failure_mode:
        status += " Random failure mode used the scenario seed for reproducible sampling."
    state = {
        "scenario_id": n_clicks,
        "topology_type": topology_type,
        "node_count": node_count,
        "active_node_count": network.graph.number_of_nodes(),
        "active_edge_count": network.graph.number_of_edges(),
        "edge_prob": edge_prob,
        "seed": seed,
        "import_data": import_state,
        "failure_profile": serialise_failure_profile(failure_profile),
        "source_label": source_label,
    }
    return status, state, None


@app.callback(
    Output("network-graph", "figure"),
    Input("network-state", "data"),
    Input("simulation-state", "data"),
)
def render_network_graph(network_state, simulation_state):
    if not network_state:
        return empty_figure()

    active_simulation = simulation_state if is_simulation_current(network_state, simulation_state) else None

    network = build_network(
        network_state["topology_type"],
        int(network_state["node_count"]),
        float(network_state["edge_prob"]),
        network_state.get("seed"),
        network_state.get("import_data"),
        network_state.get("failure_profile"),
    )
    return build_network_figure(network, network_state.get("source_label", "Scenario"), int(network_state["node_count"]), active_simulation)




@app.callback(
    Output("simulation-state", "data"),
    Input("run-simulation", "n_clicks"),
    State("network-state", "data"),
    State("algorithm-type", "value"),
    State("traffic-intensity", "value"),
    State("flow-count", "value"),
    State("congestion-mode", "value"),
    prevent_initial_call=True,
)
def run_simulation(
    n_clicks,
    network_state,
    algorithm_type,
    traffic_intensity,
    flow_count,
    congestion_mode
):
    del n_clicks

    if not network_state:
        return None

    payload = {
        "topology": network_state["topology_type"],
        "algorithm": algorithm_type,
        "nodes": network_state["node_count"],
        "traffic": traffic_intensity,
        "flow_count": int(flow_count or 20),
        "seed": network_state.get("seed"),
        "edge_prob": network_state["edge_prob"],
        "import_data": network_state.get("import_data"),
        "failure_profile": network_state.get("failure_profile"),
    }
    if algorithm_type == "all":
        
        api_result = compare(payload)

        return {
            "mode": "all",
            "scenario_id": network_state.get("scenario_id"),
            "comparison": api_result["comparison"],
            "scores": api_result["scores"],
            "seed": network_state.get("seed")
        }

    api_result = simulate(payload)

    return {
        "mode": "single",
        "scenario_id": network_state.get("scenario_id"),
        "algorithm_label": algorithm_type.replace("_", " ").title(),
        "results": api_result,
        "edge_loads": api_result.get("edge_loads", {}),
        "flow_details": api_result.get("flow_details", []),
        "seed": network_state.get("seed")
    }



@app.callback(
    Output("report-state", "data", allow_duplicate=True),
    Input("export-report", "n_clicks"),
    State("network-state", "data"),
    State("simulation-state", "data"),
    prevent_initial_call=True,
)
def export_report(
    n_clicks,
    network_state,
    simulation_state
):
    del n_clicks

    if not simulation_state:
        return None

    recommendation_data = recommendation_api({
            "network_state": network_state,
            "simulation_state": simulation_state
        }
    )


    report_data = report({
            "network_state": network_state,
            "simulation_state": simulation_state,
            "recommendations": recommendation_data
        }
    )

    return report_data


@app.callback(
    Output("metrics-panel-heading", "children"),
    Output("metrics-display", "children"),
    Output("edge-load-display", "children"),
    Output("paths-panel-heading", "children"),
    Output("paths-display", "children"),
    Output("comparison-panel-heading", "children"),
    Output("comparison-results", "children"),
    Output("recommendations-display", "children"),
    Input("simulation-state", "data"),
    Input("network-state", "data"),
    Input("report-state", "data"),
)
def render_results(simulation_state, network_state, report_state):
    if simulation_state and not is_simulation_current(network_state, simulation_state):
        simulation_state = None
        report_state = None

    recommendations = []

    if simulation_state and network_state:
        recommendations = get_recommendations(network_state, simulation_state)

    recommendations_panel = build_recommendations_panel(
        recommendations,
        report_state
    )

    if not simulation_state:
        return (
            panel_heading("Performance Readout", "The metrics update after each simulation run."),
            html.P("Run a simulation to populate the readout.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK}),
            html.Div(),
            panel_heading("Flow Narratives", "Inspect the first few traffic flows to see who gets through and who gets dropped."),
            html.P("Generate or import a network and run a simulation to inspect flow outcomes.", style={"color": COLORS["muted"], "fontFamily": SANS_STACK}),
            panel_heading("Algorithm Comparison", "Use ALL mode to rank the routing strategies."),
            html.P('Switch the algorithm dropdown to "ALL" for a ranked comparison.', style={"color": COLORS["muted"], "fontFamily": SANS_STACK}),
            recommendations_panel,
        )

    if simulation_state.get("mode") == "all":
        return (
            panel_heading("Algorithm Comparison", "Rank all routing strategies for the current scenario."),
            build_comparison_panel(simulation_state),
            html.Div(),
            panel_heading("Metric Histogram", "Compare Score, PDR, Latency, Throughput, and Max Util across all algorithms."),
            build_comparison_histograms(simulation_state),
            panel_heading("Ranking Summary", "A compact score order for the current comparison run."),
            build_comparison_summary_panel(simulation_state),
            recommendations_panel,
        )

    results = simulation_state["results"]
    metrics_panel = build_metrics_panel(results, simulation_state.get("seed"))
    edge_panel = build_edge_load_panel(simulation_state)
    flow_panel = build_flow_details_panel(simulation_state.get("flow_details", []))
    comparison_hint = html.P('Switch the algorithm dropdown to "ALL" for a ranked comparison.', style={"color": COLORS["muted"], "fontFamily": SANS_STACK})
    return (
        panel_heading("Performance Readout", "The metrics update after each simulation run."),
        metrics_panel,
        edge_panel,
        panel_heading("Flow Narratives", "Inspect the first few traffic flows to see who gets through and who gets dropped."),
        flow_panel,
        panel_heading("Algorithm Comparison", "Use ALL mode to rank the routing strategies."),
        comparison_hint,
        recommendations_panel,
    )


def run_dashboard():
    port = 8050
    print("\n" + "=" * 50)
    print("  Network Routing Analyzer is running!")
    print("  Open your browser and go to:")
    print(f"  http://localhost:{port}")
    print("=" * 50 + "\n")
    app.run(debug=False, use_reloader=False, port=port)


if __name__ == "__main__":
    run_dashboard()
