from flask import Flask, request, render_template_string
import requests, json, re, math, ast, operator, difflib, datetime, os

app = Flask(__name__)
FB = "https://alpha-98bb1-default-rtdb.firebaseio.com"

# MEMÓRIA
try:
    data = requests.get(f"{FB}/memoria.json", timeout=5).json() or {}
    cerebro = {v.get("original","").lower(): v.get("resposta","") for k,v in data.items() if isinstance(v,dict) and "resposta" in v}
except:
    cerebro = {}

def salvar_fb(p,r):
    try:
        safe = "".join(c if c.isalnum() else "_" for c in p.lower())[:60]
        requests.put(f"{FB}/memoria/{safe}.json", json={"original":p,"resposta":r}, timeout=5)
    except: pass

# MATEMATICA
OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow,ast.USub:operator.neg}
def eval_node(n):
    if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return n.value
    if isinstance(n,ast.BinOp): return OPS[type(n.op)](eval_node(n.left),eval_node(n.right))
    if isinstance(n,ast.UnaryOp): return OPS[type(n.op)](eval_node(n.operand))
    raise ValueError

def responder(perg):
    p=perg.strip()
    pl=p.lower()
    
    # ADMIN ENSINAR - só funciona no /admin ou com prefixo oculto
    if pl.startswith("ensina:") and "|" in p:
        _, rest = p.split("ensina:",1)
        q,a = rest.split("|",1)
        q=q.strip(); a=a.strip()
        cerebro[q.lower()]=a
        salvar_fb(q,a)
        return f"Salvo: {q}"

    # 1. MEMÓRIA EXATA
    if pl in cerebro: return cerebro[pl]
    # 2. APROXIMADO
    m=difflib.get_close_matches(pl, cerebro.keys(), n=1, cutoff=0.8)
    if m: return cerebro[m[0]]

    # 3. MATEMATICA
    try:
        expr=re.sub(r'[^0-9+\-*/().\s]','',pl.replace('x','*').replace('vezes','*'))
        if expr and len(expr)>1 and any(o in expr for o in "+-*/"):
            res=eval_node(ast.parse(expr,mode='eval').body)
            return f"{expr.strip()} = {res}"
    except: pass

    if "raiz" in pl:
        nums=re.findall(r'\d+\.?\d*',pl)
        if nums: return f"Raiz quadrada de {nums[0]} = {math.sqrt(float(nums[0])):.4f}"

    # 4. WIKIPEDIA RÁPIDO
    try:
        q_busca=re.sub(r'o que e|quem e|qual e|\?','',pl).strip()
        r=requests.get(f"https://pt.wikipedia.org/w/api.php?action=query&list=search&srsearch={q_busca}&format=json",timeout=3).json()
        if r.get("query",{}).get("search"):
            tit=r["query"]["search"][0]["title"].replace(" ","_")
            s=requests.get(f"https://pt.wikipedia.org/api/rest_v1/page/summary/{tit}",timeout=3).json()
            if s.get("extract"):
                resp=s["extract"][:600]
                cerebro[pl]=resp
                salvar_fb(pl,resp)
                return resp
    except: pass

    return "Ainda não tenho essa informação na minha base. Em breve será atualizada."

HTML="""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlphAI</title>
<style>
body{margin:0;font-family:Inter,sans-serif;background:#fff;color:#111;display:flex;flex-direction:column;height:100vh}
header{padding:16px;text-align:center;font-weight:600;border-bottom:1px solid #eee}
#chat{flex:1;overflow-y:auto;padding:20px;max-width:700px;margin:0 auto;width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:12px;padding-bottom:90px}
.msg{padding:14px 18px;border-radius:18px;max-width:80%;line-height:1.4;font-size:15px}
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
def ask():
    return responder(request.args.get("q",""))

@app.route("/admin")
def admin():
    return '<form action="/ask">Pergunta: <input name="q" value="ensina: pergunta | resposta" style="width:80%"><br><button>Salvar</button></form>'

if __name__=="__main__": app.run(host="0.0.0.0",port=5000)
