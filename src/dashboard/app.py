import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import networkx as nx
import pandas as pd
import random

from src.network.topology import NetworkTopology
from src.algorithms.routing import create_routing_algorithm
from src.traffic.generator import TrafficGenerator
from src.metrics.analyzer import PerformanceMetrics

# Initialize the Dash app
app = dash.Dash(__name__)

# Global variables to store state
current_network = None
current_algorithm = None
current_paths = []

# App layout
app.layout = html.Div([
    html.H1("Network Routing Algorithm Analyzer", style={'text-align': 'center'}),
    
    html.Div([
        html.Div([
            html.H3("Network Configuration"),
            dcc.Dropdown(
                id='topology-type',
                options=[
                    {'label': 'Mesh', 'value': 'mesh'},
                    {'label': 'Random', 'value': 'random'},
                    {'label': 'Ring', 'value': 'ring'},
                    {'label': 'Star', 'value': 'star'}
                ],
                value='mesh',
                style={'width': '100%'}
            ),
            html.Br(),
            html.Label("Number of Nodes:"),
            dcc.Slider(id='node-count', min=5, max=20, step=1, value=10,
                      marks={i: str(i) for i in range(5, 21, 5)}),
            html.Br(),
            html.Button('Generate Network', id='generate-network', n_clicks=0),
        ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top'}),
        
        html.Div([
            html.H3("Traffic Configuration"),
            dcc.Dropdown(
                id='traffic-intensity',
                options=[
                    {'label': 'Low', 'value': 'low'},
                    {'label': 'Medium', 'value': 'medium'},
                    {'label': 'High', value: 'high'}
                ],
                value='medium',
                style={'width': '100%'}
            ),
            html.Br(),
            html.Label("Number of Flows:"),
            dcc.Input(id='flow-count', type='number', value=20, min=1, max=100),
            html.Br(),
            html.Button('Generate Traffic', id='generate-traffic', n_clicks=0),
        ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top'}),
        
        html.Div([
            html.H3("Routing Algorithm"),
            dcc.Dropdown(
                id='algorithm-type',
                options=[
                    {'label': 'Dijkstra', 'value': 'dijkstra'},
                    {'label': 'Bellman-Ford', 'value': 'bellman_ford'},
                    {'label': 'Ant Colony Optimization', 'value': 'aco'},
                    {'label': 'Genetic Algorithm', 'value': 'ga'}
                ],
                value='dijkstra',
                style={'width': '100%'}
            ),
            html.Br(),
            html.Button('Run Simulation', id='run-simulation', n_clicks=0),
        ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top'}),
    ]),
    
    html.Hr(),
    
    html.Div([
        html.Div([
            html.H3("Network Topology Visualization"),
            dcc.Graph(id='network-graph')
        ], style={'width': '50%', 'display': 'inline-block'}),
        
        html.Div([
            html.H3("Performance Metrics"),
            html.Div(id='metrics-display'),
            html.H3("Routing Paths"),
            html.Div(id='paths-display')
        ], style={'width': '50%', 'display': 'inline-block', 'vertical-align': 'top'})
    ]),
    
    html.Hr(),
    
    html.Div([
        html.H3("Algorithm Comparison"),
        html.Button('Compare All Algorithms', id='compare-algorithms', n_clicks=0),
        html.Div(id='comparison-results')
    ])
])

# Callbacks
@app.callback(
    Output('network-graph', 'figure'),
    Input('generate-network', 'n_clicks'),
    Input('topology-type', 'value'),
    Input('node-count', 'value')
)
def update_network_graph(n_clicks, topology_type, node_count):
    global current_network
    
    if n_clicks > 0:
        # Generate network
        current_network = NetworkTopology()
        
        if topology_type == 'mesh':
            current_network.create_mesh_topology(node_count)
        elif topology_type == 'random':
            current_network.create_random_topology(node_count, 0.3)
        elif topology_type == 'ring':
            current_network.create_ring_topology(node_count)
        elif topology_type == 'star':
            current_network.create_star_topology(node_count)
        
        # Create network visualization
        G = current_network.graph
        pos = nx.spring_layout(G, seed=42)
        
        # Extract edge coordinates
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Extract node coordinates
        node_x = []
        node_y = []
        node_text = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(f'Node {node}')
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            marker=dict(
                size=20,
                color='lightblue',
                line=dict(width=2, color='darkblue')
            )
        )
        
        figure = go.Figure(data=[edge_trace, node_trace],
                          layout=go.Layout(
                            title=f'{topology_type.capitalize()} Network Topology',
                            titlefont_size=16,
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20,l=5,r=5,t=40),
                            annotations=[ dict(
                                text="Network nodes and connections",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.005, y=-0.07,
                                xanchor="left", yanchor="bottom",
                                font=dict(size=14)
                            ) ],
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                          )
        
        return figure
    
    # Default empty figure
    return go.Figure()

@app.callback(
    [Output('metrics-display', 'children'),
     Output('paths-display', 'children')],
    Input('run-simulation', 'n_clicks'),
    Input('algorithm-type', 'value'),
    Input('traffic-intensity', 'value'),
    Input('flow-count', 'value')
)
def run_simulation(n_clicks, algorithm_type, traffic_intensity, flow_count):
    global current_network, current_algorithm, current_paths
    
    if n_clicks > 0 and current_network:
        # Generate traffic
        traffic = TrafficGenerator(current_network, traffic_intensity)
        flows = traffic.generate_flows(flow_count)
        
        # Create routing algorithm
        algorithm = create_routing_algorithm(algorithm_type, current_network)
        current_algorithm = algorithm
        
        # Analyze performance
        metrics_analyzer = PerformanceMetrics(current_network)
        results = metrics_analyzer.analyze_routing_performance(algorithm, flows)
        
        # Store paths for visualization
        current_paths = results['paths']
        
        # Display metrics
        metrics_html = html.Div([
            html.P(f"Execution Time: {results['execution_time']:.4f} seconds"),
            html.P(f"Successful Routes: {results['successful_routes']}/{results['total_flows']}"),
            html.P(f"Packet Delivery Ratio: {results['packet_delivery_ratio']:.2%}"),
            html.P(f"Average Latency: {results['average_latency']:.2f} units"),
            html.P(f"Average Throughput: {results['average_throughput']:.2f} KB/unit"),
            html.P(f"Average Hop Count: {results['average_hop_count']:.2f}")
        ])
        
        # Display sample paths
        paths_html = html.Div([
            html.P(f"Showing first 5 paths out of {len(current_paths)}:"),
            html.Ul([
                html.Li(f"Path {i+1}: {' -> '.join(map(str, path))}") 
                for i, path in enumerate(current_paths[:5])
            ])
        ])
        
        return metrics_html, paths_html
    
    return html.P("Run simulation to see results"), html.P("No paths generated yet")

@app.callback(
    Output('comparison-results', 'children'),
    Input('compare-algorithms', 'n_clicks')
)
def compare_all_algorithms(n_clicks):
    global current_network
    
    if n_clicks > 0 and current_network:
        # Generate traffic for comparison
        traffic = TrafficGenerator(current_network, "medium")
        flows = traffic.generate_flows(15)
        
        # Create all algorithms
        algorithms = {
            'Dijkstra': create_routing_algorithm('dijkstra', current_network),
            'Bellman-Ford': create_routing_algorithm('bellman_ford', current_network),
            'ACO': create_routing_algorithm('aco', current_network),
            'GA': create_routing_algorithm('ga', current_network)
        }
        
        # Analyze performance
        metrics_analyzer = PerformanceMetrics(current_network)
        comparison = metrics_analyzer.compare_algorithms(algorithms, flows)
        
        # Create comparison table
        table_header = [
            html.Thead(html.Tr([
                html.Th("Algorithm"),
                html.Th("Execution Time (s)"),
                html.Th("PDR (%)"),
                html.Th("Avg Latency"),
                html.Th("Avg Throughput"),
                html.Th("Avg Hop Count")
            ]))
        ]
        
        table_rows = []
        for alg_name, metrics in comparison.items():
            row = html.Tr([
                html.Td(alg_name),
                html.Td(f"{metrics['execution_time']:.4f}"),
                html.Td(f"{metrics['packet_delivery_ratio']*100:.1f}%"),
                html.Td(f"{metrics['average_latency']:.2f}"),
                html.Td(f"{metrics['average_throughput']:.2f}"),
                html.Td(f"{metrics['average_hop_count']:.2f}")
            ])
            table_rows.append(row)
        
        table_body = [html.Tbody(table_rows)]
        
        return html.Table(table_header + table_body, 
                         style={'width': '100%', 'border-collapse': 'collapse', 'border': '1px solid black'})
    
    return html.P("Click 'Compare All Algorithms' to run comparison")

# Main function to run the app
def run_dashboard():
    app.run_server(debug=True, port=8050)

if __name__ == '__main__':
    run_dashboard()
