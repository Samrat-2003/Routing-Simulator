import os
import sys
import json

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("PROJECT_ROOT =", PROJECT_ROOT)

from flask import Flask,request,jsonify
from src.network.topology import NetworkTopology
from src.services.simulation_service import simulate_network
from src.services.comparison_service import compare_algorithms
from src.planning.recommendations import build_recommendations
from src.reporting.exporter import export_simulation_bundle


def parse_number(value):
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return value


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


def normalise_node_map(node_map):
    return {parse_number(node): value for node, value in (node_map or {}).items()}


def normalise_edge_map(edge_map):
    return {edge_from_storage_key(edge): value for edge, value in (edge_map or {}).items()}


def deserialise_failure_profile(profile):
    profile = profile or {}
    return {
        "down_nodes": list(profile.get("down_nodes", [])),
        "down_edges": [edge_from_storage_key(edge) for edge in profile.get("down_edges", [])],
        "packet_loss_nodes": normalise_node_map(profile.get("packet_loss_nodes")),
        "packet_loss_edges": normalise_edge_map(profile.get("packet_loss_edges")),
        "maintenance_edges": normalise_edge_map(profile.get("maintenance_edges")),
    }


def build_network_from_request(data):

    topology = data.get("topology", "mesh")

    try:
        nodes = int(data.get("nodes", 20))
    except ValueError:
        raise ValueError("nodes must be an integer")

    seed = data.get("seed")
    edge_prob = float(data.get("edge_prob", 0.3))
    bandwidth_range = data.get("bandwidth_range", [data.get("bandwidth_min", 10), data.get("bandwidth_max", 100)])

    network = NetworkTopology(seed=seed)
    import_data = data.get("import_data")

    if import_data and import_data.get("edges"):
        network.load_from_data(import_data.get("nodes"), import_data.get("edges"), seed=seed)

    elif topology == "mesh":
        network.create_mesh_topology(nodes, bandwidth_range=bandwidth_range)

    elif topology == "ring":
        network.create_ring_topology(nodes, bandwidth_range=bandwidth_range)

    elif topology == "star":
        network.create_star_topology(nodes, bandwidth_range=bandwidth_range)

    elif topology == "random":
        network.create_random_topology(
            nodes,
            p=edge_prob,
            bandwidth_range=bandwidth_range
        )

    else:
        raise ValueError(f"Unknown topology {topology}")

    network.apply_failure_profile(deserialise_failure_profile(data.get("failure_profile")))
    return network


app = Flask(__name__)

# @app.route("/")
# def home():
#     return {"status": "running"}
# 
# @app.route("/api/test")
# def api_test():
#     return{"message":"api works"}

@app.route("/api/health")
def health():
    return{
        "status":"healthy",
        "service":"routing-simulator-api"
    }

@app.route("/api/simulate",methods=['POST'])
def simulate():
    data = request.get_json()

    try:
        network = build_network_from_request(data) 
    except ValueError as e:
        return jsonify({
            "error": str(e)
        }), 400
    
    algorithm = data.get("algorithm", "dijkstra")
    traffic = data.get("traffic", "medium")
    seed = data.get("seed")
    flow_count = int(data.get("flow_count", 20) or 20)
    
    result = simulate_network(
        network=network,
        algorithm_type=algorithm,
        traffic_intensity=traffic,
        flow_count=flow_count,
        seed=seed,
    )

    return jsonify(result)

@app.route("/api/compare",methods=['POST'])
def compare():
    data = request.get_json()

    try:
        network = build_network_from_request(data)
    except ValueError as e:
        return jsonify({
            "error":str(e)
        }),400
    
    seed = data.get("seed")
    traffic = data.get("traffic", "medium")
    flow_count = int(data.get("flow_count", 20) or 20)
    
    result = compare_algorithms(
        network=network,
        traffic_intensity=traffic,
        flow_count=flow_count,
        seed=seed
        )
    
    return jsonify(result)


@app.route("/api/recommendations", methods=["POST"])
def recommendations():
    data = request.get_json()

    network_state = data.get("network_state")
    simulation_state = data.get("simulation_state")


    recommendations = build_recommendations(
        network_state,
        simulation_state
    )

    

    return jsonify(recommendations)

@app.route("/api/network-info",methods=['POST'])
def network_info(): 
    data = request.get_json()

    try:
        network = build_network_from_request(data)
    except ValueError as e:
        return jsonify({
            "error":str(e)
        }),400

    return jsonify(
        network.get_network_info()
    )

@app.route("/api/report",methods =['POST'])
def report():
     
    data = request.get_json()

    network_state = data.get("network_state")
    simulation_state = data.get("simulation_state")
    recommendations = data.get("recommendations", [])

    report = export_simulation_bundle(
        network_state,
        simulation_state,
        recommendations
    )

    return jsonify(report)
    
@app.route("/api/algorithms")
def algorithms():

    return jsonify({
        "algorithms": [
            {
                "id": "dijkstra",
                "name": "Dijkstra"
            },
            {
                "id": "bellman_ford",
                "name": "Bellman Ford"
            },
            {
                "id": "pca_mr",
                "name": "PCA-MR Proposed Algorithm"
            },
            {
                "id": "aco",
                "name": "Ant Colony Optimization"
            },
            {
                "id": "ga",
                "name": "Genetic Algorithm"
            }
        ]
    })  

@app.route("/api/topologies")
def topologies():

    return jsonify({
        "topologies": [
            {
                "id": "mesh",
                "name": "Mesh"
            },
            {
                "id": "ring",
                "name": "Ring"
            },
            {
                "id": "star",
                "name": "Star"
            },
            {
                "id": "random",
                "name": "Random"
            }
        ]
    })



if __name__ == "__main__":
    app.run(debug=True)
