import os
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify

app = Flask(__name__)

API_TOKEN = os.environ.get("PERSONALKOLLEN_TOKEN")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Bridge Personalkollen attivo!"})

def ottieni_turni_per_data(data_target):
    if not API_TOKEN:
        return None

    url = "https://personalkollen.se/api/work-periods/"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Accept": "application/json"
    }
    params = {"date": data_target}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

# Endpoint Turni Oggi
@app.route("/turni-oggi", methods=["GET", "POST"])
def turni_oggi():
    oggi = datetime.now().strftime("%Y-%m-%d")
    dati = ottieni_turni_per_data(oggi)
    return jsonify({"success": True, "date": oggi, "data": dati})

# Endpoint Turni Domani
@app.route("/turni-domani", methods=["GET", "POST"])
def turni_domani():
    domani = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    dati = ottieni_turni_per_data(domani)
    return jsonify({"success": True, "date": domani, "data": dati})

# Endpoint Turni Intera Settimana (Prossimi 7 giorni)
@app.route("/turni-settimana", methods=["GET", "POST"])
def turni_settimana():
    oggi = datetime.now()
    risultati_settimana = []

    for i in range(7):
        giorno = (oggi + timedelta(days=i)).strftime("%Y-%m-%d")
        dati_giorno = ottieni_turni_per_data(giorno)
        risultati_settimana.append({
            "date": giorno,
            "data": dati_giorno
        })

    return jsonify({"success": True, "weekly_schedule": risultati_settimana})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
