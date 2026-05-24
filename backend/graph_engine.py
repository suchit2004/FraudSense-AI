import networkx as nx
from collections import deque
import threading

class GraphEngine:
    def __init__(self, max_edges: int = 2000):
        self.lock = threading.Lock()
        self.max_edges = max_edges
        self.graph = nx.DiGraph()
        # Keep track of edge records to perform sliding window removal: (sender, receiver, timestamp)
        self.edge_records = deque()

    def add_transaction(self, sender: str, receiver: str, amount: float, timestamp: float):
        """Adds a transaction edge to the network graph, maintaining the sliding window size."""
        with self.lock:
            # Add edge or update amount
            if self.graph.has_edge(sender, receiver):
                self.graph[sender][receiver]['amount'] += amount
                self.graph[sender][receiver]['count'] += 1
                self.graph[sender][receiver]['timestamps'].append(timestamp)
            else:
                self.graph.add_edge(sender, receiver, amount=amount, count=1, timestamps=[timestamp])
            
            self.edge_records.append((sender, receiver, timestamp))
            
            # Prune old edges if limit exceeded
            while len(self.edge_records) > self.max_edges:
                old_sender, old_receiver, _ = self.edge_records.popleft()
                if self.graph.has_edge(old_sender, old_receiver):
                    # If there was only 1 transaction, remove edge. Otherwise, decrement count
                    if self.graph[old_sender][old_receiver]['count'] <= 1:
                        self.graph.remove_edge(old_sender, old_receiver)
                    else:
                        self.graph[old_sender][old_receiver]['count'] -= 1
                        if self.graph[old_sender][old_receiver]['timestamps']:
                            self.graph[old_sender][old_receiver]['timestamps'].pop(0)
                
                # Clean up isolated nodes (nodes with 0 degree)
                for node in [old_sender, old_receiver]:
                    if self.graph.has_node(node) and self.graph.degree(node) == 0:
                        self.graph.remove_node(node)

    def detect_cycles(self, max_cycle_length: int = 5) -> list[list[str]]:
        """
        Finds directed cycles in the graph, representing money round-tripping.
        To avoid performance bottlenecks on large graphs, we find simple cycles
        within strongly connected components.
        """
        cycles = []
        with self.lock:
            try:
                # Find strongly connected components with size > 1
                sccs = [scc for scc in nx.strongly_connected_components(self.graph) if len(scc) > 1]
                for scc in sccs:
                    subgraph = self.graph.subgraph(scc)
                    # Get simple cycles in subgraph
                    for cycle in nx.simple_cycles(subgraph):
                        if len(cycle) <= max_cycle_length:
                            cycles.append(cycle)
                        if len(cycles) >= 10:  # Cap the number of cycles returned to prevent lag
                            break
                    if len(cycles) >= 10:
                        break
            except Exception:
                pass
        return cycles

    def is_in_cycle(self, node: str) -> bool:
        """Checks if a specific VPA node is part of any active transaction loop."""
        with self.lock:
            if not self.graph.has_node(node):
                return False
            try:
                return any(node in cycle for cycle in nx.simple_cycles(self.graph.subgraph(nx.descendants(self.graph, node) | {node})))
            except Exception:
                return False

    def detect_mule_nodes(self, top_n: int = 5) -> list[dict]:
        """
        Identifies money mules. A mule typically:
        1. Has high In-Degree (receives money from many accounts).
        2. Has high Out-Degree (immediately forwards it to others).
        3. Ratio of money coming in vs going out is close to 1.
        4. Alternatively acts as a pure 'sink' (high PageRank, but 0 out-degree).
        """
        mules = []
        with self.lock:
            if self.graph.number_of_nodes() < 3:
                return []
            
            try:
                pagerank = nx.pagerank(self.graph, alpha=0.85, weight='amount')
                in_degrees = dict(self.graph.in_degree())
                out_degrees = dict(self.graph.out_degree())
                
                for node in self.graph.nodes():
                    in_deg = in_degrees.get(node, 0)
                    out_deg = out_degrees.get(node, 0)
                    pr = pagerank.get(node, 0)
                    
                    # Calculate net flow behavior:
                    # An account receiving from multiple sources and sending to others
                    if in_deg >= 2 and out_deg >= 1:
                        # Mule score is proportional to in-degree and pagerank
                        score = pr * in_deg
                        mules.append({
                            'vpa': node,
                            'score': float(score),
                            'in_degree': in_deg,
                            'out_degree': out_deg,
                            'reason': "Layering Node (High In-Degree and Out-Degree)"
                        })
                    elif in_deg >= 3 and out_deg == 0:
                        # Direct sink account
                        score = pr * in_deg * 1.5
                        mules.append({
                            'vpa': node,
                            'score': float(score),
                            'in_degree': in_deg,
                            'out_degree': out_deg,
                            'reason': "Sink Account (Collects from many sources)"
                        })
                
                # Sort by score descending
                mules = sorted(mules, key=lambda x: x['score'], reverse=True)[:top_n]
            except Exception:
                pass
        return mules

    def get_neighborhood(self, node: str, depth: int = 1) -> dict:
        """
        Returns JSON-serializable node and edge lists of the ego-network around a node.
        Useful for rendering local transaction graphs in UI.
        """
        with self.lock:
            if not self.graph.has_node(node):
                return {'nodes': [], 'links': []}
                
            # Create ego graph
            ego = nx.ego_graph(self.graph, node, radius=depth, undirected=True)
            
            nodes_list = []
            for n in ego.nodes():
                nodes_list.append({
                    'id': n,
                    'label': n,
                    'is_target': n == node,
                    'degree': ego.degree(n)
                })
                
            links_list = []
            for u, v, data in ego.edges(data=True):
                links_list.append({
                    'source': u,
                    'target': v,
                    'amount': float(data.get('amount', 0.0)),
                    'count': data.get('count', 1)
                })
                
            return {'nodes': nodes_list, 'links': links_list}

    def get_full_graph_data(self) -> dict:
        """Returns the complete network nodes and edges for visualization."""
        with self.lock:
            nodes_list = [{'id': n, 'label': n, 'degree': self.graph.degree(n)} for n in self.graph.nodes()]
            links_list = []
            for u, v, data in self.graph.edges(data=True):
                links_list.append({
                    'source': u,
                    'target': v,
                    'amount': float(data.get('amount', 0.0))
                })
            return {'nodes': nodes_list, 'links': links_list}

    def clear(self):
        """Clears the graph network."""
        with self.lock:
            self.graph.clear()
            self.edge_records.clear()
