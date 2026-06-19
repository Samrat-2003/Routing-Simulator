import os
import sys

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


def build_network_from_request(data):

    topology = data.get("topology", "mesh")

    try:
        nodes = int(data.get("nodes", 20))
    except ValueError:
        raise ValueError("nodes must be an integer")

    seed = data.get("seed")
    edge_prob = float(data.get("edge_prob", 0.3))

    network = NetworkTopology(seed=seed)

    if topology == "mesh":
        network.create_mesh_topology(nodes)

    elif topology == "ring":
        network.create_ring_topology(nodes)

    elif topology == "star":
        network.create_star_topology(nodes)

    elif topology == "random":
        network.create_random_topology(
            nodes,
            p=edge_prob
        )

    else:
        raise ValueError(f"Unknown topology {topology}")

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
    
    result = simulate_network(
        network=network,
        algorithm_type=algorithm,
        traffic_intensity=traffic,
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
    
    result = compare_algorithms(
        network=network,
        traffic_intensity=traffic,
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