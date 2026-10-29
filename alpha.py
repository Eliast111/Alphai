import os
import re
import difflib
import logging
import urllib.parse
from typing import Optional

import requests
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
logging.basicConfig(level=logging.INFO)

FB = os.environ.get(
    "FIREBASE_DATABASE_URL",
    "https://alpha-98bb1-default-rtdb.firebaseio.com"
).rstrip("/")
TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "8"))
MAX_MEMORY_ITEMS = int(os.environ.get("MAX_MEMORY_ITEMS", "300"))
MAX_MESSAGE_CHARS = 2000
MAX_CONTEXT_MESSAGES = 12

# Optional OpenAI-compatible chat-completions API.
# Set these environment variables in Vercel to enable model-based conversation.
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
AI_MODEL = os.environ.get("AI_MODEL", "")
AI_ENABLED = bool(AI_API_KEY and AI_MODEL)

HTML = r"""
<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#080d18">
<title>AlphAI ULTRA</title>
<style>
:root{color-scheme:dark;--bg:#080d18;--panel:#101827;--panel2:#151f31;--line:#26334a;--text:#eef4ff;--muted:#9aabc5;--blue:#36bafa;--purple:#8b7cff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#142744 0,#080d18 52%);color:var(--text);font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;height:100dvh;display:flex;overflow:hidden}
button,input,textarea{font:inherit}button{cursor:pointer}
.sidebar{width:260px;border-right:1px solid var(--line);padding:18px;display:flex;flex-direction:column;gap:14px;background:#080d18cc}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:19px;letter-spacing:.2px}.logo{display:grid;place-items:center;width:38px;height:38px;border-radius:13px;background:linear-gradient(135deg,var(--blue),var(--purple));color:#06101c;font-weight:900}
.sub{color:var(--muted);font-size:12px}.new{background:linear-gradient(135deg,#1b9cda,#7164e8);color:white;border:0;border-radius:13px;padding:12px;font-weight:700}
.side-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1.4px;margin-top:10px}.history{display:flex;flex-direction:column;gap:6px;overflow:auto}.history button{border:1px solid transparent;text-align:left;color:#c7d3e8;background:transparent;border-radius:10px;padding:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.history button:hover{background:var(--panel);border-color:var(--line)}
.sidebar-foot{margin-top:auto;color:var(--muted);font-size:12px}
.main{min-width:0;flex:1;display:flex;flex-direction:column;position:relative}.topbar{height:64px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 22px;background:#080d18a8;backdrop-filter:blur(12px)}.top-title{font-weight:750}.status{font-size:12px;color:#8fe3bd;display:flex;align-items:center;gap:7px}.dot{width:7px;height:7px;border-radius:50%;background:#54dfa0;box-shadow:0 0 12px #54dfa0}
.chat{width:100%;max-width:900px;margin:0 auto;flex:1;overflow-y:auto;padding:28px 22px 24px;scroll-behavior:smooth}.welcome{min-height:55%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:30px 0}.welcome .orb{width:70px;height:70px;border-radius:24px;display:grid;place-items:center;background:linear-gradient(135deg,#1b9cda,#8b7cff);color:#06101c;font-size:30px;font-weight:900;box-shadow:0 0 55px #258bd533}.welcome h1{font-size:clamp(28px,5vw,42px);margin:18px 0 8px;letter-spacing:-1.5px}.gradient{background:linear-gradient(90deg,#59d1ff,#aaa1ff);background-clip:text;color:transparent}.welcome p{color:var(--muted);max-width:500px;margin:0}.suggestions{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:24px}.suggestions button{border:1px solid var(--line);background:#111b2b;color:#d9e5f7;padding:10px 13px;border-radius:14px}
.msg{display:flex;margin:18px 0;gap:11px;align-items:flex-start}.msg.user{flex-direction:row-reverse}.avatar{width:32px;height:32px;flex:0 0 32px;border-radius:11px;background:var(--panel2);display:grid;place-items:center;color:var(--blue);font-weight:800}.user .avatar{background:#263c60;color:#fff}.content{max-width:min(78%,700px);padding:13px 16px;border:1px solid var(--line);background:#111b2a;border-radius:5px 17px 17px 17px;white-space:pre-wrap;overflow-wrap:anywhere}.user .content{background:linear-gradient(135deg,#1d4770,#39356f);border-color:#3c5b86;border-radius:17px 5px 17px 17px}.content img{display:block;max-width:100%;height:auto;border-radius:12px;margin-top:12px}.source-list{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}.source-list a{font-size:12px;color:#8edcff;text-decoration:none;border:1px solid #2c536d;border-radius:8px;padding:4px 8px}.source-list a:hover{text-decoration:underline}.meta{font-size:11px;color:var(--muted);margin-top:7px}.typing{color:var(--muted);font-size:13px;padding:8px 0}
.composer-wrap{padding:12px 20px calc(14px + env(safe-area-inset-bottom));background:linear-gradient(transparent,#080d18 20%)}.composer{max-width:900px;margin:0 auto;border:1px solid #35445e;background:#101827;border-radius:20px;padding:8px;display:flex;gap:8px;align-items:flex-end;box-shadow:0 10px 40px #0004}.composer textarea{resize:none;max-height:150px;min-height:42px;flex:1;border:0;outline:0;background:transparent;color:var(--text);padding:10px 9px}.composer button{border:0;border-radius:13px;padding:11px 15px;background:linear-gradient(135deg,#28b7ef,#7669f5);color:#07111c;font-weight:800}.composer button:disabled{opacity:.45;cursor:default}.disclaimer{text-align:center;color:#71829b;font-size:11px;margin-top:8px}
.mobile-menu{display:none;background:transparent;border:1px solid var(--line);color:var(--text);border-radius:9px;padding:6px 10px}
@media(max-width:720px){.sidebar{position:fixed;z-index:5;inset:0 auto 0 0;width:min(290px,85vw);transform:translateX(-105%);transition:transform .2s;box-shadow:20px 0 60px #0008}.sidebar.open{transform:translateX(0)}.mobile-menu{display:block}.topbar{padding:0 13px}.chat{padding:18px 13px}.composer-wrap{padding-left:10px;padding-right:10px}.content{max-width:88%}.welcome{min-height:50%}.suggestions button{font-size:12px}}
</style>
</head>
<body>
<aside class="sidebar" id="sidebar">
  <div class="brand"><div class="logo">A</div><div>AlphAI <span class="sub">ULTRA</span></div></div>
  <button class="new" id="newChat">＋ Nova conversa</button>
  <div class="side-label">Conversas neste dispositivo</div>
  <div class="history" id="history"></div>
  <div class="sidebar-foot">A memória de conhecimentos fica no Firebase quando configurado. O histórico do chat fica neste navegador.</div>
</aside>
<main class="main">
  <header class="topbar">
    <div style="display:flex;align-items:center;gap:10px"><button class="mobile-menu" id="menuBtn" aria-label="Abrir menu">☰</button><div><div class="top-title">Centro de comando</div><div class="sub">Assistente com memória e pesquisa</div></div></div>
    <div class="status"><span class="dot"></span><span id="statusText">Pronta</span></div>
  </header>
  <section class="chat" id="chat">
    <div class="welcome" id="welcome">
      <div class="orb">A</div><h1>Olá, sou a <span class="gradient">AlphAI</span>.</h1>
      <p>Vamos explorar ideias, aprender coisas novas e criar imagens. O que gostarias de fazer hoje?</p>
      <div class="suggestions">
        <button data-prompt="Explica inteligência artificial de forma simples">Explica uma ideia</button>
        <button data-prompt="O que é programação Python?">Aprender programação</button>
        <button data-prompt="gera imagem de uma cidade futurista em Maputo">Criar uma imagem</button>
      </div>
    </div>
    <div id="messages"></div><div class="typing" id="typing" hidden>AlphAI está a pensar…</div>
  </section>
  <div class="composer-wrap"><form class="composer" id="form"><textarea id="prompt" rows="1" maxlength="2000" placeholder="Escreve a tua mensagem…" aria-label="Mensagem"></textarea><button id="send" type="submit">Enviar ↑</button></form><div class="disclaimer">Confirma informações importantes. As respostas podem conter erros.</div></div>
</main>
<script>
const $=id=>document.getElementById(id);
const STORAGE_KEY='alphai_ultra_conversations_v1';
let conversations=[], activeId=null, busy=false;
try{conversations=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');if(!Array.isArray(conversations))conversations=[];}catch{conversations=[];}
function id(){return Date.now().toString(36)+Math.random().toString(36).slice(2,8)}
function save(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(conversations.slice(0,50)));}catch{}}
function active(){return conversations.find(c=>c.id===activeId)}
function createChat(){const c={id:id(),title:'Nova conversa',messages:[],updated:Date.now()};conversations.unshift(c);activeId=c.id;save();render();$('sidebar').classList.remove('open');$('prompt').focus();}
function renderHistory(){
 const host=$('history');host.replaceChildren();
 conversations.slice().sort((a,b)=>b.updated-a.updated).forEach(c=>{
  const b=document.createElement('button');b.textContent=c.title||'Nova conversa';b.title=b.textContent;
  b.onclick=()=>{activeId=c.id;render();$('sidebar').classList.remove('open')};host.appendChild(b);
 });
}
function addMessageNode(m){
 const row=document.createElement('div');row.className='msg '+(m.role==='user'?'user':'assistant');
 const av=document.createElement('div');av.className='avatar';av.textContent=m.role==='user'?'Tu':'A';
 const body=document.createElement('div');body.className='content';body.textContent=m.text||'';
 if(m.image_url){const img=document.createElement('img');img.src=m.image_url;img.alt='Imagem gerada pela AlphAI';img.loading='lazy';img.referrerPolicy='no-referrer';img.onerror=()=>{img.remove();const e=document.createElement('div');e.className='meta';e.textContent='Não foi possível carregar a imagem. Tenta novamente.';body.append(e)};body.appendChild(img);}
 if(m.prompt){const p=document.createElement('div');p.className='meta';p.textContent='Prompt: '+m.prompt;body.appendChild(p);}
 if(m.sources&&m.sources.length){const list=document.createElement('div');list.className='source-list';m.sources.forEach(s=>{try{const u=new URL(s.url);if(!['http:','https:'].includes(u.protocol))return;const a=document.createElement('a');a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';a.textContent=s.title||u.hostname;list.appendChild(a)}catch{}});body.appendChild(list);}
 row.append(av,body);$('messages').appendChild(row);
}
function render(){
 const c=active();$('messages').replaceChildren();$('welcome').hidden=!!(c&&c.messages.length);
 if(c)c.messages.forEach(addMessageNode);
 renderHistory();$('chat').scrollTop=$('chat').scrollHeight;
}
function pushMessage(role,text,extra={}){
 const c=active();if(!c)return;
 const m={role,text,...extra};c.messages.push(m);c.updated=Date.now();
 if(role==='user'&&c.title==='Nova conversa')c.title=(text.slice(0,42)||'Nova conversa');
 save();render();
}
async function sendMessage(text){
 if(busy)return;text=(text??$('prompt').value).trim();if(!text)return;
 if(!activeId)createChat();
 $('prompt').value='';$('prompt').style.height='auto';pushMessage('user',text);
 busy=true;$('send').disabled=true;$('typing').hidden=false;$('statusText').textContent='A pensar…';
 try{
  const c=active();
  const context=c.messages.slice(-13,-1).map(m=>({role:m.role==='assistant'?'assistant':'user',content:m.text})).filter(m=>m.content);
  const res=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:text,history:context})});
  let data;try{data=await res.json()}catch{throw new Error('O servidor devolveu uma resposta inválida.')}
  if(!res.ok)throw new Error(data.error||'Não foi possível obter resposta.');
  pushMessage('assistant',data.text||'Não consegui gerar uma resposta.',{image_url:data.image_url||null,prompt:data.prompt||null,sources:Array.isArray(data.sources)?data.sources:[]});
 }catch(e){pushMessage('assistant','Ocorreu um erro: '+(e.message||'verifica a ligação e tenta novamente.'));}
 finally{busy=false;$('send').disabled=false;$('typing').hidden=true;$('statusText').textContent='Pronta';$('prompt').focus();}
}
$('form').addEventListener('submit',e=>{e.preventDefault();sendMessage()});
$('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}});
$('prompt').addEventListener('input',()=>{const el=$('prompt');el.style.height='auto';el.style.height=Math.min(el.scrollHeight,150)+'px'});
$('newChat').onclick=createChat;
$('menuBtn').onclick=()=>$('sidebar').classList.toggle('open');
document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>sendMessage(b.dataset.prompt));
if(!conversations.length)createChat();else{activeId=conversations[0].id;render();}
</script>
</body>
</html>
"""


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def is_greeting(text: str) -> bool:
    t = re.sub(r"[!.,?…]+$", "", normalize(text))
    greetings = {
        "ola", "olá", "oi", "oie", "hey", "hi", "hello",
        "bom dia", "boa tarde", "boa noite",
        "ola alphai", "olá alphai", "oi alphai"
    }
    return t in greetings


def is_thanks(text: str) -> bool:
    t = normalize(text)
    return any(x in t for x in ("obrigado", "obrigada", "muito obrigado", "valeu", "agradeço"))


def image_prompt(text: str) -> Optional[str]:
    triggers = (
        "gera imagem de", "gera uma imagem de", "gerar imagem de",
        "gerar uma imagem de", "crie imagem de", "cria imagem de",
        "cria uma imagem de", "crie uma imagem de", "desenha",
        "desenhe", "imagem de", "faz uma imagem de"
    )
    low = text.casefold()
    for trigger in triggers:
        pos = low.find(trigger)
        if pos >= 0:
            prompt = text[pos + len(trigger):].strip(" \t:,-.")
            if len(prompt) >= 2:
                return prompt[:500]
    return None


def firebase_get_memory():
    try:
        response = requests.get(
            f"{FB}/memoria.json",
            params={"orderBy": '"$key"', "limitToLast": str(MAX_MEMORY_ITEMS)},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        data = response.json() or {}
        if not isinstance(data, dict):
            return []
        items = []
        for key, value in data.items():
            if isinstance(value, dict) and value.get("original") and value.get("resposta"):
                items.append({
                    "id": key,
                    "original": str(value["original"])[:500],
                    "resposta": str(value["resposta"])[:5000]
                })
        return items
    except (requests.RequestException, ValueError):
        app.logger.warning("Firebase memory read failed", exc_info=True)
        return []


def firebase_save_memory(question: str, answer: str) -> bool:
    if not question.strip() or not answer.strip():
        return False
    try:
        response = requests.post(
            f"{FB}/memoria.json",
            json={"original": question.strip()[:500], "resposta": answer.strip()[:5000]},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        app.logger.warning("Firebase memory write failed", exc_info=True)
        return False


def find_memory(query: str, items: list) -> Optional[str]:
    q = normalize(query)
    if not q:
        return None
    originals = [normalize(item["original"]) for item in items]
    for i, original in enumerate(originals):
        if q == original:
            return items[i]["resposta"]
    matches = difflib.get_close_matches(q, originals, n=1, cutoff=0.86)
    if matches:
        return items[originals.index(matches[0])]["resposta"]
    # Simple token overlap for questions phrased differently.
    q_tokens = {x for x in re.findall(r"\w+", q) if len(x) > 2}
    best_score, best_answer = 0.0, None
    for item, original in zip(items, originals):
        tokens = {x for x in re.findall(r"\w+", original) if len(x) > 2}
        if not q_tokens or not tokens:
            continue
        score = len(q_tokens & tokens) / len(q_tokens | tokens)
        if score > best_score:
            best_score, best_answer = score, item["resposta"]
    return best_answer if best_score >= 0.65 else None


def search_wikipedia(query: str):
    cleaned = re.sub(r"^(o que é|o que e|quem é|quem e|explica|me explica)\s+", "", query.strip(), flags=re.I)
    if len(cleaned) < 2:
        return None
    url = "https://pt.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(cleaned[:100])
    try:
        response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "AlphAI/1.0 (educational assistant)"})
        if response.status_code != 200:
            return None
        data = response.json()
        extract = data.get("extract")
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
        if extract:
            return {
                "text": extract[:1800],
                "sources": [{"title": "Wikipedia", "url": page_url or url}]
            }
    except (requests.RequestException, ValueError):
        app.logger.info("Wikipedia search unavailable")
    return None


def ask_model(question: str, history: list):
    if not AI_ENABLED:
        return None
    messages = [{
        "role": "system",
        "content": (
            "És a AlphAI, uma assistente útil que responde em português claro. "
            "Sê honesta sobre incertezas; não inventes fontes nem afirmes ter feito ações que não fizeste. "
            "Usa o contexto recente quando for relevante. Se a pergunta pedir informação atual que não conheces, "
            "explica a limitação e recomenda verificação."
        )
    }]
    for item in history[-MAX_CONTEXT_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})
    messages.append({"role": "user", "content": question[:MAX_MESSAGE_CHARS]})
    try:
        response = requests.post(
            f"{AI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": messages, "temperature": 0.6},
            timeout=25
        )
        response.raise_for_status()
        data = response.json()
        answer_text = data["choices"][0]["message"]["content"]
        if isinstance(answer_text, list):
            answer_text = " ".join(str(part.get("text", "")) for part in answer_text if isinstance(part, dict))
        if isinstance(answer_text, str) and answer_text.strip():
            return {"text": answer_text.strip()[:8000], "sources": []}
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        app.logger.warning("AI provider request failed", exc_info=True)
    return None


def make_image_url(prompt: str) -> str:
    encoded = urllib.parse.quote(prompt, safe="")
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        "?width=1024&height=1024&nologo=true&enhance=true"
    )


def answer_message(payload: dict):
    raw = payload.get("q", "")
    if not isinstance(raw, str):
        return {"text": "A mensagem tem de ser texto.", "sources": []}, 400
    raw = raw.strip()
    if not raw:
        return {"text": "Escreve uma mensagem para começarmos.", "sources": []}, 400
    if len(raw) > MAX_MESSAGE_CHARS:
        return {"text": f"A mensagem é demasiado longa. Usa até {MAX_MESSAGE_CHARS} caracteres.",
