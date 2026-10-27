from flask import Flask, request, render_template_string
import requests
import difflib
import urllib.parse
from typing import Dict, Tuple, Optional

app = Flask(__name__)

FIREBASE_URL = "https://alpha-98bb1-default-rtdb.firebaseio.com"
TIMEOUT = 6

# ----------------- MEMÓRIA -----------------
def get_memory() -> Dict[str, str]:
    try:
        resp = requests.get(f"{FIREBASE_URL}/memoria.json", timeout=TIMEOUT).json()
        if not resp: return {}
        return {
            v["original"].lower(): v["resposta"]
            for v in resp.values()
            if isinstance(v, dict) and v.get("original") and v.get("resposta")
        }
    except Exception:
        return {}

def save_memory(question: str, answer: str, source: str = "") -> None:
    try:
        safe_key = "".join(c if c.isalnum() else "_" for c in question.lower())[:60]
        payload = {"original": question, "resposta": answer, "fonte": source}
        requests.put(f"{FIREBASE_URL}/memoria/{safe_key}.json", json=payload, timeout=TIMEOUT)
    except Exception:
        pass

# ----------------- FONTES OFICIAIS -----------------
def search_wikipedia(query: str) -> Optional[Tuple[str, str]]:
    try:
        term = query.lower()
        for prefix in ["o que é", "o que e", "quem é", "quem e", "defina", "explique"]:
            if term.startswith(prefix):
                term = term.replace(prefix, "", 1).strip()
        term = term[:80]
        url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(term)}"
        data = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "AlphAI/1.0"}).json()
        if data.get("extract"):
            source_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            return data["extract"][:600], source_url
    except Exception:
        pass
    return None

def search_duckduckgo(query: str) -> Optional[Tuple[str, str]]:
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        data = requests.get(url, timeout=TIMEOUT).json()
        if data.get("AbstractText"):
            return data["AbstractText"][:600], data.get("AbstractURL", "")
    except Exception:
        pass
    return None

def search_books(query: str) -> Optional[Tuple[str, str]]:
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query)}&maxResults=1"
        data = requests.get(url, timeout=TIMEOUT).json()
        if data.get("items"):
            info = data["items"][0].get("volumeInfo", {})
            desc = info.get("description")
            if desc:
                return desc[:600], info.get("infoLink", "")
    except Exception:
        pass
    return None

# ----------------- CORE -----------------
STATIC_KNOWLEDGE = {
    "quem é você": "Sou o AlphAI, criado pelo Eliast.",
}

def answer_question(question: str) -> str:
    q_raw = question.strip()
    if not q_raw:
        return "Digite sua pergunta."

    q_lower = q_raw.lower().replace("?", "").strip()

    # Comando de ensino
    if q_lower.startswith("ensina:") and "|" in q_raw:
        try:
            _, content = q_raw.split("ensina:", 1)
            q_part, a_part = content.split("|", 1)
            save_memory(q_part.strip(), a_part.strip(), "manual")
            return "Aprendido."
        except ValueError:
            return "Formato: ensina: pergunta | resposta"

    memory = get_memory()

    # 1. Memória exata
    if q_lower in memory:
        return memory[q_lower]

    # 2. Conhecimento estático
    if q_lower in STATIC_KNOWLEDGE:
        return STATIC_KNOWLEDGE[q_lower]

    # 3. Similaridade
    close = difflib.get_close_matches(q_lower, memory.keys(), n=1, cutoff=0.8)
    if close:
        return memory[close[0]]

    # 4. Fontes oficiais
    for search_func in (search_wikipedia, search_duckduckgo, search_books):
        result = search_func(q_raw)
        if result:
            text, source = result
            save_memory(q_raw, text, source)
            return f"{text}\n\nFonte: {source}" if source else text

    return "Não encontrei essa informação nas fontes oficiais. Você pode me ensinar usando: ensina: pergunta | resposta"

# ----------------- WEB -----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlphAI</title>
<style>
:root{--bg:#ffffff;--fg:#111;--muted:#f2f2f2;--border:#e5e5e5}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,Inter,Segoe UI,sans-serif;background:var(--bg);color:var(--fg);display:flex;flex-direction:column;height:100vh}
header{padding:20px;text-align:center;font-weight:700;letter-spacing:-0.3px;border-bottom:1px solid var(--border)}
#chat{flex:1;overflow-y:auto;padding:24px;max-width:720px;margin:0 auto;width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:14px;padding-bottom:100px}
.bubble{padding:14px 18px;border-radius:20px;max-width:84%;line-height:1.5;font-size:15px;white-space:pre-wrap}
.user{background:var(--fg);color:#fff;align-self:flex-end;border-bottom-right-radius:6px}
.bot{background:var(--muted);align-self:flex-start;border-bottom-left-radius:6px}
#inputBar{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid var(--border);padding:14px;display:flex;gap:10px;max-width:720px;margin:0 auto}
#q{flex:1;padding:14px 20px;border-radius:28px;border:1px solid var(--border);outline:none;font-size:15px}
#send{padding:14px 22px;border-radius:28px;border:none;background:var(--fg);color:#fff;cursor:pointer}
</style>
</head>
<body>
<header>AlphAI</header>
<div id="chat"><div id="msgs"></div></div>
<div id="inputBar"><input id="q" placeholder="Digite sua mensagem"><button id="send">Enviar</button></div>
<script>
const msgs=document.getElementById('msgs'), input=document.getElementById('q'), btn=document.getElementById('send');
function add(text, cls){const d=document.createElement('div');d.className='bubble '+cls;d.textContent=text;msgs.appendChild(d);window.scrollTo(0,document.body.scrollHeight)}
async function send(){const v=input.value.trim();if(!v)return;add(v,'user');input.value='';const r=await fetch('/ask?q='+encodeURIComponent(v));const t=await r.text();add(t,'bot')}
btn.onclick=send; input.addEventListener('keydown',e=>{if(e.key==='Enter')send()});
add('Olá. Como posso ajudar?','bot');
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/ask")
def ask():
    return answer_question(request.args.get("q", ""))
