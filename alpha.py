from flask import Flask, request, render_template_string
import requests, difflib

app = Flask(__name__)
FB = "https://alpha-98bb1-default-rtdb.firebaseio.com"

BASE = {
"ola": "Olá! 😊 Como posso ajudar hoje?",
"oi": "Oi! Tudo bem? Em que posso te ajudar?",
"quem e voce": "Sou o AlphAI, criado pelo Eliast. Como posso te ajudar?",
"o que e quimica": "A Química é a ciência que estuda a composição, estrutura, propriedades e transformações da matéria.",
"o que e fisica": "A Física estuda a natureza, energia, matéria e suas interações.",
"o que e biologia": "Biologia é a ciência que estuda os seres vivos.",
}

def get_mem():
    try:
        d=requests.get(f"{FB}/memoria.json",timeout=5).json() or {}
        m={v.get("original","").lower():v.get("resposta","") for v in d.values() if isinstance(v,dict)}
        BASE.update(m)
    except: pass

def salvar(p,r):
    try:
        safe="".join(c if c.isalnum() else "_" for c in p.lower())[:60]
        requests.put(f"{FB}/memoria/{safe}.json", json={"original":p,"resposta":r}, timeout=5)
    except: pass

def responder(perg):
    get_mem()
    p=perg.strip().lower()
    p_clean=p.replace("?","").replace("!","").strip()
    
    if p_clean.startswith("ensina:") and "|" in perg:
        q,a=perg.split("ensina:",1)[1].split("|",1)
        q=q.strip(); a=a.strip()
        salvar(q,a); BASE[q.lower()]=a
        return "Pronto! Aprendi."

    if p_clean in BASE: return BASE[p_clean]
    
    m=difflib.get_close_matches(p_clean, BASE.keys(), n=1, cutoff=0.7)
    if m: return BASE[m[0]]
    
    for k in BASE:
        if k in p_clean or p_clean in k:
            return BASE[k]
    
    return "Ainda estou organizando essa informação. Pode perguntar de outra forma? Exemplo: 'O que é química'"

HTML="""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlphAI</title>
<style>
body{margin:0;font-family:sans-serif;background:#fff;color:#111;display:flex;flex-direction:column;height:100vh}
header{padding:16px;text-align:center;font-weight:600;border-bottom:1px solid #eee}
#chat{flex:1;overflow-y:auto;padding:20px;max-width:700px;margin:0 auto;width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:12px;padding-bottom:90px}
.msg{padding:14px 18px;border-radius:18px;max-width:80%;line-height:1.4}
.user{background:#111;color:#fff;align-self:flex-end}
.bot{background:#f2f2f2;align-self:flex-start}
#box{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #eee;padding:12px;display:flex;max-width:700px;margin:0 auto}
input{flex:1;padding:14px 18px;border-radius:24px;border:1px solid #ddd;outline:none}
button{margin-left:8px;padding:14px 22px;border-radius:24px;border:none;background:#111;color:#fff}
</style></head><body>
<header>AlphAI • Online</header>
<div id="chat"><div id="msgs"></div></div>
<div id="box"><input id="q" placeholder="Digite sua mensagem..."><button onclick="send()">Enviar</button></div>
<script>
const m=document.getElementById('msgs');
function add(t,c){let d=document.createElement('div');d.className='msg '+c;d.innerText=t;m.appendChild(d);window.scrollTo(0,document.body.scrollHeight)}
async function send(){
 let q=document.getElementById('q').value.trim(); if(!q) return;
 add(q,'user'); document.getElementById('q').value='';
 let r=await fetch('/ask?q='+encodeURIComponent(q)); let txt=await r.text();
 add(txt,'bot');
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')send()})
add('Olá! Sou o AlphAI. Como posso ajudar hoje?','bot')
</script></body></html>
"""
@app.route("/")
def home(): return render_template_string(HTML)
@app.route("/ask")
def ask(): return responder(request.args.get("q",""))
@app.route("/admin")
def admin(): return '<form action="/ask">ensina: <input name="q" style="width:70%"><button>Salvar</button></form>'
