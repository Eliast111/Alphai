import os,re,sqlite3,urllib.parse
from datetime import datetime
from flask import Flask,jsonify,request,render_template
import requests
from dotenv import load_dotenv
load_dotenv()
app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=8*1024*1024
DB=os.getenv("ALPHAI_DB_PATH","alphai_memory.db")
KEY=os.getenv("AI_API_KEY","").strip()
BASE=os.getenv("AI_BASE_URL","https://api.openai.com/v1").rstrip("/")
MODEL=os.getenv("AI_MODEL","").strip()
def connect():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
with connect() as c:
 c.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, sid TEXT, question TEXT, answer TEXT, created TEXT)")
 c.execute("CREATE INDEX IF NOT EXISTS mem_sid ON memories(sid,id)")
def sid(v): return re.sub(r"[^a-zA-Z0-9_-]","",str(v or "guest"))[:80] or "guest"
def ask_ai(messages,image=None):
 if not KEY or not MODEL: return None,"Configura AI_API_KEY e AI_MODEL no ficheiro .env."
 msgs=list(messages)
 if image:
  msgs[-1]={"role":"user","content":[{"type":"text","text":msgs[-1]["content"] or "Analisa esta imagem."},{"type":"image_url","image_url":{"url":image}}]}
 try:
  r=requests.post(BASE+"/chat/completions",headers={"Authorization":"Bearer "+KEY},json={"model":MODEL,"messages":msgs,"temperature":0.7},timeout=35); r.raise_for_status()
  out=r.json()["choices"][0]["message"]["content"]
  if isinstance(out,list): out="\n".join(x.get("text","") for x in out if isinstance(x,dict))
  return str(out).strip(),None
 except Exception as e: return None,"Falha na API de IA. Verifica chave, modelo, URL e ligação. Detalhe: "+str(e)
def search(q):
 try:
  from bs4 import BeautifulSoup
  r=requests.post("https://html.duckduckgo.com/html/",data={"q":q},headers={"User-Agent":"Mozilla/5.0 AlphAI/2.0"},timeout=12); r.raise_for_status()
  soup=BeautifulSoup(r.text,"html.parser"); out=[]
  for el in soup.select(".result")[:6]:
   t=el.select_one(".result__title"); s=el.select_one(".result__snippet"); a=t.select_one("a") if t else None
   if t: out.append({"title":t.get_text(" ",strip=True),"snippet":s.get_text(" ",strip=True) if s else "","url":a.get("href","") if a else ""})
  return out
 except Exception: return []
def wiki(q):
 try:
  r=requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(q.replace(" ","_")),headers={"User-Agent":"AlphAI-ULTRA/2.0"},timeout=8)
  d=r.json()
  if r.ok and d.get("extract"): return {"title":d.get("title",q),"extract":d["extract"],"url":d.get("content_urls",{}).get("desktop",{}).get("page","")}
 except Exception: pass
 return None
@app.get("/")
def home(): return render_template("index.html")
@app.get("/health")
def health(): return jsonify(ok=True,app="AlphAI ULTRA 2.0",ai_configured=bool(KEY and MODEL))
@app.post("/api/chat")
def chat():
 b=request.get_json(silent=True) or {}; q=str(b.get("message","")).strip(); image=b.get("image_data"); mode=str(b.get("mode","chat")).lower(); session=sid(b.get("session_id"))
 if not q and not image: return jsonify(error="Escreve uma mensagem ou anexa uma imagem."),400
 if len(q)>12000: return jsonify(error="Mensagem demasiado longa."),413
 if image and (not isinstance(image,str) or not image.startswith("data:image/") or len(image)>6000000): return jsonify(error="Imagem inválida ou demasiado grande."),400
 sources=[]; w=None; prompt=q
 if mode=="search":
  sources=search(q)
  if sources: prompt="Responde em português com base nos resultados e inclui links. Pergunta: "+q+"\n"+ "\n".join(f"- {x['title']}: {x['snippet']} ({x['url']})" for x in sources)
  else:
   w=wiki(q)
   if w: prompt=f"Responde com base neste resumo limitado da Wikipédia. Pergunta: {q}\n{w['extract']}\n{w['url']}"
   else: return jsonify(answer="A pesquisa externa não está disponível agora. Tenta novamente mais tarde.",sources=[])
 system=("És AlphAI ULTRA, assistente de programação. Responde em português e fornece código completo, dependências e passos para executar. Não afirmes que testaste código." if mode=="code" else "És AlphAI ULTRA, sintetiza resultados web sem inventar fontes." if mode=="search" else "És AlphAI ULTRA. Responde em português europeu, com clareza e honestidade.")
 with connect() as c: rows=c.execute("SELECT question,answer FROM memories WHERE sid=? ORDER BY id DESC LIMIT 8",(session,)).fetchall()
 messages=[{"role":"system","content":system}]
 for row in reversed(rows): messages.extend([{"role":"user","content":row["question"]},{"role":"assistant","content":row["answer"]}])
 messages.append({"role":"user","content":prompt or "Analisa esta imagem."})
 answer,error=ask_ai(messages,image)
 if error:
  if mode=="search" and sources: answer="Resultados encontrados (sem síntese da IA):\n\n"+"\n\n".join(f"{x['title']}\n{x['snippet']}\n{x['url']}" for x in sources)
  elif mode=="search" and w: answer=f"{w['title']}\n\n{w['extract']}\n\nFonte: {w['url']}"
  else: return jsonify(answer=error,sources=sources,warning="Configuração necessária")
 with connect() as c:
  c.execute("INSERT INTO memories(sid,question,answer,created) VALUES(?,?,?,?)",(session,q or "[imagem enviada]",answer,datetime.utcnow().isoformat()+"Z"))
  c.execute("DELETE FROM memories WHERE sid=? AND id NOT IN (SELECT id FROM memories WHERE sid=? ORDER BY id DESC LIMIT 80)",(session,session))
 return jsonify(answer=answer,sources=sources,wikipedia=w,mode=mode)
@app.get("/api/memory")
def memory():
 with connect() as c: rows=c.execute("SELECT id,question,answer,created FROM memories WHERE sid=? ORDER BY id DESC LIMIT 80",(sid(request.args.get("session_id")),)).fetchall()
 return jsonify(items=[dict(x) for x in rows])
@app.delete("/api/memory")
def clear():
 b=request.get_json(silent=True) or {}
 with connect() as c: c.execute("DELETE FROM memories WHERE sid=?",(sid(b.get("session_id")),))
 return jsonify(ok=True)
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=False)
