from django.shortcuts import render, redirect
from .forms import WalletFetchForm
from .models import Transaction, Wallet
from .blockchain_service import fetch_wallet_transactions
from .graph_analysis import draw_forensic_graph, extract_features, forensic_graph_analysis
from .ml_model import predict
from .report_generator import generate_pdf
from django.db.models import Q
from django.http import FileResponse

def home(request):
    return render(request, "investigation/home.html")

def wallet(request):
    wallets = Wallet.objects.all()
    return render(request, "investigation/wallet.html", {"wallets": wallets})

def fetch_wallet(request):
    if request.method == "POST":
        form = WalletFetchForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data["wallet_address"]
            tx_data = fetch_wallet_transactions(address)

            if tx_data:
                for tx in tx_data:
                    Transaction.objects.get_or_create(
                        sender=tx["sender"],
                        receiver=tx["receiver"],
                        amount=tx["amount"]
                    )
                    request.session["last_address"] = address
                
                return redirect("analyze")
    else:
        form = WalletFetchForm()

    return render(request, "investigation/fetch_wallet.html", {"form": form})

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
    
    # Ensure predictions are properly formatted as boolean values
    # Convert predictions to boolean if they're not already
    if predictions is not None and len(predictions) > 0:
        # If predictions are probabilities, convert to binary (0 or 1)
        # Assuming 0 = safe, 1 = suspicious
        predictions = [bool(pred) for pred in predictions]
    else:
        # If no predictions, default to False for all nodes
        predictions = [False] * len(nodes)

    # Get fraud analysis details
    fraud_analysis = G.graph.get('fraud_analysis', {})

    print("Nodes:", nodes)
    print("Features:", features)
    print("Predictions:", predictions)

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
        for u, v in G.edges():
            if u == node or v == node:
                edge_data = G.get_edge_data(u, v)
                if edge_data and edge_data.get('suspicious'):
                    reasons = edge_data.get('reasons', [])
                    if reasons:
                        wallet_reasons.extend(reasons)
        
        # Determine if wallet is suspicious based on prediction
        is_suspicious = predictions[i] if i < len(predictions) else False
        
        # If suspicious, add a default reason if none found
        if is_suspicious and not wallet_reasons:
            wallet_reasons.append("Flagged by ML model based on transaction patterns")
        
        wallet = Wallet.objects.create(
            address=node,
            centrality=features[i][0] if len(features[i]) > 0 else 0.0,
            clustering=features[i][1] if len(features[i]) > 1 else 0.0,
            total_transactions=total_tx,
            suspicious_transaction_count=suspicious_tx,
            genuine_transaction_count=genuine_tx,
            suspicious=is_suspicious  # Use the prediction value
        )
        
        wallet_details.append({
            'wallet': wallet,
            'reasons': list(set(wallet_reasons))[:3]  # Get unique reasons, limit to 3
        })

    # Count suspicious and safe wallets
    suspicious_count = sum(1 for w in Wallet.objects.all() if w.suspicious)
    safe_count = Wallet.objects.count() - suspicious_count
    
    print(f"Total wallets: {Wallet.objects.count()}")
    print(f"Suspicious: {suspicious_count}")
    print(f"Safe: {safe_count}")

    return render(request, "investigation/result.html", {
        "wallets": Wallet.objects.all(),
        "wallet_details": wallet_details,
        "graph_url": graph_url,
        "json_url": json_url,
        "fraud_analysis": fraud_analysis,
        "suspicious_count": suspicious_count,
        "safe_count": safe_count
    })

def export_pdf(request):
    wallets = Wallet.objects.all()
    file_path, filename = generate_pdf(wallets, fraud_analysis={}, wallet_details=[])

    response = FileResponse(open(file_path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response