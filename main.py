import os
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)

API_TOKEN = os.environ.get("PERSONALKOLLEN_TOKEN")
NOME_PERSONALE = "Nicolas"  # Filtra i turni per il tuo nome

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

def crea_frase_turni(dati_json, giorno_label, data_target, solo_miei=False):
    if not dati_json or "results" not in dati_json or not dati_json["results"]:
        return f"{giorno_label} non ci sono turni registrati." if not solo_miei else f"{giorno_label} non hai turni previsti."
    
    turni_set = set()
    turni_list = []

    for period in dati_json.get("results", []):
        period_date = period.get("date", "")
        if period_date and period_date != data_target:
            continue

        nome = period.get("staff_name", "Un dipendente")
        
        # Se è una richiesta personale, scarta tutti gli altri dipendenti
        if solo_miei and NOME_PERSONALE.lower() not in nome.lower():
            continue

        inizio = period.get("start_time", "")[:5]
        fine = period.get("end_time", "")[:5]
        
        if solo_miei:
            item = f"dalle {inizio} alle {fine}" if inizio and fine else "in turno"
        else:
            item = f"{nome} ({inizio}-{fine})" if inizio and fine else nome
            
        if item not in turni_set:
            turni_set.add(item)
            turni_list.append(item)
    
    if not turni_list:
        return f"{giorno_label} non hai turni previsti." if solo_miei else f"{giorno_label} non ci sono turni registrati."
    
    if solo_miei:
        return f"{giorno_label} lavori " + " e ".join(turni_list) + "."
    return f"{giorno_label}: " + ", ".join(turni_list) + "."

def genera_testo_giorno(delta_giorni, giorno_label, solo_miei=False):
    data_target = (datetime.now() + timedelta(days=delta_giorni)).strftime("%Y-%m-%d")
    dati = ottieni_turni_per_data(data_target)
    return crea_frase_turni(dati, giorno_label, data_target, solo_miei=solo_miei)

def genera_testo_settimana(solo_miei=False):
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
                
                if solo_miei and NOME_PERSONALE.lower() not in nome.lower():
                    continue

                inizio = period.get("start_time", "")[:5]
                item = f"dalle {inizio}" if solo_miei else (f"{nome} alle {inizio}" if nome else "")
                
                if item and item not in turni_set:
                    turni_set.add(item)
                    turni_giorno.append(item)
                    
            if turni_giorno:
                frasi_giorni.append(f"{nome_giorno} " + ", ".join(turni_giorno))
        
    if not frasi_giorni:
        return "Non hai turni previsti per i prossimi sette giorni." if solo_miei else "Non ci sono turni registrati per i prossimi sette giorni."
    
    prefisso = "Ecco i tuoi turni della settimana. " if solo_miei else "Ecco i turni della squadra per la settimana. "
    return prefisso + ". ".join(frasi_giorni) + "."

@app.route("/turni-oggi", methods=["GET", "POST"])
@app.route("/turni-domani", methods=["GET", "POST"])
@app.route("/turni-settimana", methods=["GET", "POST"])
def gestisci_alexa():
    if request.method == "POST":
        req_data = request.get_json(silent=True) or {}
        intent_name = req_data.get("request", {}).get("intent", {}).get("name", "").lower()
        
        # Riconoscimento se la richiesta è personale ("miei", "ho", "lavoro")
        solo_miei = any(k in intent_name for k in ["mio", "miei", "ho", "personale"])

        if "domani" in intent_name or "domani" in request.path:
            return alexa_response(genera_testo_giorno(1, "Domani", solo_miei=solo_miei))
        elif "settimana" in intent_name or "settimana" in request.path:
            return alexa_response(genera_testo_settimana(solo_miei=solo_miei))
        else:
            return alexa_response(genera_testo_giorno(0, "Oggi", solo_miei=solo_miei))

    # Test via browser (GET)
    return jsonify({"success": True, "speech": genera_testo_giorno(0, "Oggi")})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
