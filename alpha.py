from flask import Flask, request, render_template_string
import requests, datetime
app = Flask(__name__)
FB = "https://alpha-98bb1-default-rtdb.firebaseio.com"

CHAT_HTML = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlphAI</title>
<style>
body{font-family:Inter,sans-serif;background:#ffffff;color:#111;margin:0}
header{border-bottom:1px solid #eee;padding:16px;text-align:center;font-weight:600}
#chat{max-width:700px;margin:0 auto;padding:24px;padding-bottom:90px}
.msg{padding:14px 18px;border-radius:12px;margin:10px 0;line-height:1.5;max-width:85%}
.user{background:#111;color:white;margin-left:auto}
.bot{background:#f5f5f5}
#box{position:fixed;bottom:0;left:0;right:0;background:white;border-top:1px solid #eee;padding:12px;display:flex;max-width:700px;margin:0 auto}
input{flex:1;padding:14px 18px;border-radius:24px;border:1px solid #ddd;outline:none}
button{margin-left:8px;padding:14px 22px;border-radius:24px;border:none;background:#111;color:white;cursor:pointer}
small{color:#999}
</style></head><body>
<header>AlphAI • Online</header>
<div id="chat"><div id="msgs"></div></div>
<div id="box"><input id="q" placeholder="Digite sua mensagem..."><button onclick="send()">Enviar</button></div>
<script>
const msgs=document.getElementById('msgs');
function add(t,cls){let d=document.createElement('div');d.className='msg '+cls;d.innerHTML=t;msgs.appendChild(d);window.scrollTo(0,document.body.scrollHeight)}
async function send(){
 let q=document.getElementById('q').value.trim(); if(!q) return;
 add(q,'user'); document.getElementById('q').value='';
 let r=await fetch('/api?q='+encodeURIComponent(q)); let txt=await r.text();
 add(txt,'bot');
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')send()})
add('Olá! Sou o AlphAI. Como posso ajudar hoje?','bot')
</script></body></html>
"""

ADMIN_HTML = """
<h2>Admin AlphAI</h2>
<form action="/admin/save">
Pergunta:<br><input name="p" style="width:80%"><br>
Resposta:<br><textarea name="r" style="width:80%;height:100px"></textarea><br>
<button>Salvar no Firebase</button>
</form>
<p><a href="/api/list">Ver memoria JSON</a></p>
"""

@app.route("/")
def home():
    return render_template_string(CHAT_HTML)

@app.route("/admin")
def admin():
    return render_template_string(ADMIN_HTML)

@app.route("/admin/save")
def admin_save():
    p=request.args.get("p","").strip()
    r=request.args.get("r","").strip()
    if not p or not r: return "Preencha tudo"
    safe = "".join([c if c.isalnum() else "_" for c in p.lower()])[:60]
    try:
        requests.put(f"{FB}/memoria/{safe}.json", json={"original":p, "resposta":r, "data":str(datetime.date.today())}, timeout=10)
        return f"Salvo: {p} -> {r} <br><a href='/admin'>Voltar</a>"
    except Exception as e:
        return str(e)

@app.route("/api")
def api():
    q=request.args.get("q","").strip()
    if not q: return "Como posso ajudar?"
    try:
        dados=requests.get(f"{FB}/memoria.json", timeout=8).json() or {}
        ql=q.lower()
        # exato
        for v in dados.values():
            if v.get("original","").lower() == ql:
                return v.get("resposta")
        # contem
        for v in dados.values():
            if ql in v.get("original","").lower() or v.get("original","").lower() in ql:
                return v.get("resposta")
    except: pass
    return "Ainda estou aprendendo sobre isso. Nossa equipe vai atualizar minha base em breve."

@app.route("/api/list")
def list_mem():
    try:
        return requests.get(f"{FB}/memoria.json", timeout=8).json() or {}
    except Exception as e:
        return str(e)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
