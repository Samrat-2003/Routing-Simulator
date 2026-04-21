import heapq
import random
import numpy as np
from collections import defaultdict

class RoutingAlgorithm:
    """Base class for routing algorithms"""
    def __init__(self, network):
        self.network = network
    
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

class ACORouting(RoutingAlgorithm):
    """Ant Colony Optimization based routing"""
    def __init__(self, network, alpha=1, beta=2, evaporation_rate=0.5, ants=10, iterations=20):
        super().__init__(network)
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
            rand_val = random.uniform(0, total_prob)
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
    def __init__(self, network, population_size=20, generations=30, mutation_rate=0.1):
        super().__init__(network)
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
                
                new_population.extend([child1, child2])
            
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
                next_node = random.choice(all_neighbors)
            else:
                next_node = random.choice(neighbors)
            
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
            tournament_indices = random.sample(range(len(population)), min(tournament_size, len(population)))
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            winner_index = tournament_indices[np.argmin(tournament_fitness)]
            selected.append(population[winner_index])
        return selected
    
    def _crossover(self, parent1, parent2):
        """Simple crossover operation"""
        if len(parent1) < 3 or len(parent2) < 3:
            return parent1, parent2
        
        # Single point crossover
        point1 = random.randint(1, len(parent1) - 2)
        point2 = random.randint(1, len(parent2) - 2)
        
        child1 = parent1[:point1] + [node for node in parent2[point2:] if node not in parent1[:point1]]
        child2 = parent2[:point2] + [node for node in parent1[point1:] if node not in parent2[:point2]]
        
        return child1, child2
    
    def _mutate(self, path, source, destination):
        """Mutate a path by swapping nodes or adding/removing nodes"""
        if len(path) < 3 or random.random() > self.mutation_rate:
            return path
        
        mutation_type = random.choice(['swap', 'insert', 'remove'])
        
        if mutation_type == 'swap' and len(path) > 3:
            # Swap two nodes (not source or destination)
            idx1, idx2 = random.sample(range(1, len(path)-1), 2)
            path[idx1], path[idx2] = path[idx2], path[idx1]
        elif mutation_type == 'insert':
            # Insert a random node
            available_nodes = [n for n in self.network.graph.nodes() if n not in path]
            if available_nodes:
                insert_pos = random.randint(1, len(path)-1)
                new_node = random.choice(available_nodes)
                path.insert(insert_pos, new_node)
        elif mutation_type == 'remove' and len(path) > 3:
            # Remove a node (not source or destination)
            remove_pos = random.randint(1, len(path)-2)
            path.pop(remove_pos)
        
        return path

# Factory function to create routing algorithm instances
def create_routing_algorithm(algorithm_name, network, **kwargs):
    """Factory function to create routing algorithm instances"""
    algorithms = {
        'dijkstra': DijkstraRouting,
        'bellman_ford': BellmanFordRouting,
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