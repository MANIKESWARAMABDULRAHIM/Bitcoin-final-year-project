import networkx as nx
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from django.conf import settings


def forensic_graph_analysis(transactions):
    G = nx.DiGraph()
    
    # Handle empty transactions
    if not transactions:
        G.graph['fraud_analysis'] = {
            'high_centrality_nodes': [],
            'large_amount_threshold': 0,
            'circular_flow_nodes': [],
            'rapid_exchange_pairs': [],
            'total_transactions': 0,
            'mean_amount': 0,
        }
        return G

    # Add edges
    amounts = []
    for tx in transactions:
        G.add_edge(tx.sender, tx.receiver, amount=tx.amount)
        amounts.append(tx.amount)

    # 1️⃣ Centrality Detection
    centrality = nx.betweenness_centrality(G)
    threshold_centrality = np.percentile(list(centrality.values()), 80)

    # 2️⃣ Large Amount Detection
    mean_amount = np.mean(amounts) if amounts else 0
    std_amount = np.std(amounts) if amounts else 0
    large_threshold = mean_amount + std_amount

    # 3️⃣ Circular Flow Detection
    cycles = list(nx.simple_cycles(G))
    nodes_in_cycles = set()
    for cycle in cycles:
        nodes_in_cycles.update(cycle)

    # 4️⃣ Rapid Back-and-Forth
    rapid_pairs = set()
    for u, v in G.edges():
        if G.has_edge(v, u):
            rapid_pairs.add((u, v))
            rapid_pairs.add((v, u))

    # Store analysis results for reporting
    G.graph['fraud_analysis'] = {
        'high_centrality_nodes': [n for n, c in centrality.items() if c > threshold_centrality],
        'large_amount_threshold': large_threshold,
        'circular_flow_nodes': list(nodes_in_cycles),
        'rapid_exchange_pairs': list(rapid_pairs)[:10],
        'total_transactions': len(amounts),
        'mean_amount': mean_amount,
    }

    # Mark suspicious edges with reasons
    for u, v in G.edges():
        G[u][v]["suspicious"] = False
        G[u][v]["reasons"] = []

        # Rule 1: High centrality sender
        if centrality.get(u, 0) > threshold_centrality:
            G[u][v]["suspicious"] = True
            G[u][v]["reasons"].append("High centrality - hub node")

        # Rule 2: Large amount
        if G[u][v]["amount"] > large_threshold:
            G[u][v]["suspicious"] = True
            G[u][v]["reasons"].append(f"Large amount (>{large_threshold:.4f} BTC)")

        # Rule 3: Circular flow
        if u in nodes_in_cycles:
            G[u][v]["suspicious"] = True
            G[u][v]["reasons"].append("Circular money flow detected")

        # Rule 4: Rapid back-and-forth
        if (u, v) in rapid_pairs:
            G[u][v]["suspicious"] = True
            G[u][v]["reasons"].append("Rapid back-and-forth transactions")

    return G


def extract_features(G):
    centrality = nx.degree_centrality(G)
    clustering = nx.clustering(G.to_undirected())

    nodes = list(G.nodes())
    features = []

    for node in nodes:
        features.append([
            centrality.get(node, 0),
            clustering.get(node, 0),
            G.degree(node)
        ])

    return nodes, features


def get_graph_json(G):
    """Export graph data as JSON for 3D visualization"""
    centrality = nx.betweenness_centrality(G)
    threshold = np.percentile(list(centrality.values()), 80) if centrality else 0
    
    nodes_data = []
    for i, node in enumerate(G.nodes()):
        total_amount = sum(G[u][v].get('amount', 0) for u, v in G.edges() if u == node or v == node)
        is_suspicious = any(G[u][v].get('suspicious', False) for u, v in G.edges() if u == node or v == node)
        reasons = []
        for u, v in G.edges():
            if u == node or v == node:
                if G[u][v].get('suspicious'):
                    reasons.extend(G[u][v].get('reasons', []))
        
        nodes_data.append({
            'id': node,
            'index': i,
            'centrality': round(centrality.get(node, 0), 4),
            'is_suspicious': is_suspicious,
            'reasons': list(set(reasons))[:3],
            'tx_count': G.degree(node),
            'total_amount': round(total_amount, 8)
        })
    
    edges_data = []
    for u, v in G.edges():
        edges_data.append({
            'source': u,
            'target': v,
            'amount': round(G[u][v].get('amount', 0), 8),
            'suspicious': G[u][v].get('suspicious', False),
            'reasons': G[u][v].get('reasons', [])
        })
    
    return {
        'nodes': nodes_data,
        'edges': edges_data,
        'fraud_analysis': G.graph.get('fraud_analysis', {})
    }
def draw_forensic_graph(G):
    """Generate 2D graph image and JSON for 3D visualization"""
    
    # Export JSON for 3D
    graph_json = get_graph_json(G)
    json_path = os.path.join(settings.MEDIA_ROOT, "graph_data.json")
    with open(json_path, 'w') as f:
        json.dump(graph_json, f, indent=2)
    
    pos = nx.spring_layout(G, seed=42)

    # Edge colors
    edge_colors = [
        "red" if G[u][v].get("suspicious", False) else "gray"
        for u, v in G.edges()
    ]

    # Centrality for risk detection
    centrality = nx.betweenness_centrality(G)
    threshold = np.percentile(list(centrality.values()), 80) if centrality else 0

    node_colors = []
    node_sizes = []
    node_labels = {}

    for node in G.nodes():
        tx_count = G.nodes[node].get("tx_count", 0)
        total_amount = G.nodes[node].get("total_amount", 0)

        # Node color - 3D effect
        if centrality[node] > threshold:
            node_colors.append("orange")
        else:
            node_colors.append("lightblue")

        # Node size based on total transaction amount
        node_sizes.append(1200 + total_amount * 0.03)

        # Detailed label
        node_labels[node] = (
            f"{node}\n"
            f"Tx: {tx_count}\n"
            f"Total: ₹{total_amount}"
        )

    # Edge amount labels
    edge_labels = {
        (u, v): f"₹{G[u][v].get('amount', 0)}"
        for u, v in G.edges()
    }

    plt.figure(figsize=(15, 11))

    # Draw nodes and edges
    nx.draw(
        G,
        pos,
        labels=node_labels,
        node_color=node_colors,
        edge_color=edge_colors,
        node_size=node_sizes,
        font_size=7,
        font_weight="bold"
    )

    # Draw edge labels (transaction amount)
    nx.draw_networkx_edge_labels(
        G,
        pos,
        edge_labels=edge_labels,
        font_size=8
    )

    plt.title("Blockchain Forensic Risk Graph (With Transaction Amounts)")

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    file_path = os.path.join(settings.MEDIA_ROOT, "forensic_graph.png")
    plt.savefig(file_path, bbox_inches="tight", dpi=300)
    plt.close()

    return settings.MEDIA_URL + "forensic_graph.png", settings.MEDIA_URL + "graph_data.json"
