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
def _env_float(name: str, default: float, minimum: float = 1.0) -> float:
    """Read a positive numeric environment setting without breaking startup."""
    try:
        return max(minimum, float(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 1000) -> int:
    """Read a bounded integer environment setting."""
    try:
        return min(maximum, max(minimum, int(os.environ.get(name, str(default)))))
    except (TypeError, ValueError):
        return default


TIMEOUT = _env_float("HTTP_TIMEOUT", 8)
MAX_MEMORY_ITEMS = _env_int("MAX_MEMORY_ITEMS", 300, 1, 1000)
MAX_MESSAGE_CHARS = 2000
MAX_CONTEXT_MESSAGES = 12

# Google Gemini API configuration (server-side only).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
if GEMINI_MODEL.startswith("models/"):
    GEMINI_MODEL = GEMINI_MODEL[len("models/"):]
if not GEMINI_MODEL:
    GEMINI_MODEL = "gemini-3.8-flash"

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + urllib.parse.quote(GEMINI_MODEL, safe="")
    + ":generateContent"
)
# Groq is the primary provider. Keep both keys on the server only.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# The assistant is available when at least one provider is configured.
AI_ENABLED = bool(GROQ_API_KEY or GEMINI_API_KEY)

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

.markdown-rendered {
  white-space: normal;
  line-height: 1.75;
  overflow-wrap: anywhere;
}
.markdown-rendered p { margin: 0 0 13px; }
.markdown-rendered p:last-child { margin-bottom: 0; }
.markdown-rendered h1,.markdown-rendered h2,
.markdown-rendered h3,.markdown-rendered h4 {
  line-height: 1.3;
  margin: 22px 0 12px;
  color: #eef4ff;
}
.markdown-rendered h1 { font-size: 1.55em; }
.markdown-rendered h2 { font-size: 1.35em; }
.markdown-rendered h3 { font-size: 1.15em; }
.markdown-rendered strong { color: #fff; font-weight: 800; }
.markdown-rendered a { color: #59d1ff; }
.markdown-rendered ul,.markdown-rendered ol {
  padding-left: 25px;
  margin: 10px 0 15px;
}
.markdown-rendered li { margin: 5px 0; }
.markdown-rendered blockquote {
  border-left: 3px solid #36bafa;
  padding: 8px 14px;
  margin: 14px 0;
  background: #17243a;
  border-radius: 0 10px 10px 0;
  color: #c6d8ed;
}
.markdown-rendered table {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  margin: 15px 0;
  font-size: 13px;
}
.markdown-rendered th,.markdown-rendered td {
  border: 1px solid #35445e;
  padding: 9px 12px;
  text-align: left;
}
.markdown-rendered th { background: #1b2a42; }
.markdown-rendered tr:nth-child(even) { background: #172235; }
.markdown-rendered pre {
  position: relative;
  overflow-x: auto;
  background: #080f1d;
  border: 1px solid #35445e;
  border-radius: 12px;
  padding: 42px 14px 14px;
  margin: 14px 0;
  max-width: 100%;
}
.markdown-rendered pre code {
  background: transparent;
  padding: 0;
  color: #c7e8ff;
  font-size: 13px;
  white-space: pre;
}
.markdown-rendered :not(pre) > code {
  background: #26354c;
  color: #8edcff;
  padding: 2px 6px;
  border-radius: 5px;
  font-size: .9em;
}
.copy-code {
  position: absolute;
  top: 7px;
  right: 8px;
  border: 1px solid #354d6b;
  background: #17243a;
  color: #8edcff;
  padding: 5px 10px;
  border-radius: 7px;
  font-size: 11px;
}
.copy-code:hover { background: #263d5c; }
.markdown-rendered hr {
  border: 0;
  border-top: 1px solid #35445e;
  margin: 20px 0;
}

</style>

<script src="https://cdn.jsdelivr.net/npm/marked@15.0.12/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.6/dist/purify.min.js"></script>
</head>
<body>
<aside class="sidebar" id="sidebar">
  <div class="brand"><div class="logo">A</div><div>AlphAI <span class="sub">ULTRA</span></div></div>
  <button class="new" id="newChat">＋ Nova conversa</button>
  <div class="side-label">Conversas neste dispositivo</div>
  <div class="history" id="history"></div>
  <div class="sidebar-foot">O teu espaço de trabalho inteligente. As conversas ficam guardadas neste dispositivo.</div>
</aside>
<main class="main">
  <header class="topbar">
    <div style="display:flex;align-items:center;gap:10px"><button class="mobile-menu" id="menuBtn" aria-label="Abrir menu">☰</button><div><div class="top-title">AlphAI Workspace</div><div class="sub">O teu assistente inteligente</div></div></div>
    <div class="status"><span class="dot"></span><span id="statusText">Pronta</span></div>
  </header>
  <section class="chat" id="chat">
    <div class="welcome" id="welcome">
      <div class="orb">A</div><h1>Olá, sou a <span class="gradient">AlphAI</span>.</h1>
      <p>Transforma ideias em soluções. Aprende, cria, pesquisa e desenvolve os teus projectos com a AlphAI.</p>
      <div class="suggestions">
        <button data-prompt="Explica inteligência artificial de forma simples">Explica uma ideia</button>
        <button data-prompt="O que é programação Python?">Aprender programação</button>
        <button data-prompt="gera imagem de uma cidade futurista em Maputo">Criar uma imagem</button>
      </div>
    </div>
    <div id="messages"></div><div class="typing" id="typing" hidden>AlphAI está a pensar…</div>
  </section>
  <div class="composer-wrap"><form class="composer" id="form"><textarea id="prompt" rows="1" maxlength="2000" placeholder="Escreve a tua mensagem…" aria-label="Mensagem"></textarea><button id="send" type="submit">Enviar ↑</button></form><div class="disclaimer">A AlphAI pode cometer erros. Verifica informações importantes.</div></div>
</main>
<script>
const $=id=>document.getElementById(id);

document.addEventListener('click',async e=>{
 const button=e.target.closest('.copy-code');
 if(!button)return;

 const pre=button.closest('pre');
 const code=pre&&pre.querySelector('code');
 if(!code)return;

 const value=code.innerText;

 try{
   if(navigator.clipboard&&window.isSecureContext){
     await navigator.clipboard.writeText(value);
   }else{
     const area=document.createElement('textarea');
     area.value=value;
     area.style.position='fixed';
     area.style.opacity='0';
     document.body.appendChild(area);
     area.select();
     const copied=document.execCommand('copy');
     area.remove();
     if(!copied)throw new Error('Cópia indisponível');
   }

   button.textContent='Copiado!';
 }catch(error){
   button.textContent='Falhou';
   console.error('Erro ao copiar:',error);
 }
});

const STORAGE_KEY='alphai_ultra_conversations_v1';
let conversations=[], activeId=null, busy=false;
try{
  const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');
  conversations=Array.isArray(saved)?saved.filter(c=>c&&typeof c==='object'&&typeof c.id==='string'&&Array.isArray(c.messages)).slice(0,50):[];
  conversations.forEach(c=>{
    c.title=typeof c.title==='string'?c.title:'Nova conversa';
    c.updated=Number.isFinite(c.updated)?c.updated:Date.now();
    c.messages=c.messages.filter(m=>m&&typeof m==='object'&&['user','assistant'].includes(m.role)).map(m=>({...m,text:typeof m.text==='string'?m.text:''}));
  });
}catch{conversations=[];}
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
 const row=document.createElement('div');
 row.className='msg '+(m.role==='user'?'user':'assistant');

 const av=document.createElement('div');
 av.className='avatar';
 av.textContent=m.role==='user'?'Tu':'A';

 const body=document.createElement('div');
 body.className='content';

 if(m.role==='assistant' && window.marked && window.DOMPurify){
   try{
     const parsed=window.marked.parse(String(m.text||''),{
       gfm:true,
       breaks:true
     });

     body.classList.add('markdown-rendered');
     body.innerHTML=window.DOMPurify.sanitize(parsed,{
       USE_PROFILES:{html:true}
     });

     body.querySelectorAll('pre code').forEach(code=>{
       const pre=code.parentElement;
       const copy=document.createElement('button');
       copy.type='button';
       copy.className='copy-code';
       copy.textContent='Copiar';
       pre.appendChild(copy);
     });
   }catch(error){
     console.error('Erro ao formatar Markdown:',error);
     body.textContent=m.text||'';
   }
 }else{
   body.textContent=m.text||'';
 }

 if(m.image_url){
   const img=document.createElement('img');
   img.src=m.image_url;
   img.alt='Imagem gerada pela AlphAI';
   img.loading='lazy';
   img.referrerPolicy='no-referrer';
   img.onerror=()=>{
     img.remove();
     const e=document.createElement('div');
     e.className='meta';
     e.textContent='Não foi possível carregar a imagem. Tenta novamente.';
     body.append(e);
   };
   body.appendChild(img);
 }

 if(m.prompt){
   const p=document.createElement('div');
   p.className='meta';
   p.textContent='Prompt: '+m.prompt;
   body.appendChild(p);
 }

 if(m.sources&&m.sources.length){
   const list=document.createElement('div');
   list.className='source-list';

   m.sources.forEach(s=>{
     try{
       const u=new URL(s.url);
       if(!['http:','https:'].includes(u.protocol))return;
       const a=document.createElement('a');
       a.href=u.href;
       a.target='_blank';
       a.rel='noopener noreferrer';
       a.textContent=s.title||u.hostname;
       list.appendChild(a);
     }catch{}
   });

   body.appendChild(list);
 }

 row.append(av,body);
 $('messages').appendChild(row);
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


def ask_groq(question: str, history: list):
    """Try Groq first. Returns None on provider/network errors so Gemini can take over."""
    if not GROQ_API_KEY or not question.strip():
        return None
    if not isinstance(history, list):
        history = []

    system_message = (
        "És a AlphAI ULTRA, uma assistente digital avançada. Responde em português claro, natural e profissional. "
        "Sê honesta sobre incertezas; não inventes fontes nem afirmes ter feito ações que não fizeste. "
        "Usa o contexto recente quando for relevante. Se não souberes algo, explica a limitação."
    )
    messages = [{"role": "system", "content": system_message}]
    for item in history[-MAX_CONTEXT_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content", "")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()[:MAX_MESSAGE_CHARS]
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question.strip()[:MAX_MESSAGE_CHARS]})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.6,
        "max_completion_tokens": 1200
    }
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=(10, 45)
        )
        if response.status_code >= 400:
            app.logger.warning("Groq API returned HTTP %s: %s", response.status_code, response.text[:1000])
            return None
        data = response.json()
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            app.logger.warning("Groq returned no usable choice")
            return None
        message = choices[0].get("message") or {}
        answer_text = message.get("content", "")
        if isinstance(answer_text, str) and answer_text.strip():
            return {"text": answer_text.strip()[:8000], "sources": [], "provider": "Groq"}
        app.logger.warning("Groq response contained no text")
        return None
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        app.logger.warning("Groq request failed; trying the next provider", exc_info=True)
        return None


def ask_multi_model(question: str, history: list):
    """Automatic routing: Groq primary, Gemini fallback."""
    result = ask_groq(question, history)
    if result:
        return result
    result = ask_model(question, history)
    if result:
        result["provider"] = "Gemini"
        return result
    return None


def ask_model(question: str, history: list):
    """Generate an answer with Gemini, retrying temporary service errors."""
    import time

    if not AI_ENABLED or not GEMINI_API_KEY:
        return None
    if not isinstance(question, str) or not question.strip():
        return None
    if not isinstance(history, list):
        history = []

    system_instruction = (
        "És a AlphAI ULTRA, uma assistente digital avançada. Responde em português claro, natural e profissional. "
        "Sê honesta sobre incertezas; não inventes fontes nem afirmes ter feito ações que não fizeste. "
        "Usa o contexto recente quando for relevante. Se a pergunta pedir informação atual que não conheces, "
        "explica a limitação e recomenda verificação."
    )

    # Keep the conversation valid for Gemini: turns must alternate user/model.
    contents = []
    for item in history[-MAX_CONTEXT_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content", "")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()[:MAX_MESSAGE_CHARS]
        if not content:
            continue
        api_role = "model" if role == "assistant" else "user"
        if not contents and api_role == "model":
            continue
        if contents and contents[-1]["role"] == api_role:
            contents[-1]["parts"][0]["text"] += "\n" + content
        else:
            contents.append({"role": api_role, "parts": [{"text": content}]})

    current_question = question.strip()[:MAX_MESSAGE_CHARS]
    if contents and contents[-1]["role"] == "user":
        contents[-1]["parts"][0]["text"] += "\n" + current_question
    else:
        contents.append({"role": "user", "parts": [{"text": current_question}]})

    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024}
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    # Retry only temporary errors; do not retry invalid keys or bad requests.
    temporary_statuses = {429, 500, 502, 503, 504}
    retry_delays = (2, 5)

    for attempt in range(3):
        try:
            response = requests.post(
                GEMINI_API_URL,
                headers=headers,
                json=payload,
                timeout=(15, 90)
            )

            if response.status_code in temporary_statuses:
                app.logger.warning(
                    "Gemini temporarily unavailable (HTTP %s), attempt %s/3",
                    response.status_code,
                    attempt + 1
                )
                if attempt < 2:
                    time.sleep(retry_delays[attempt])
                    continue
                return None

            if response.status_code >= 400:
                app.logger.error(
                    "Gemini API error HTTP %s: %s",
                    response.status_code,
                    response.text[:1500]
                )
                return None

            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates or not isinstance(candidates[0], dict):
                app.logger.warning("Gemini returned no usable candidate: %s", str(data)[:1000])
                return None

            candidate = candidates[0]
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            answer_text = "\n".join(
                part.get("text", "")
                for part in parts
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            ).strip()

            if answer_text:
                return {"text": answer_text[:8000], "sources": []}

            app.logger.warning(
                "Gemini candidate contained no text (finishReason=%s)",
                candidate.get("finishReason", "unknown")
            )
            return None

        except requests.Timeout:
            app.logger.warning("Gemini timed out (attempt %s/3)", attempt + 1)
            if attempt < 2:
                time.sleep(retry_delays[attempt])
                continue
            return None
        except requests.RequestException:
            app.logger.warning("Gemini network request failed", exc_info=True)
            return None
        except (ValueError, TypeError, KeyError, AttributeError):
            app.logger.warning("Gemini response could not be parsed", exc_info=True)
            return None

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
        return {"text": f"A mensagem é demasiado longa. Usa até {MAX_MESSAGE_CHARS} caracteres.", "sources": []}, 400

    prompt = image_prompt(raw)
    if prompt:
        return {
            "text": f"Vou preparar uma imagem de: {prompt}",
            "image_url": make_image_url(prompt),
            "prompt": prompt,
            "sources": [{"title": "Pollinations AI", "url": "https://pollinations.ai/"}]
        }, 200

    low = normalize(raw)
    if low.startswith("ensina:"):
        token = os.environ.get("ALPHAI_ADMIN_TOKEN", "")
        provided = request.headers.get("X-Admin-Token", "")
        if not token:
            return {"text": "O ensino está desativado: configura ALPHAI_ADMIN_TOKEN nas variáveis de ambiente da Vercel.", "sources": []}, 403
        if not provided or not requests_compare(provided, token):
            return {"text": "Não tens autorização para ensinar a memória partilhada.", "sources": []}, 403
        if "|" not in raw:
            return {"text": "Formato: ensina: pergunta | resposta", "sources": []}, 400
        question, taught = raw.split(":", 1)[1].split("|", 1)
        question, taught = question.strip(), taught.strip()
        if not question or not taught:
            return {"text": "A pergunta e a resposta não podem estar vazias.", "sources": []}, 400
        ok = firebase_save_memory(question, taught)
        return ({"text": f"Aprendi: {question}" if ok else "Não consegui guardar isso no Firebase. Verifica as permissões e tenta novamente.", "sources": []}, 200 if ok else 502)

    if is_greeting(raw):
        return {"text": "Olá! Sou a AlphAI. Posso ajudar-te a aprender, pesquisar ideias ou criar uma imagem. O que gostarias de fazer?", "sources": []}, 200
    if is_thanks(raw):
        return {"text": "De nada! Se quiseres, podemos continuar a explorar o assunto.", "sources": []}, 200

    history = payload.get("history", [])
    if not isinstance(history, list):
        history = []
    memory = firebase_get_memory()
    remembered = find_memory(raw, memory)
    if remembered:
        return {"text": remembered, "sources": [{"title": "Memória AlphAI", "url": "https://alphai-one.vercel.app/"}]}, 200

    model_result = ask_multi_model(raw, history)
    if model_result:
        return model_result, 200

    wiki = search_wikipedia(raw)
    if wiki:
        # Save researched answers as knowledge, if Firebase permits writes.
        firebase_save_memory(raw, wiki["text"])
        return {"text": wiki["text"], "sources": wiki["sources"]}, 200

    if not AI_ENABLED:
        return {
            "text": (
                "Ainda não tenho informação suficiente para responder com confiança neste momento. "
                "Tenta reformular a pergunta ou consulta uma fonte adicional."
            ),
            "sources": []
        }, 200
    return {"text": "Não consegui obter uma resposta agora. Tenta reformular a pergunta ou tenta novamente mais tarde.", "sources": []}, 200


def requests_compare(a: str, b: str) -> bool:
    # Constant-time comparison avoids leaking token-match timing.
    import hmac
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "ai_enabled": AI_ENABLED,
        "groq_enabled": bool(GROQ_API_KEY),
        "gemini_enabled": bool(GEMINI_API_KEY),
        "primary_provider": "Groq" if GROQ_API_KEY else ("Gemini" if GEMINI_API_KEY else None),
        "firebase_configured": bool(FB)
    })


@app.route("/ask", methods=["POST"])
def ask():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Envia JSON com o campo q."}), 400
    data, status = answer_message(payload)
    return jsonify(data), status


@app.route("/image", methods=["GET"])
def image_route():
    prompt = request.args.get("q", "").strip()
    if not prompt or len(prompt) > 500:
        return jsonify({"error": "Indica um prompt com até 500 caracteres."}), 400
    from flask import redirect
    return redirect(make_image_url(prompt), code=302)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
