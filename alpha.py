from flask import Flask, request, render_template_string
import requests, difflib, urllib.parse
from typing import Dict, Optional, Tuple

app = Flask(__name__)
FB = "https://alpha-98bb1-default-rtdb.firebaseio.com"
TIMEOUT = 6

# ---------- SAUDAÇÕES - NUNCA BUSCAR ----------
GREETINGS = {
    "ola", "olá", "oi", "oii", "oie", "e ai", "e aí", "hey", "hi", "hello",
    "bom dia", "boa tarde", "boa noite", "tudo bem", "como vai"
}

def is_greeting(text: str) -> bool:
    t = text.lower().strip().replace("!","").replace("?","").strip()
    # se for só 1-2 palavras e está na lista
    if t in GREETINGS: return True
    if len(t.split()) <= 2 and any(g in t for g in GREETINGS): return True
    return False

def get_memory() -> Dict[str, str]:
    try:
        d = requests.get(f"{FB}/memoria.json", timeout=TIMEOUT).json() or {}
        return {v["original"].lower(): v["resposta"] for v in d.values() if isinstance(v, dict) and v.get("original")}
    except: return {}

def save_memory(q: str, a: str, src=""):
    try:
        safe = "".join(c if c.isalnum() else "_" for c in q.lower())[:60]
        requests.put(f"{FB}/memoria/{safe}.json", json={"original":q,"resposta":a,"fonte":src}, timeout=TIMEOUT)
    except: pass

def search_wikipedia(query: str) -> Optional[Tuple[str,str]]:
    # só busca se pergunta tiver mais de 2 palavras OU contiver "o que é / quem é"
    low = query.lower()
    if is_greeting(low): return None
    # extrai termo útil
    if "o que" not in low and "quem" not in low and "defina" not in low and "explique" not in low and len(low.split()) < 3:
        return None
    try:
        term = low
        for p in ["o que é","o que e","quem é","quem e","defina","explique","oque e"]:
            term = term.replace(p,"")
        term = term.strip()[:80]
        if len(term) < 3: return None
        url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(term)}"
        j = requests.get(url, timeout=TIMEOUT, headers={"User-Agent":"AlphAI"}).json()
        if j.get("extract") and "may refer to" not in j.get("extract",""):
            return j["extract"][:600], j.get("content_urls",{}).get("desktop",{}).get("page","")
    except: pass
    return None

def search_ddg(query: str) -> Optional[Tuple[str,str]]:
    if is_greeting(query): return None
    if len(query.split()) < 3 and "o que" not in query.lower(): return None
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        j = requests.get(url, timeout=TIMEOUT).json()
        if j.get("AbstractText"): return j["AbstractText"][:600], j.get("AbstractURL","")
    except: pass
    return None

def answer(q: str) -> str:
    raw = q.strip()
    if not raw: return "Digite sua mensagem."
    low = raw.lower().replace("?","").strip()

    if low.startswith("ensina:") and "|" in raw:
        _, c = raw.split("ensina:",1)
        qp, ap = c.split("|",1)
        save_memory(qp.strip(), ap.strip(), "manual")
        return "Aprendido."

    # 1. SAUDAÇÃO TEM PRIORIDADE TOTAL
    if is_greeting(raw):
        return "Olá! Como posso ajudar?"

    mem = get_memory()
    if low in mem: return mem[low]
    
    close = difflib.get_close_matches(low, mem.keys(), n=1, cutoff=0.85)
    if close: return mem[close[0]]

    # 2. Só depois busca fontes
    for fn in (search_wikipedia, search_ddg):
        res = fn(raw)
        if res:
            txt, src = res
            save_memory(raw, txt, src)
            return f"{txt}\n\nFonte: {src}" if src else txt

    return "Não encontrei. Você pode me ensinar: ensina: pergunta | resposta"

HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AlphAI</title>
<style>body{margin:0;font-family:sans-serif;background:#fff;display:flex;flex-direction:column;height:100vh}header{padding:20px;text-align:center;font-weight:700;border-bottom:1px solid #eee}#chat{flex:1;overflow-y:auto;padding:20px;max-width:720px;margin:0 auto;width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:12px;padding-bottom:90px}.b{padding:14px 18px;border-radius:18px;max-width:85%;line-height:1.5;white-space:pre-wrap}.user{background:#111;color:#fff;align-self:flex-end}.bot{background:#f2f2f2;align-self:flex-start}#bar{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #eee;padding:12px;display:flex;max-width:720px;margin:0 auto}input{flex:1;padding:14px 18px;border-radius:24px;border:1px solid #ddd}button{margin-left:8px;padding:14px 22px;border-radius:24px;border:none;background:#111;color:#fff}</style></head><body>
<header>AlphAI</header><div id="chat"><div id="msgs"></div></div><div id="bar"><input id="q" placeholder="Digite sua mensagem"><button onclick="send()">Enviar</button></div>
<script>const m=document.getElementById('msgs');function add(t,c){let d=document.createElement('div');d.className='b '+c;d.textContent=t;m.appendChild(d);scrollTo(0,document.body.scrollHeight)}async function send(){let v=document.getElementById('q').value.trim();if(!v)return;add(v,'user');document.getElementById('q').value='';let r=await fetch('/ask?q='+encodeURIComponent(v));let t=await r.text();add(t,'bot')}document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')send()});add('Olá. Como posso ajudar?','bot');</script></body></html>"""

@app.route("/")
def home(): return render_template_string(HTML)
@app.route("/ask")
def ask(): return answer(request.args.get("q",""))
