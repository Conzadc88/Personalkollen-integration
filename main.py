import os
import requests
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

# Recupera il token dalle variabili d'ambiente di Render per sicurezza
API_TOKEN = os.environ.get("PERSONALKOLLEN_TOKEN")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Bridge Personalkollen attivo!"})

@app.route("/turni-oggi", methods=["GET"])
def turni_oggi():
    if not API_TOKEN:
        return jsonify({"error": "Token non configurato"}), 500

    url = "https://personalkollen.se/api/work-periods/"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Accept": "application/json"
    }
    
    oggi = datetime.now().strftime("%Y-%m-%d")
    params = {"date": oggi}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            dati = response.json()
            return jsonify({"success": True, "date": oggi, "data": dati})
        else:
            return jsonify({"error": f"Errore API {response.status_code}", "details": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
