import sys
import os

# Ensure project root is on sys.path regardless of where this file is run from
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import networkx as nx

from src.network.topology import NetworkTopology
from src.algorithms.routing import create_routing_algorithm
from src.traffic.generator import TrafficGenerator
from src.metrics.analyzer import PerformanceMetrics

# ── App init ─────────────────────────────────────────────────────────────────
app = dash.Dash(__name__)

current_network = None

# ── Styles ────────────────────────────────────────────────────────────────────
CARD  = {'background': '#f9f9f9', 'border': '1px solid #ddd', 'borderRadius': '8px',
         'padding': '16px', 'marginBottom': '16px'}
LABEL = {'fontWeight': 'bold', 'marginTop': '10px', 'display': 'block'}
INPUT = {'width': '100%', 'padding': '6px', 'boxSizing': 'border-box', 'marginTop': '4px'}
BTN   = {'marginTop': '14px', 'width': '100%', 'padding': '10px', 'background': '#2c7be5',
         'color': 'white', 'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer',
         'fontWeight': 'bold', 'fontSize': '14px'}
TH    = {'border': '1px solid #ccc', 'padding': '8px', 'background': '#eef2f7', 'textAlign': 'left'}
TD    = {'border': '1px solid #ccc', 'padding': '8px'}

# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = html.Div(
    style={'fontFamily': 'Arial, sans-serif', 'maxWidth': '1400px',
           'margin': '0 auto', 'padding': '20px'},
    children=[

        html.H1("Network Routing Algorithm Analyzer",
                style={'textAlign': 'center', 'color': '#1a1a2e', 'marginBottom': '24px'}),

        # ── Row 1: three config cards ────────────────────────────────────────
        html.Div(style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}, children=[

            # Card 1 – Network
            html.Div(style={**CARD, 'flex': '1', 'minWidth': '260px'}, children=[
                html.H3("① Network Configuration", style={'marginTop': 0}),

                html.Label("Topology Type", style=LABEL),
                dcc.Dropdown(
                    id='topology-type',
                    options=[
                        {'label': 'Mesh (fully connected)', 'value': 'mesh'},
                        {'label': 'Random (Erdős–Rényi)',   'value': 'random'},
                        {'label': 'Ring',                   'value': 'ring'},
                        {'label': 'Star',                   'value': 'star'},
                    ],
                    value='random',
                    clearable=False,
                ),

                html.Label("Number of Nodes (10 – 200)", style=LABEL),
                dcc.Input(id='node-count', type='number', value=20,
                          min=10, max=200, step=1, style=INPUT),

                # Edge probability – only relevant for random topology
                html.Div(id='edge-prob-container', children=[
                    html.Label("Edge Probability (0.1 – 0.8)", style=LABEL),
                    dcc.Input(id='edge-prob', type='number', value=0.3,
                              min=0.1, max=0.8, step=0.05, style=INPUT),
                ]),

                html.Button('Generate Network', id='generate-network', n_clicks=0, style=BTN),
                html.Div(id='network-status',
                         style={'marginTop': '8px', 'color': '#555', 'fontSize': '13px'}),
            ]),

            # Card 2 – Traffic
            html.Div(style={**CARD, 'flex': '1', 'minWidth': '260px'}, children=[
                html.H3("② Traffic Configuration", style={'marginTop': 0}),

                html.Label("Traffic Intensity", style=LABEL),
                dcc.Dropdown(
                    id='traffic-intensity',
                    options=[
                        {'label': 'Low  (10 flows)',    'value': 'low'},
                        {'label': 'Medium  (20 flows)', 'value': 'medium'},
                        {'label': 'High  (40 flows)',   'value': 'high'},
                        {'label': 'Custom',             'value': 'custom'},
                    ],
                    value='medium',
                    clearable=False,
                ),

                # Custom flow count – shown only when Custom is selected
                html.Div(id='custom-flow-container', style={'display': 'none'}, children=[
                    html.Label("Number of Flows (1 – 100)", style=LABEL),
                    dcc.Input(id='flow-count', type='number', value=20,
                              min=1, max=100, step=1, style=INPUT),
                ]),

                html.Label("Congestion Simulation", style=LABEL),
                html.Div(
                    style={
                        'display': 'flex', 'alignItems': 'center', 'gap': '10px',
                        'marginTop': '6px', 'marginBottom': '4px',
                    },
                    children=[
                        # Toggle switch built from a Checklist
                        dcc.Checklist(
                            id='congestion-mode',
                            options=[{'label': '', 'value': 'on'}],
                            value=['on'],
                            inputStyle={
                                'width': '36px', 'height': '20px', 'cursor': 'pointer',
                                'accentColor': '#2c7be5',
                            },
                        ),
                        html.Span(
                            id='congestion-toggle-label',
                            style={'fontSize': '13px', 'fontWeight': 'bold', 'color': '#2c7be5'},
                            children='ON',
                        ),
                    ],
                ),
                html.Div(
                    id='congestion-info',
                    style={'fontSize': '11px', 'color': '#2c7be5', 'marginTop': '4px',
                           'fontStyle': 'italic', 'padding': '6px 8px',
                           'background': '#eef4ff', 'borderRadius': '4px',
                           'borderLeft': '3px solid #2c7be5'},
                    children="Active: each flow degrades edges it uses (+25% weight). "
                             "Edges used by 3+ flows risk 30% packet drop.",
                ),
            ]),

            # Card 3 – Algorithm
            html.Div(style={**CARD, 'flex': '1', 'minWidth': '260px'}, children=[
                html.H3("③ Routing Algorithm", style={'marginTop': 0}),

                html.Label("Algorithm", style=LABEL),
                dcc.Dropdown(
                    id='algorithm-type',
                    options=[
                        {'label': 'Dijkstra (shortest path)',       'value': 'dijkstra'},
                        {'label': 'Bellman-Ford (distributed SP)',  'value': 'bellman_ford'},
                        {'label': 'ACO (Ant Colony Optimization)',  'value': 'aco'},
                        {'label': 'GA (Genetic Algorithm)',         'value': 'ga'},
                        {'label': 'ALL – compare every algorithm',  'value': 'all'},
                    ],
                    value='dijkstra',
                    clearable=False,
                ),

                html.Button('Run Simulation', id='run-simulation', n_clicks=0, style=BTN),
            ]),
        ]),

        html.Hr(),

        # ── Row 2: graph + metrics ───────────────────────────────────────────
        html.Div(style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}, children=[

            html.Div(style={**CARD, 'flex': '1.2', 'minWidth': '340px'}, children=[
                html.H3("Network Topology", style={'marginTop': 0}),
                dcc.Graph(id='network-graph', style={'height': '420px'}),
            ]),

            html.Div(style={**CARD, 'flex': '0.8', 'minWidth': '280px'}, children=[
                html.H3("Performance Metrics", style={'marginTop': 0}),
                html.Div(id='metrics-display', style={'fontSize': '14px'}),
                html.H3("Sample Paths", style={'marginTop': '16px'}),
                html.Div(id='paths-display', style={'fontSize': '13px'}),
            ]),
        ]),

        html.Hr(),

        # ── Row 3: comparison table ──────────────────────────────────────────
        html.Div(style=CARD, children=[
            html.H3("Algorithm Comparison", style={'marginTop': 0}),
            html.Div(id='comparison-results', style={'fontSize': '14px'}),
        ]),
    ],
)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output('edge-prob-container', 'style'),
    Input('topology-type', 'value'),
)
def toggle_edge_prob(topology):
    return {'display': 'block'} if topology == 'random' else {'display': 'none'}


@app.callback(
    Output('custom-flow-container', 'style'),
    Input('traffic-intensity', 'value'),
)
def toggle_custom_flows(intensity):
    return {'display': 'block'} if intensity == 'custom' else {'display': 'none'}


@app.callback(
    Output('congestion-toggle-label', 'children'),
    Output('congestion-toggle-label', 'style'),
    Output('congestion-info', 'children'),
    Output('congestion-info', 'style'),
    Input('congestion-mode', 'value'),
)
def update_congestion_ui(value):
    is_on = bool(value)  # Checklist returns [] when unchecked, ['on'] when checked
    if is_on:
        label       = 'ON'
        label_style = {'fontSize': '13px', 'fontWeight': 'bold', 'color': '#2c7be5'}
        info_text   = ("Active: each flow degrades edges it uses (+25% weight). "
                       "Edges used by 3+ flows risk 30% packet drop.")
        info_style  = {
            'fontSize': '11px', 'color': '#2c7be5', 'marginTop': '4px',
            'fontStyle': 'italic', 'padding': '6px 8px',
            'background': '#eef4ff', 'borderRadius': '4px',
            'borderLeft': '3px solid #2c7be5',
        }
    else:
        label       = 'OFF'
        label_style = {'fontSize': '13px', 'fontWeight': 'bold', 'color': '#888'}
        info_text   = "Disabled: classic static routing — no edge degradation or packet drops."
        info_style  = {
            'fontSize': '11px', 'color': '#888', 'marginTop': '4px',
            'fontStyle': 'italic', 'padding': '6px 8px',
            'background': '#f5f5f5', 'borderRadius': '4px',
            'borderLeft': '3px solid #ccc',
        }
    return label, label_style, info_text, info_style


@app.callback(
    Output('network-graph',  'figure'),
    Output('network-status', 'children'),
    Input('generate-network', 'n_clicks'),
    State('topology-type', 'value'),
    State('node-count',    'value'),
    State('edge-prob',     'value'),
    prevent_initial_call=True,
)
def update_network_graph(n_clicks, topology_type, node_count, edge_prob):
    global current_network

    node_count = int(node_count or 20)
    edge_prob  = float(edge_prob  or 0.3)

    current_network = NetworkTopology()
    if topology_type == 'mesh':
        current_network.create_mesh_topology(node_count)
    elif topology_type == 'random':
        current_network.create_random_topology(node_count, edge_prob)
    elif topology_type == 'ring':
        current_network.create_ring_topology(node_count)
    elif topology_type == 'star':
        current_network.create_star_topology(node_count)

    G   = current_network.graph
    pos = nx.spring_layout(G, seed=42)

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode='lines',
        line=dict(width=1.5, color='#aaa'), hoverinfo='none',
    )

    show_labels = node_count <= 30
    node_trace = go.Scatter(
        x=[pos[n][0] for n in G.nodes()],
        y=[pos[n][1] for n in G.nodes()],
        mode='markers+text' if show_labels else 'markers',
        text=[f'Node {n}' for n in G.nodes()],
        textposition='middle center',
        hoverinfo='text',
        marker=dict(
            size=14 if show_labels else 8,
            color='#5b8dee',
            line=dict(width=2, color='#1a4fa0'),
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=f'{topology_type.capitalize()} – {G.number_of_nodes()} nodes, '
                  f'{G.number_of_edges()} edges',
            showlegend=False, hovermode='closest',
            margin=dict(b=10, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    status = (f"✔ Network ready — {G.number_of_nodes()} nodes, "
              f"{G.number_of_edges()} edges"
              + (f", edge prob {edge_prob}" if topology_type == 'random' else ""))
    return fig, status


@app.callback(
    Output('metrics-display',    'children'),
    Output('paths-display',      'children'),
    Output('comparison-results', 'children'),
    Input('run-simulation', 'n_clicks'),
    State('algorithm-type',    'value'),
    State('traffic-intensity', 'value'),
    State('flow-count',        'value'),
    State('congestion-mode',   'value'),
    prevent_initial_call=True,
)
def run_simulation(n_clicks, algorithm_type, traffic_intensity, flow_count, congestion_mode):
    global current_network

    if not current_network:
        err = html.P("⚠ Please generate a network first.", style={'color': 'red'})
        return err, html.Div(), html.Div()

    intensity_defaults = {'low': 10, 'medium': 20, 'high': 40}
    count = int(flow_count or 20) if traffic_intensity == 'custom' \
            else intensity_defaults.get(traffic_intensity, 20)

    traffic_gen = TrafficGenerator(current_network, traffic_intensity)
    flows       = traffic_gen.generate_flows(count)
    use_congestion = bool(congestion_mode)  # Checklist: ['on'] = True, [] = False
    analyzer    = PerformanceMetrics(current_network, simulate_congestion=use_congestion)

    # ── ALL: compare every algorithm ─────────────────────────────────────────
    if algorithm_type == 'all':
        algorithms = {
            'Dijkstra':     create_routing_algorithm('dijkstra',     current_network),
            'Bellman-Ford': create_routing_algorithm('bellman_ford', current_network),
            'ACO':          create_routing_algorithm('aco',          current_network),
            'GA':           create_routing_algorithm('ga',           current_network),
        }
        comparison = analyzer.compare_algorithms(algorithms, flows)

        # ── Scoring ───────────────────────────────────────────────────────────
        # Normalise each metric across algorithms then compute weighted score
        def normalise(values, lower_is_better=False):
            mn, mx = min(values), max(values)
            if mx == mn:
                return [1.0] * len(values)
            norm = [(v - mn) / (mx - mn) for v in values]
            return [1 - n for n in norm] if lower_is_better else norm

        names   = list(comparison.keys())
        metrics_list = list(comparison.values())

        pdr_norm       = normalise([m['packet_delivery_ratio'] for m in metrics_list])
        latency_norm   = normalise([m['average_latency']       for m in metrics_list], lower_is_better=True)
        time_norm      = normalise([m['execution_time']        for m in metrics_list], lower_is_better=True)
        throughput_norm= normalise([m['average_throughput']    for m in metrics_list])
        hops_norm      = normalise([m['average_hop_count']     for m in metrics_list], lower_is_better=True)

        WEIGHTS = {'pdr': 0.40, 'latency': 0.25, 'throughput': 0.15, 'time': 0.12, 'hops': 0.08}
        scores  = [
            round(
                WEIGHTS['pdr']        * pdr_norm[i]        +
                WEIGHTS['latency']    * latency_norm[i]     +
                WEIGHTS['throughput'] * throughput_norm[i]  +
                WEIGHTS['time']       * time_norm[i]        +
                WEIGHTS['hops']       * hops_norm[i],
                4
            )
            for i in range(len(names))
        ]

        best_idx  = scores.index(max(scores))
        best_name = names[best_idx]

        # ── Table ─────────────────────────────────────────────────────────────
        BEST_ROW = {
            'background': '#d4edda', 'fontWeight': 'bold',
            'border': '2px solid #28a745',
        }
        BEST_TD  = {**TD, 'background': '#d4edda', 'fontWeight': 'bold'}
        BEST_TH_CELL = {**TH, 'background': '#d4edda', 'fontWeight': 'bold'}

        header = html.Thead(html.Tr(
            [html.Th(c, style=TH) for c in
             ['Algorithm', 'Time (s)', 'PDR', 'Avg Latency', 'Avg Throughput', 'Avg Hops', 'Score']]
        ))

        rows = []
        for i, (name, m) in enumerate(comparison.items()):
            is_best  = (i == best_idx)
            cell     = BEST_TD if is_best else TD
            label    = f"{name} ★ BEST" if is_best else name
            rows.append(html.Tr([
                html.Td(label,                                     style=cell),
                html.Td(f"{m['execution_time']:.4f}",             style=cell),
                html.Td(f"{m['packet_delivery_ratio']:.2%}",      style=cell),
                html.Td(f"{m['average_latency']:.2f}",            style=cell),
                html.Td(f"{m['average_throughput']:.2f} KB/unit", style=cell),
                html.Td(f"{m['average_hop_count']:.2f}",          style=cell),
                html.Td(f"{scores[i]:.4f}",                       style=cell),
            ]))

        table = html.Table(
            [header, html.Tbody(rows)],
            style={'width': '100%', 'borderCollapse': 'collapse'},
        )

        # ── Weight legend ──────────────────────────────────────────────────────
        legend = html.Div([
            html.P(
                f"★ Best overall algorithm: {best_name}  (score {scores[best_idx]:.4f})",
                style={'color': '#155724', 'fontWeight': 'bold', 'fontSize': '15px',
                       'margin': '12px 0 4px'}
            ),
            html.P(
                "Score weights — PDR 40%  |  Latency 25%  |  Throughput 15%  |  Time 12%  |  Hops 8%",
                style={'color': '#555', 'fontSize': '12px', 'fontStyle': 'italic'}
            ),
        ])

        congestion_label = "with congestion simulation" if use_congestion else "without congestion (static)"
        summary = html.P(f"Compared all 4 algorithms on {count} flows — {congestion_label}.",
                         style={"color": "#155724" if use_congestion else "#555"})
        return summary, html.Div(), html.Div([legend, table])

    # ── Single algorithm ──────────────────────────────────────────────────────
    algo    = create_routing_algorithm(algorithm_type, current_network)
    results = analyzer.analyze_routing_performance(algo, flows)
    paths   = results['paths']

    metrics_html = html.Table(
        [html.Tbody([
            html.Tr([html.Td("Algorithm",             style=TH),
                     html.Td(results['algorithm'],                                    style=TD)]),
            html.Tr([html.Td("Execution Time",        style=TH),
                     html.Td(f"{results['execution_time']:.4f} s",                   style=TD)]),
            html.Tr([html.Td("Successful Routes",     style=TH),
                     html.Td(f"{results['successful_routes']} / {results['total_flows']}", style=TD)]),
            html.Tr([html.Td("Packet Delivery Ratio", style=TH),
                     html.Td(f"{results['packet_delivery_ratio']:.2%}",               style=TD)]),
            html.Tr([html.Td("Average Latency",       style=TH),
                     html.Td(f"{results['average_latency']:.2f} units",               style=TD)]),
            html.Tr([html.Td("Average Throughput",    style=TH),
                     html.Td(f"{results['average_throughput']:.2f} KB/unit",          style=TD)]),
            html.Tr([html.Td("Average Hop Count",     style=TH),
                     html.Td(f"{results['average_hop_count']:.2f}",                   style=TD)]),
        ])],
        style={'width': '100%', 'borderCollapse': 'collapse'},
    )

    paths_html = html.Div([
        html.P(f"Showing first 5 of {len(paths)} paths:"),
        html.Ul([html.Li(f"Path {i+1}: {' → '.join(map(str, p))}")
                 for i, p in enumerate(paths[:5])]),
    ]) if paths else html.P("No paths found.")

    hint = html.P('Select "ALL" in the algorithm dropdown to compare all algorithms.',
                  style={'color': '#888', 'fontStyle': 'italic'})
    return metrics_html, paths_html, hint


# ── Entry point ───────────────────────────────────────────────────────────────
def run_dashboard():
    port = 8050
    print("\n" + "="*50)
    print("  Network Routing Analyzer is running!")
    print(f"  Open your browser and go to:")
    print(f"  http://localhost:{port}")
    print("="*50 + "\n")
    app.run(debug=False, use_reloader=False, port=port)

if __name__ == '__main__':
    run_dashboard()