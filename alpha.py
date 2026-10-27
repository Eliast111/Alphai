from flask import Flask, request
import requests
app = Flask(__name__)
URL = "https://alpha-98bb1-default-rtdb.firebaseio.com"

@app.route("/")
def home():
    return """
    <h1>Alpha V1</h1>
    <form action='/ask'>
    <input name='q' placeholder='Pergunte ou ensina: a|b'>
    <button>Enviar</button>
    </form>
    """

@app.route("/ask")
def ask():
    q = request.args.get("q","")
    if "|" in q and q.lower().startswith("ensina:"):
        p, r = q[7:].split("|",1)
        safe = p.strip().replace(".","_").replace("/","_")
        requests.put(f"{URL}/memoria/{safe}.json", json={"original":p.strip(), "resposta":r.strip()})
        return f"Aprendi: {p} = {r}"
    # busca
    try:
        dados = requests.get(f"{URL}/memoria.json").json() or {}
        for v in dados.values():
            if q.lower() in v.get("original","").lower():
                return v["resposta"]
    except: pass
    return f"Nao sei {q}. Me ensina: ensina: {q} | resposta"
