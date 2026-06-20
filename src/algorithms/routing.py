import heapq
import math
import random
from collections import defaultdict

import networkx as nx
import numpy as np

class RoutingAlgorithm:
    """Base class for routing algorithms"""
    def __init__(self, network, seed=None):
        self.network = network
        self.seed = seed
        self.random = random.Random(seed)

    def route(self, source, destination):
        raise NotImplementedError("Subclasses must implement route method")

class DijkstraRouting(RoutingAlgorithm):
    """Dijkstra's shortest path algorithm"""
    def route(self, source, destination):
        try:
            path = self._dijkstra(source, destination)
            return path
        except Exception as e:
            print(f"Dijkstra routing failed: {e}")
            return None
    
    def _dijkstra(self, source, destination):
        """Implementation of Dijkstra's algorithm"""
        graph = self.network.graph
        distances = {node: float('infinity') for node in graph.nodes()}
        previous = {node: None for node in graph.nodes()}
        distances[source] = 0
        visited = set()
        
        priority_queue = [(0, source)]
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited:
                continue
                
            visited.add(current_node)
            
            if current_node == destination:
                break
                
            for neighbor in graph.neighbors(current_node):
                edge_weight = graph[current_node][neighbor].get('weight', 1)
                distance = current_distance + edge_weight
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))
        
        # Reconstruct path
        path = []
        current = destination
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()
        
        return path if path[0] == source else None

class BellmanFordRouting(RoutingAlgorithm):
    """Bellman-Ford algorithm implementation"""
    def route(self, source, destination):
        try:
            path = self._bellman_ford(source, destination)
            return path
        except Exception as e:
            print(f"Bellman-Ford routing failed: {e}")
            return None
    
    def _bellman_ford(self, source, destination):
        """Implementation of Bellman-Ford algorithm"""
        graph = self.network.graph
        distances = {node: float('infinity') for node in graph.nodes()}
        previous = {node: None for node in graph.nodes()}
        distances[source] = 0
        
        # Relax edges repeatedly
        for _ in range(len(graph.nodes()) - 1):
            for u, v, data in graph.edges(data=True):
                weight = data.get('weight', 1)
                if distances[u] != float('infinity') and distances[u] + weight < distances[v]:
                    distances[v] = distances[u] + weight
                    previous[v] = u
                    
                # Also check reverse direction for undirected graph
                if distances[v] != float('infinity') and distances[v] + weight < distances[u]:
                    distances[u] = distances[v] + weight
                    previous[u] = v
        
        # Reconstruct path
        path = []
        current = destination
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()
        
        return path if path[0] == source else None

class PCAMRRouting(RoutingAlgorithm):
    """PCA-MR+: Predictive Congestion-Aware Multipath Routing.

    PCA-MR uses a dynamic link metric:
        psi = alpha * normalized_weight
              + beta  * [-ln(1 - packet_loss)]
              + gamma * congestion_penalty(load_ratio)

    Fixes applied after empirical testing across many scenarios:

    1. normalized_weight now reads the edge's static `base_weight`
       instead of the live `weight` field. The analyzer already
       inflates `weight` for congestion after every routed flow, so
       reading it here was double-counting congestion on top of the
       gamma term below, which tracks the same thing independently.

    2. congestion_penalty no longer grows linearly from zero. A link
       at 30% utilization has no real drop risk, so it shouldn't cost
       anything. The penalty is zero below `congestion_threshold`
       (0.85, matching the "congested edge" cutoff used elsewhere in
       this project) and grows quadratically above it, reaching
       exactly `gamma` at 100% utilization and continuing to climb for
       genuine overload. This makes PCA-MR only divert traffic when a
       link is actually becoming risky, instead of paying a latency
       tax for harmless headroom.
    """

    def __init__(
        self,
        network,
        alpha=0.35,
        beta=0.4,
        gamma=0.6,
        prediction_smoothing=0.7,
        congestion_threshold=0.85,
        candidate_paths=4,
        seed=None,
    ):
        super().__init__(network, seed=seed)
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.prediction_smoothing = prediction_smoothing
        self.congestion_threshold = congestion_threshold
        self.candidate_paths = candidate_paths
        self.edge_loads = defaultdict(float)
        self.predicted_costs = {}
        self.current_packet_size = 1.0
        self._max_base_weight = 1.0
        self._adaptive_alpha = alpha
        self._adaptive_beta = beta
        self._adaptive_gamma = gamma

    def set_current_flow(self, flow):
        """Expose the next demand size before route selection."""
        self.current_packet_size = max(float(getattr(flow, "size", 1.0) or 1.0), 0.0)

    def update_edge_load(self, path, packet_size=None):
        """Record routed demand so later flows can avoid hot links."""
        if not path or len(path) < 2:
            return

        demand = self.current_packet_size if packet_size is None else max(float(packet_size or 0.0), 0.0)
        for i in range(len(path) - 1):
            self.edge_loads[self._edge_key(path[i], path[i + 1])] += demand

    def route(self, source, destination):
        try:
            if source == destination:
                return [source]
            if source not in self.network.graph or destination not in self.network.graph:
                return None

            self._refresh_predicted_costs()
            return self._select_best_candidate_path(source, destination)
        except Exception as e:
            print(f"PCA-MR routing failed: {e}")
            return None

    def _select_best_candidate_path(self, source, destination):
        paths = self._candidate_paths(source, destination)
        if not paths:
            return self._dynamic_dijkstra(source, destination)

        return min(paths, key=self._path_score)

    def _candidate_paths(self, source, destination):
        def edge_weight(u, v, _data):
            return self.predicted_costs.get(
                self._edge_key(u, v),
                self._current_edge_cost(u, v),
            )

        try:
            path_iterator = nx.shortest_simple_paths(
                self.network.graph,
                source,
                destination,
                weight=edge_weight,
            )
            paths = []
            for path in path_iterator:
                paths.append(path)
                if len(paths) >= max(1, int(self.candidate_paths)):
                    break
            return paths
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def _path_score(self, path):
        if not path or len(path) < 2:
            return float("infinity")

        edge_cost = 0.0
        path_success_probability = 1.0
        max_load_ratio = 0.0

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if not self.network.graph.has_edge(u, v):
                return float("infinity")
            key = self._edge_key(u, v)
            edge = self.network.graph[u][v]
            edge_cost += self.predicted_costs.get(key, self._current_edge_cost(u, v))
            path_success_probability *= 1.0 - self._loss_probability(u, v, edge)
            max_load_ratio = max(max_load_ratio, self._projected_load_ratio(u, v, edge))

        loss_risk = -math.log(max(path_success_probability, 1e-9))
        bottleneck_penalty = self._congestion_penalty(max_load_ratio)
        hop_penalty = 0.01 * (len(path) - 1)

        return (
            edge_cost
            + self._adaptive_beta * loss_risk
            + self._adaptive_gamma * bottleneck_penalty
            + hop_penalty
        )

    def _dynamic_dijkstra(self, source, destination):
        graph = self.network.graph
        distances = {node: float("infinity") for node in graph.nodes()}
        previous = {node: None for node in graph.nodes()}
        distances[source] = 0
        priority_queue = [(0, source)]
        visited = set()

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            if current_node in visited:
                continue

            visited.add(current_node)
            if current_node == destination:
                break

            for neighbor in graph.neighbors(current_node):
                edge_cost = self.predicted_costs.get(
                    self._edge_key(current_node, neighbor),
                    self._current_edge_cost(current_node, neighbor),
                )
                distance = current_distance + edge_cost

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))

        path = []
        current = destination
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()

        return path if path and path[0] == source else None

    def _refresh_predicted_costs(self):
        base_weights = [
            max(float(data.get("base_weight", data.get("weight", 1.0))), 0.0)
            for _, _, data in self.network.graph.edges(data=True)
        ]
        self._max_base_weight = max(base_weights, default=1.0) or 1.0
        self._adaptive_alpha, self._adaptive_beta, self._adaptive_gamma = self._adaptive_weights()

        for u, v in self.network.graph.edges():
            key = self._edge_key(u, v)
            current_cost = self._current_edge_cost(u, v)
            previous_cost = self.predicted_costs.get(key, current_cost)
            self.predicted_costs[key] = (
                self.prediction_smoothing * current_cost
                + (1 - self.prediction_smoothing) * previous_cost
            )

    def _current_edge_cost(self, u, v):
        edge = self.network.graph[u][v]
        normalized_weight = self._normalized_weight(edge)
        loss = self._loss_probability(u, v, edge)
        loss_penalty = -math.log(max(1.0 - loss, 1e-9))
        load_ratio = self._projected_load_ratio(u, v, edge)
        congestion_penalty = self._congestion_penalty(load_ratio)

        return (
            self._adaptive_alpha * normalized_weight
            + self._adaptive_beta * loss_penalty
            + self._adaptive_gamma * congestion_penalty
        )

    def _adaptive_weights(self):
        graph = self.network.graph
        if graph.number_of_edges() == 0:
            return self.alpha, self.beta, self.gamma

        load_ratios = [
            self._projected_load_ratio(u, v, data)
            for u, v, data in graph.edges(data=True)
        ]
        losses = [
            self._loss_probability(u, v, data)
            for u, v, data in graph.edges(data=True)
        ]

        max_load = max(load_ratios, default=0.0)
        avg_load = sum(load_ratios) / len(load_ratios) if load_ratios else 0.0
        max_loss = max(losses, default=0.0)
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        overload = max(0.0, max_load - self.congestion_threshold)
        headroom = max(1.0 - self.congestion_threshold, 1e-6)

        alpha = self.alpha
        beta = self.beta * (1.0 + 2.5 * max_loss + avg_loss)
        gamma = self.gamma * (1.0 + 3.0 * (overload / headroom) + avg_load)

        if max_loss >= 0.15:
            alpha *= 0.75
        if max_load >= self.congestion_threshold:
            alpha *= 0.65

        total = alpha + beta + gamma
        if total <= 0:
            return self.alpha, self.beta, self.gamma
        return alpha / total, beta / total, gamma / total

    def _normalized_weight(self, edge):
        base = max(float(edge.get("base_weight", edge.get("weight", 1.0))), 0.0)
        return base / self._max_base_weight

    def _congestion_penalty(self, load_ratio):
        """Zero below the congestion threshold; grows quadratically
        above it, reaching 1.0 (so `gamma` itself) at full capacity and
        climbing further into genuine overload."""
        if load_ratio <= self.congestion_threshold:
            return 0.0
        headroom = max(1.0 - self.congestion_threshold, 1e-6)
        scaled_overload = (load_ratio - self.congestion_threshold) / headroom
        quadratic_penalty = scaled_overload ** 2
        logarithmic_penalty = -math.log(max(1.0 - min(load_ratio, 0.999999), 1e-9))
        return quadratic_penalty + logarithmic_penalty

    def _loss_probability(self, u, v, edge):
        loss = max(
            float(edge.get("packet_loss", 0.0)),
            float(self.network.graph.nodes[u].get("packet_loss", 0.0)),
            float(self.network.graph.nodes[v].get("packet_loss", 0.0)),
        )
        return min(max(loss, 0.0), 0.999999)

    def _projected_load_ratio(self, u, v, edge):
        bandwidth = max(float(edge.get("bandwidth", 100.0)), 1.0)
        projected_load = self.edge_loads[self._edge_key(u, v)] + self.current_packet_size
        return projected_load / bandwidth

    def _edge_key(self, u, v):
        return (min(u, v), max(u, v))

class ACORouting(RoutingAlgorithm):
    """Ant Colony Optimization based routing"""
    def __init__(self, network, alpha=1, beta=2, evaporation_rate=0.5, ants=10, iterations=20, seed=None):
        super().__init__(network, seed=seed)
        self.alpha = alpha  # pheromone importance
        self.beta = beta    # heuristic importance
        self.evaporation_rate = evaporation_rate
        self.ants = ants
        self.iterations = iterations
        self.pheromones = defaultdict(lambda: defaultdict(float))
        self._initialize_pheromones()
    
    def _initialize_pheromones(self):
        """Initialize pheromone trails"""
        graph = self.network.graph
        for u, v in graph.edges():
            self.pheromones[u][v] = 1.0
            self.pheromones[v][u] = 1.0  # For undirected graph
    
    def route(self, source, destination):
        try:
            best_path = self._aco_optimization(source, destination)
            if best_path is None:
                # Genuine failure — don't mask it with Dijkstra
                return None
            return best_path
        except Exception as e:
            print(f"ACO routing failed: {e}")
            return None
    
    def _aco_optimization(self, source, destination):
        """Run ACO optimization"""
        best_path = None
        best_cost = float('infinity')
        
        for _ in range(self.iterations):
            # Each ant finds a path
            ant_paths = []
            for _ in range(self.ants):
                path = self._ant_walk(source, destination)
                if path:
                    cost = self._calculate_path_cost(path)
                    ant_paths.append((path, cost))
                    
                    # Update best path if this is better
                    if cost < best_cost:
                        best_cost = cost
                        best_path = path
            
            # Update pheromones
            self._update_pheromones(ant_paths)
        
        return best_path
    
    def _ant_walk(self, source, destination):
        """Single ant walks from source to destination"""
        current = source
        path = [current]
        visited = {current}
        
        while current != destination:
            # Get neighbors
            neighbors = [n for n in self.network.graph.neighbors(current) if n not in visited]
            if not neighbors:
                return None  # Dead end
            
            # Calculate probabilities
            probabilities = []
            total_prob = 0
            
            for neighbor in neighbors:
                pheromone = self.pheromones[current][neighbor]
                weight = self.network.graph[current][neighbor].get('weight', 1)
                heuristic = 1.0 / weight if weight > 0 else 1.0
                
                prob = (pheromone ** self.alpha) * (heuristic ** self.beta)
                probabilities.append((neighbor, prob))
                total_prob += prob
            
            # Normalize probabilities
            if total_prob == 0:
                return None
                
            # Select next node based on probability
            rand_val = self.random.uniform(0, total_prob)
            cum_prob = 0
            
            for neighbor, prob in probabilities:
                cum_prob += prob
                if rand_val <= cum_prob:
                    current = neighbor
                    path.append(current)
                    visited.add(current)
                    break
        
        return path
    
    def _calculate_path_cost(self, path):
        """Calculate total cost of a path"""
        cost = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            cost += self.network.graph[u][v].get('weight', 1)
        return cost
    
    def _update_pheromones(self, ant_paths):
        """Update pheromone trails based on ant paths"""
        # Evaporation
        for u in self.pheromones:
            for v in self.pheromones[u]:
                self.pheromones[u][v] *= (1 - self.evaporation_rate)
        
        # Deposit new pheromones
        for path, cost in ant_paths:
            if path and cost > 0:
                deposit = 1.0 / cost
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    self.pheromones[u][v] += deposit
                    self.pheromones[v][u] += deposit  # For undirected graph

class GARouting(RoutingAlgorithm):
    """Genetic Algorithm based routing"""
    def __init__(self, network, population_size=20, generations=30, mutation_rate=0.1, seed=None):
        super().__init__(network, seed=seed)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
    
    def route(self, source, destination):
        try:
            best_path = self._genetic_optimization(source, destination)
            if best_path is None:
                return None
            return best_path
        except Exception as e:
            print(f"GA routing failed: {e}")
            return None
    
    def _genetic_optimization(self, source, destination):
        """Run genetic algorithm optimization"""
        # Initialize population
        population = self._initialize_population(source, destination)
        if not population:
            return None
        
        best_path = None
        best_fitness = float('infinity')
        
        for _ in range(self.generations):
            # Evaluate fitness
            fitness_scores = [self._fitness(individual) for individual in population]
            
            # Track best solution
            min_fitness_idx = np.argmin(fitness_scores)
            if fitness_scores[min_fitness_idx] < best_fitness:
                best_fitness = fitness_scores[min_fitness_idx]
                best_path = population[min_fitness_idx]
            
            # Selection
            selected = self._selection(population, fitness_scores)
            
            # Crossover and mutation
            new_population = []
            for i in range(0, len(selected), 2):
                parent1 = selected[i]
                parent2 = selected[i+1] if i+1 < len(selected) else selected[0]
                
                child1, child2 = self._crossover(parent1, parent2)
                child1 = self._mutate(child1, source, destination)
                child2 = self._mutate(child2, source, destination)

                repaired_child1 = self._repair_path(child1, source, destination)
                repaired_child2 = self._repair_path(child2, source, destination)
                if repaired_child1:
                    new_population.append(repaired_child1)
                if repaired_child2:
                    new_population.append(repaired_child2)
            
            if new_population:
                population = new_population[:self.population_size]
        
        return best_path
    
    def _initialize_population(self, source, destination):
        """Create initial population of paths"""
        population = []
        for _ in range(self.population_size):
            path = self._random_path(source, destination)
            if path:
                population.append(path)
        return population

    def _repair_path(self, path, source, destination):
        """Repair a mutated or crossed-over path into a valid simple route."""
        if not path:
            return self._random_path(source, destination)

        cleaned = []
        seen = set()
        for node in path:
            if node not in self.network.graph:
                continue
            if cleaned and node == cleaned[-1]:
                continue
            if node in seen:
                loop_start = cleaned.index(node)
                cleaned = cleaned[:loop_start + 1]
                seen = set(cleaned)
                continue
            cleaned.append(node)
            seen.add(node)

        if not cleaned or cleaned[0] != source:
            cleaned.insert(0, source)
        if cleaned[-1] != destination:
            cleaned.append(destination)

        repaired = [cleaned[0]]
        for next_node in cleaned[1:]:
            current = repaired[-1]
            if current == next_node:
                continue
            if self.network.graph.has_edge(current, next_node):
                repaired.append(next_node)
                continue

            try:
                bridge = self.network.get_shortest_path(current, next_node)
            except Exception:
                bridge = None

            if not bridge:
                try:
                    bridge = self.network.get_shortest_path(current, destination)
                except Exception:
                    bridge = None

            if not bridge:
                return self._random_path(source, destination)

            repaired.extend(bridge[1:])
            if repaired[-1] == destination:
                break

        if repaired[-1] != destination:
            try:
                tail = self.network.get_shortest_path(repaired[-1], destination)
            except Exception:
                tail = None
            if not tail:
                return self._random_path(source, destination)
            repaired.extend(tail[1:])

        final_path = []
        for node in repaired:
            if node in final_path:
                loop_start = final_path.index(node)
                final_path = final_path[:loop_start + 1]
            else:
                final_path.append(node)

        return final_path if self._fitness(final_path) != float('infinity') else self._random_path(source, destination)
    
    def _random_path(self, source, destination):
        """Generate a random path from source to destination"""
        if source == destination:
            return [source]
        
        visited = {source}
        path = [source]
        current = source
        
        max_attempts = len(self.network.graph.nodes()) * 2
        attempts = 0
        
        while current != destination and attempts < max_attempts:
            neighbors = [n for n in self.network.graph.neighbors(current) if n not in visited]
            if not neighbors:
                # Try to find alternative path
                all_neighbors = list(self.network.graph.neighbors(current))
                if not all_neighbors:
                    return None
                next_node = self.random.choice(all_neighbors)
            else:
                next_node = self.random.choice(neighbors)
            
            path.append(next_node)
            visited.add(next_node)
            current = next_node
            attempts += 1
        
        return path if current == destination else None
    
    def _fitness(self, path):
        """Calculate fitness of a path (lower is better)"""
        if not path or len(path) < 2:
            return float('infinity')
        
        cost = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            if self.network.graph.has_edge(u, v):
                cost += self.network.graph[u][v].get('weight', 1)
            else:
                return float('infinity')  # Invalid path
        return cost
    
    def _selection(self, population, fitness_scores):
        """Select individuals for reproduction using tournament selection"""
        selected = []
        for _ in range(len(population)):
            # Tournament selection
            tournament_size = 3
            tournament_indices = self.random.sample(range(len(population)), min(tournament_size, len(population)))
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            winner_index = tournament_indices[np.argmin(tournament_fitness)]
            selected.append(population[winner_index])
        return selected
    
    def _crossover(self, parent1, parent2):
        """Simple crossover operation"""
        if len(parent1) < 3 or len(parent2) < 3:
            return parent1, parent2
        
        # Single point crossover
        point1 = self.random.randint(1, len(parent1) - 2)
        point2 = self.random.randint(1, len(parent2) - 2)
        
        child1 = parent1[:point1] + [node for node in parent2[point2:] if node not in parent1[:point1]]
        child2 = parent2[:point2] + [node for node in parent1[point1:] if node not in parent2[:point2]]
        
        return child1, child2
    
    def _mutate(self, path, source, destination):
        """Mutate a path by swapping nodes or adding/removing nodes"""
        if len(path) < 3 or self.random.random() > self.mutation_rate:
            return path

        mutation_type = self.random.choice(['swap', 'insert', 'remove'])

        if mutation_type == 'swap' and len(path) > 3:
            # Swap two nodes (not source or destination)
            idx1, idx2 = self.random.sample(range(1, len(path)-1), 2)
            path[idx1], path[idx2] = path[idx2], path[idx1]
        elif mutation_type == 'insert':
            # Insert a random node
            available_nodes = [n for n in self.network.graph.nodes() if n not in path]
            if available_nodes:
                insert_pos = self.random.randint(1, len(path)-1)
                new_node = self.random.choice(available_nodes)
                path.insert(insert_pos, new_node)
        elif mutation_type == 'remove' and len(path) > 3:
            # Remove a node (not source or destination)
            remove_pos = self.random.randint(1, len(path)-2)
            path.pop(remove_pos)
        
        return self._repair_path(path, source, destination)

# Factory function to create routing algorithm instances
def create_routing_algorithm(algorithm_name, network, **kwargs):
    """Factory function to create routing algorithm instances"""
    algorithms = {
        'dijkstra': DijkstraRouting,
        'bellman_ford': BellmanFordRouting,
        'pca_mr': PCAMRRouting,
        'aco': ACORouting,
        'ga': GARouting
    }
    
    if algorithm_name.lower() not in algorithms:
        raise ValueError(f"Unknown algorithm: {algorithm_name}")
    
    return algorithms[algorithm_name.lower()](network, **kwargs)

# Example usage
if __name__ == "__main__":
    from src.network.topology import NetworkTopology
    
    # Create network
    net = NetworkTopology()
    net.create_mesh_topology(5)
    
    # Test algorithms
    dijkstra = DijkstraRouting(net)
    path = dijkstra.route(0, 4)
    print("Dijkstra path:", path)
