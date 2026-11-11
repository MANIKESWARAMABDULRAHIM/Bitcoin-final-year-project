import requests


def fetch_wallet_transactions(address):
    url = f"https://blockchain.info/rawaddr/{address}?limit=5"
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    transactions = []

    for tx in data.get("txs", []):
        for output in tx.get("out", []):
            receiver = output.get("addr")
            amount = output.get("value", 0) / 1e8

            if receiver:
                transactions.append({
                    "sender": address,
                    "receiver": receiver,
                    "amount": amount
                })

    return transactions
