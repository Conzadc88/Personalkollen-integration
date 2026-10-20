import os
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

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
    # Passiamo sia date che start_date/end_date per filtrare correttamente l'API
    params = {
        "date": data_target,
        "start_date": data_target,
        "end_date": data_target
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def alexa_response(testo):
    """Formatta la risposta per Alexa nei limiti previsti."""
    if len(testo) > 7000:
        testo = testo[:6900] + "... Consulta l'app Personalkollen per i dettagli completi."
    
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": testo
            },
            "shouldEndSession": True
        }
    })

def crea_frase_turni(dati_json, giorno_label, data_target):
    if not dati_json or "results" not in dati_json or not dati_json["results"]:
        return f"{giorno_label} non ci sono turni registrati."
    
    turni_set = set()
    turni_list = []

    for period in dati_json.get("results", []):
        # Filtro di sicurezza: scarta i turni che non appartengono alla data richiesta
        period_date = period.get("date", "")
        if period_date and period_date != data_target:
            continue

        nome = period.get("staff_name", "Un dipendente")
        inizio = period.get("start_time", "")[:5]
        fine = period.get("end_time", "")[:5]
        
        item = f"{nome} ({inizio}-{fine})" if inizio and fine else nome
            
        if item not in turni_set:
            turni_set.add(item)
            turni_list.append(item)
    
    if not turni_list:
        return f"{giorno_label} non ci sono turni registrati."
    
    return f"{giorno_label}: " + ", ".join(turni_list) + "."

@app.route("/turni-oggi", methods=["GET", "POST"])
def turni_oggi():
    oggi = datetime.now().strftime("%Y-%m-%d")
    dati = ottieni_turni_per_data(oggi)
    frase = crea_frase_turni(dati, "Oggi", oggi)
    
    if request.method == "POST":
        return alexa_response(frase)
    return jsonify({"success": True, "speech": frase})

@app.route("/turni-domani", methods=["GET", "POST"])
def turni_domani():
    domani = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    dati = ottieni_turni_per_data(domani)
    frase = crea_frase_turni(dati, "Domani", domani)
    
    if request.method == "POST":
        return alexa_response(frase)
    return jsonify({"success": True, "speech": frase})

@app.route("/turni-settimana", methods=["GET", "POST"])
def turni_settimana():
    oggi = datetime.now()
    giorni_settimana = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    frasi_giorni = []

    for i in range(7):
        data_dt = oggi + timedelta(days=i)
        data_str = data_dt.strftime("%Y-%m-%d")
        nome_giorno = giorni_settimana[data_dt.weekday()]
        
        dati_giorno = ottieni_turni_per_data(data_str)
        if dati_giorno and "results" in dati_giorno:
            turni_giorno = []
            turni_set = set()
            for period in dati_giorno["results"]:
                if period.get("date") != data_str:
                    continue
                nome = period.get("staff_name", "")
                inizio = period.get("start_time", "")[:5]
                item = f"{nome} alle {inizio}" if (nome and inizio) else nome
                
                if item and item not in turni_set:
                    turni_set.add(item)
                    turni_giorno.append(item)
                    
            if turni_giorno:
                frasi_giorni.append(f"{nome_giorno}: " + ", ".join(turni_giorno))
        
    if not frasi_giorni:
        frase = "Non ci sono turni registrati per i prossimi sette giorni."
    else:
        frase = "Ecco i turni della settimana. " + ". ".join(frasi_giorni) + "."

    if request.method == "POST":
        return alexa_response(frase)
    return jsonify({"success": True, "speech": frase})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
