from flask import Flask, request, render_template_string, redirect
import requests, difflib, urllib.parse
from typing import Dict, Optional

app = Flask(__name__)
FB = "https://alpha-98bb1-default-rtdb.firebaseio.com"
TIMEOUT = 8

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

# ---------- DETECÇÃO ----------
def is_image_request(text: str) -> Optional[str]:
    t = text.lower()
    triggers = ["gera imagem", "crie imagem", "criar imagem", "gerar imagem", "desenha", "imagem de", "imagine", "cria uma imagem"]
    for trig in triggers:
        if trig in t:
            # extrai o prompt depois do trigger
            prompt = t.split(trig, 1)[-1].strip(" :de")
            if len(prompt) < 2:
                prompt = text  # usa tudo se não extraiu
            return prompt
    return None

def is_greeting(text: str) -> bool:
    t = text.lower().strip()
    return t in {"ola","olá","oi","oie","hey","hi"} or (len(t.split())<=2 and any(x in t for x in ["bom dia","boa tarde","boa noite"]))

def search_wikipedia(q: str) -> Optional[str]:
    try:
        term = q.lower()
        for p in ["o que é","o que e","quem é","quem e","me explica"]:
            term = term.replace(p,"")
        term = term.strip()[:70]
        if len(term) < 2: return None
        url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(term)}"
        j = requests.get(url, timeout=TIMEOUT, headers={"User-Agent":"AlphAI"}).json()
        if j.get("extract"): return j["extract"]
    except: pass
    return None

# ---------- RESPOSTA ----------
def answer(text: str) -> str:
    raw = text.strip()
    if not raw: return "Oi?"
    low = raw.lower()

    # Verifica se é pedido de imagem
    img_prompt = is_image_request(raw)
    if img_prompt:
        # retorna um marcador especial pro frontend entender que é imagem
        encoded = urllib.parse.quote(img_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&enhance=true"
        # link direto pro Vercel gerar
        return f"[IMAGE]{image_url}||{img_prompt}"

    if low.startswith("ensina:") and "|" in raw:
        try:
            _, c = raw.split("ensina:", 1)
            qp, ap = c.split("|", 1)
            save_memory(qp.strip(), ap.strip())
            return f"Beleza, aprendi sobre '{qp.strip()}'."
        except:
            return "Usa: ensina: pergunta | resposta"

    if is_greeting(raw):
        return "Olá! Tudo bem? Posso conversar ou gerar imagens pra você. Tenta: 'gera imagem de um leão no espaço'"

    if "obrigado" in low or "valeu" in low:
        return "De nada! Precisa de mais alguma coisa?"

    mem = get_memory()
    if low in mem: return mem[low]
    close = difflib.get_close_matches(low, mem.keys(), n=1, cutoff=0.85)
    if close: return mem[close[0]]

    wiki = search_wikipedia(raw)
    if wiki:
        save_memory(raw, wiki)
        return wiki[:600] + "\n\nQuer que eu gere uma imagem sobre isso?"

    return "Entendi. Me conta mais? Ou se quiser uma imagem, diga: gera imagem de..."

# ---------- HTML COM SUPORTE A IMAGEM ----------
HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlphAI • Imagens</title>
<style>
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#111;display:flex;flex-direction:column;height:100vh}
header{padding:18px;text-align:center;font-weight:800;border-bottom:1px solid #eee}
header span{font-weight:400;font-size:12px;color:#666;display:block;margin-top:2px}
#chat{flex:1;overflow-y:auto;padding:20px;max-width:720px;margin:0 auto;width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:14px;padding-bottom:100px}
.bubble{padding:14px 18px;border-radius:20px;max-width:85%;line-height:1.5;font-size:15px;white-space:pre-wrap;word-break:break-word}
.user{background:#111;color:#fff;align-self:flex-end;border-bottom-right-radius:6px}
.bot{background:#f2f2f2;align-self:flex-start;border-bottom-left-radius:6px}
.bubble img{max-width:100%;border-radius:14px;margin-top:8px;display:block}
.img-prompt{font-size:12px;color:#666;margin-top:6px}
#bar{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #eee;padding:12px;display:flex;max-width:720px;margin:0 auto;gap:8px}
input{flex:1;padding:14px 18px;border-radius:24px;border:1px solid #ddd;outline:none}
button{padding:14px 20px;border-radius:24px;border:none;background:#111;color:#fff;font-weight:600}
.small{font-size:11px;color:#999;text-align:center;margin-top:4px}
</style></head><body>
<header>AlphAI <span>Conversa natural + Geração de imagens</span></header>
<div id="chat"><div id="msgs"></div><div id="typing" style="display:none;font-size:13px;color:#888">Gerando imagem...</div></div>
<div id="bar"><input id="q" placeholder="Converse ou diga: gera imagem de..."><button id="send">Enviar</button></div>
<script>
const msgs=document.getElementById('msgs'), input=document.getElementById('q'), typing=document.getElementById('typing');
function addText(t,c){
  let d=document.createElement('div'); d.className='bubble '+c;
  // verifica se é imagem
  if(t.startsWith('[IMAGE]')){
    let parts = t.replace('[IMAGE]','').split('||');
    let url = parts[0];
    let prompt = parts[1] || '';
    d.innerHTML = `Gerando: "${prompt}"<br><img src="${url}" loading="lazy" onerror="this.parentElement.textContent='Erro ao gerar imagem, tenta de novo'"><div class="img-prompt">Prompt: ${prompt}</div><div class="small">AlphAI Image • Pollinations</div>`;
  } else {
    d.textContent = t;
  }
  msgs.appendChild(d); window.scrollTo(0,document.body.scrollHeight);
}
async function send(){
 let v=input.value.trim(); if(!v) return;
 addText(v,'user'); input.value=''; typing.style.display='block';
 let r=await fetch('/ask?q='+encodeURIComponent(v));
 let t=await r.text();
 typing.style.display='none';
 addText(t,'bot');
}
document.getElementById('send').onclick=send;
input.addEventListener('keydown',e=>{if(e.key==='Enter')send()});
addText('Olá! Agora eu também gero imagens. Exemplos:\\n• gera imagem de Maputo futurista\\n• crie imagem de um gato programador\\n• desenha um dragão de gelo','bot');
</script>
</body></html>
"""

@app.route("/")
def home(): return render_template_string(HTML)
@app.route("/ask")
def ask(): return answer(request.args.get("q",""))

# rota direta de imagem também
@app.route("/image")
def image_route():
    prompt = request.args.get("q","")
    if not prompt: return "Falta prompt"
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&enhance=true"
    return redirect(url)

