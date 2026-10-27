from flask import Flask, request, render_template_string
import requests, difflib, urllib.parse, re
from typing import Dict, Optional

app = Flask(__name__)
FB = "https://alpha-98bb1-default-rtdb.firebaseio.com"
TIMEOUT = 6

# ---------- MEMÓRIA ----------
def get_memory() -> Dict[str, str]:
    try:
        d = requests.get(f"{FB}/memoria.json", timeout=TIMEOUT).json() or {}
        return {v["original"].lower(): v["resposta"] for v in d.values() if isinstance(v, dict) and v.get("original")}
    except: return {}

def save_memory(q: str, a: str):
    try:
        safe = "".join(c if c.isalnum() else "_" for c in q.lower())[:60]
        requests.put(f"{FB}/memoria/{safe}.json", json={"original": q, "resposta": a}, timeout=TIMEOUT)
    except: pass

# ---------- CONVERSA NATURAL ----------
def naturalize(wiki_text: str, question: str) -> str:
    """Transforma texto enciclopédico em conversa natural"""
    # remove frases muito técnicas no começo
    txt = wiki_text.split(".")[0] + "."
    if len(txt) < 20:
        txt = wiki_text[:300]
    return txt

def detect_intent(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["ola", "olá", "oi", "e ai", "e aí", "hey"]):
        return "greeting"
    if any(x in t for x in ["tudo bem", "como vai", "como você está", "como voce esta"]):
        return "how_are_you"
    if any(x in t for x in ["obrigado", "valeu", "thanks", "agradeço"]):
        return "thanks"
    if any(x in t for x in ["quem é você", "quem e voce", "quem é vc"]):
        return "who_are_you"
    if "o que" in t or "quem" in t or "por que" in t or "como" in t or "?" in t:
        return "question"
    return "chat"

def search_wikipedia(q: str) -> Optional[str]:
    try:
        term = q.lower()
        for p in ["o que é", "o que e", "quem é", "quem e", "me explica", "o que significa"]:
            term = term.replace(p, "")
        term = term.strip()[:70]
        if len(term) < 2: return None
        url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(term)}"
        j = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "AlphAI"}).json()
        if j.get("extract"):
            return j["extract"]
    except: pass
    return None

def answer(text: str) -> str:
    raw = text.strip()
    if not raw:
        return "Oi?"

    low = raw.lower()

    if low.startswith("ensina:") and "|" in raw:
        try:
            _, c = raw.split("ensina:", 1)
            qp, ap = c.split("|", 1)
            save_memory(qp.strip(), ap.strip())
            return f"Beleza, aprendi. Agora já sei sobre '{qp.strip()}'."
        except:
            return "Usa assim: ensina: pergunta | resposta"

    intent = detect_intent(raw)

    if intent == "greeting":
        return "Olá! Tudo bem? No que posso te ajudar hoje?"
    
    if intent == "how_are_you":
        return "Tô bem, pronto pra ajudar! E você, como tá?"

    if intent == "thanks":
        return "De nada! Se precisar de mais alguma coisa é só falar."

    if intent == "who_are_you":
        return "Eu sou o AlphAI, criado pelo Eliast. Sou uma IA que conversa de forma natural e ainda aprende com você. O que quer conversar?"

    mem = get_memory()
    if low in mem:
        return mem[low]
    
    close = difflib.get_close_matches(low, mem.keys(), n=1, cutoff=0.85)
    if close:
        return mem[close[0]]

    # Se for pergunta real, busca e responde naturalmente
    if intent == "question":
        wiki = search_wikipedia(raw)
        if wiki:
            natural = naturalize(wiki, raw)
            # não salva o texto cru, salva natural
            save_memory(raw, natural)
            return natural + "\n\nQuer que eu explique de forma mais simples?"
        return "Boa pergunta. Ainda não sei sobre isso, mas se você me ensinar eu aprendo na hora. Usa: ensina: pergunta | resposta"

    # Conversa geral
    # Se não é pergunta nem saudação, continua o papo
    respostas_chat = [
        "Entendi. Me conta mais sobre isso?",
        "Interessante! Como você vê isso?",
        "Faz sentido. Quer que eu te ajude a desenvolver essa ideia?",
        "Hmm, conta mais, tô te ouvindo.",
    ]
    import random
    return random.choice(respostas_chat)

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlphAI</title>
<style>
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#111;display:flex;flex-direction:column;height:100vh}
header{padding:18px;text-align:center;font-weight:700;border-bottom:1px solid #eee;font-size:17px}
#chat{flex:1;overflow-y:auto;padding:20px;max-width:720px;margin:0 auto;width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:12px;padding-bottom:95px}
.bubble{padding:14px 18px;border-radius:20px;max-width:82%;line-height:1.5;font-size:15px;white-space:pre-wrap;animation:fade .2s}
@keyframes fade{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.user{background:#111;color:#fff;align-self:flex-end;border-bottom-right-radius:6px}
.bot{background:#f2f2f2;align-self:flex-start;border-bottom-left-radius:6px}
#bar{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #eee;padding:12px 12px 16px;display:flex;max-width:720px;margin:0 auto;gap:8px}
input{flex:1;padding:14px 18px;border-radius:24px;border:1px solid #ddd;outline:none;font-size:15px}
button{padding:14px 22px;border-radius:24px;border:none;background:#111;color:#fff;font-weight:600}
.typing{font-size:13px;color:#888;padding-left:6px}
</style></head><body>
<header>AlphAI</header>
<div id="chat"><div id="msgs"></div><div id="typing" class="typing" style="display:none">AlphAI está digitando...</div></div>
<div id="bar"><input id="q" placeholder="Converse com o AlphAI..."><button id="send">Enviar</button></div>
<script>
const msgs=document.getElementById('msgs'), input=document.getElementById('q'), btn=document.getElementById('send'), typing=document.getElementById('typing');
function add(t,c){let d=document.createElement('div');d.className='bubble '+c;d.textContent=t;msgs.appendChild(d);window.scrollTo(0,document.body.scrollHeight)}
async function send(){
 let v=input.value.trim(); if(!v) return;
 add(v,'user'); input.value=''; typing.style.display='block';
 try{
  let r=await fetch('/ask?q='+encodeURIComponent(v));
  let t=await r.text();
  typing.style.display='none';
  add(t,'bot');
 } catch{typing.style.display='none'; add('Ops, tive um problema de conexão. Tenta de novo?','bot')}
}
btn.onclick=send;
input.addEventListener('keydown',e=>{if(e.key==='Enter')send()});
setTimeout(()=>add('Olá! Eu sou o AlphAI. Pode conversar comigo naturalmente, como se fosse no WhatsApp.','bot'),300);
</script>
</body></html>
"""

@app.route("/")
def home(): return render_template_string(HTML)
@app.route("/ask")
def ask(): return answer(request.args.get("q",""))
