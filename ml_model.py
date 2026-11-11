def analyze(request):
    last_address = request.session.get("last_address", None)

    if not last_address:
        return render(request, "investigation/result.html", {
            "wallets": [],
            "fraud_analysis": {}
        })

    # Get transactions for the wallet network
    transactions = Transaction.objects.filter(
        Q(sender=last_address) | Q(receiver=last_address)
    )

    if not transactions.exists():
        return render(request, "investigation/result.html", {
            "wallets": [],
            "fraud_analysis": {
                'total_transactions': 0,
                'high_centrality_nodes': [],
                'circular_flow_nodes': [],
                'rapid_exchange_pairs': []
            }
        })

    # Analyze the graph
    G = forensic_graph_analysis(transactions)
    
    # Get graph data for both 2D and 3D visualization
    graph_url, json_url = draw_forensic_graph(G)
    nodes, features = extract_features(G)
    
    # Get predictions from ML model
    predictions = predict(features)
    
    # Convert predictions to list if it's a numpy array
    if hasattr(predictions, 'tolist'):
        predictions = predictions.tolist()
    else:
        predictions = list(predictions)
    
    # Ensure we have predictions for all nodes
    while len(predictions) < len(nodes):
        predictions.append(0)  # Pad with safe (0) if needed
    predictions = predictions[:len(nodes)]  # Truncate if too many

    # Get fraud analysis details
    fraud_analysis = G.graph.get('fraud_analysis', {})

    print("Nodes:", nodes)
    print("Features:", features)
    print("Raw Predictions:", predictions)

    # Clear existing wallets
    Wallet.objects.all().delete()

    # Create wallet records with detailed fraud reasons
    wallet_details = []
    for i, node in enumerate(nodes):
        # Count total transactions
        total_tx = Transaction.objects.filter(
            Q(sender=node) | Q(receiver=node)
        ).count()

        # Count suspicious transactions
        suspicious_tx = Transaction.objects.filter(
            Q(sender=node) | Q(receiver=node),
            suspicious=True
        ).count()

        # Genuine transactions
        genuine_tx = total_tx - suspicious_tx
        
        # Get fraud reasons for this wallet
        wallet_reasons = []
        for u, v, data in G.edges(data=True):
            if u == node or v == node:
                if data.get('suspicious', False):
                    reasons = data.get('reasons', [])
                    if reasons:
                        wallet_reasons.extend(reasons)
        
        # Get prediction value (0 = safe, 1 = suspicious)
        pred_value = predictions[i]
        is_suspicious = bool(pred_value)  # Convert 0 to False, 1 to True
        
        # Add default reason based on prediction
        if is_suspicious and not wallet_reasons:
            wallet_reasons.append("Flagged by ML model")
        elif not is_suspicious and not wallet_reasons:
            wallet_reasons.append("Normal transaction patterns")
        
        wallet = Wallet.objects.create(
            address=node,
            centrality=features[i][0] if len(features[i]) > 0 else 0.0,
            clustering=features[i][1] if len(features[i]) > 1 else 0.0,
            total_transactions=total_tx,
            suspicious_transaction_count=suspicious_tx,
            genuine_transaction_count=genuine_tx,
            suspicious=is_suspicious  # This will be True for 1, False for 0
        )
        
        wallet_details.append({
            'wallet': wallet,
            'reasons': list(set(wallet_reasons))[:3]
        })

    # Count for debugging
    suspicious_count = sum(1 for w in Wallet.objects.all() if w.suspicious)
    safe_count = Wallet.objects.count() - suspicious_count
    print(f"Total wallets: {Wallet.objects.count()}, Suspicious: {suspicious_count}, Safe: {safe_count}")

    return render(request, "investigation/result.html", {
        "wallets": Wallet.objects.all(),
        "wallet_details": wallet_details,
        "graph_url": graph_url,
        "json_url": json_url,
        "fraud_analysis": fraud_analysis,
        "suspicious_count": suspicious_count,
        "safe_count": safe_count
    })