# AlphAI ULTRA 2.0

## Funcionalidades
- Interface responsiva com modos Conversar, Pesquisar e Programar.
- IA generativa através de API compatível com Chat Completions.
- Pesquisa web leve via DuckDuckGo, com resumo Wikipédia como fallback.
- Envio de imagem para modelos que suportem visão.
- Memória SQLite separada por ID de sessão.
- Endpoint de saúde `/health`.

## Instalar no Android/Termux
```bash
pkg update
pkg install python
cd ~/storage/downloads/AlphAI_ULTRA_2_0
pip install -r requirements.txt
cp .env.example .env
nano .env
python app.py
```
Define `AI_API_KEY`, `AI_MODEL` e, se necessário, `AI_BASE_URL` no `.env`. Depois abre `http://127.0.0.1:5000`.

## Vercel
Configura `AI_API_KEY`, `AI_MODEL` e `AI_BASE_URL` nas variáveis de ambiente. SQLite local pode não persistir em ambiente serverless; usa uma base de dados externa para memória persistente.

## Limitações e segurança
A pesquisa pode falhar por bloqueios ou indisponibilidade externa. Análise de imagens exige modelo com visão. Não coloques chaves no código ou no repositório. O ID de sessão não é autenticação; não guardes dados sensíveis. Imagens são enviadas ao fornecedor de IA configurado. A aplicação não treina um modelo próprio nem executa automaticamente código gerado.
