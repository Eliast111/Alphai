# AlphAI ULTRA

Assistente digital com interface responsiva, conversação inteligente, memória de conhecimentos, pesquisa e criação de imagens. A experiência visual é independente do fornecedor do motor de IA.

Aplicação Flask com interface responsiva, histórico local no navegador, memória Firebase, pesquisa Wikipedia e geração de imagens por URL do Pollinations.

## Ficheiros

- `alpha.py`: aplicação Flask, rotas, lógica, HTML/CSS/JS.
- `api/index.py`: ponto de entrada para a Vercel.
- `requirements.txt`: dependências Python.
- `vercel.json`: configuração de deploy.
- `.env.example`: nomes das variáveis de ambiente (sem segredos).

## Executar localmente no Termux

1. Instala Python e Git, se ainda não estiverem instalados:

   ```bash
   pkg update
   pkg install python git
   ```

2. Entra na pasta do projeto e instala as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Inicia a aplicação:

   ```bash
   python alpha.py
   ```

4. Abre `http://127.0.0.1:5000` no navegador do telemóvel.

Sem variáveis de ambiente, a aplicação continua a abrir, permite saudações, pesquisa básica e tenta usar o Firebase público já indicado no código. A conversação inteligente requer configurar a credencial do motor de IA no servidor.

## Deploy na Vercel

1. Coloca estes ficheiros no repositório GitHub que está ligado ao projeto Vercel.
2. Confirma que `api/index.py`, `alpha.py`, `requirements.txt` e `vercel.json` estão na raiz/estrutura indicada.
3. No painel Vercel, abre **Project → Settings → Environment Variables**.
4. Adiciona as variáveis necessárias (ver abaixo) e faz redeploy.

### Variáveis

- `FIREBASE_DATABASE_URL`: URL do teu Realtime Database.
- `ALPHAI_ADMIN_TOKEN`: token privado forte para autorizar o comando `ensina:`.
- `GEMINI_API_KEY`: chave da API Google Gemini.
- `GEMINI_MODEL`: modelo Gemini; por defeito `gemini-2.5-flash`.
- `HTTP_TIMEOUT`: timeout de requests, por exemplo `8`.
- `MAX_MEMORY_ITEMS`: máximo de entradas lidas da memória, por exemplo `300`.

Não uses uma chave de API no frontend e nunca publiques o token administrativo no GitHub. O comando `ensina:` envia o token no cabeçalho `X-Admin-Token`; esta versão da interface não inclui um campo para o token. Para ensinar, usa um cliente HTTP autorizado ou acrescenta um formulário administrativo protegido.

## Endpoint de chat

`POST /ask`

Exemplo de corpo JSON:

```json
{
  "q": "O que é inteligência artificial?",
  "history": [
    {"role": "user", "content": "Quero aprender tecnologia"},
    {"role": "assistant", "content": "Podemos começar por IA."}
  ]
}
```

O servidor devolve JSON com `text`, `sources` e, em pedidos de imagem, `image_url` e `prompt`.

## Firebase: segurança importante

O código usa a API REST do Realtime Database. As regras atuais do teu Firebase determinam se a leitura e a escrita funcionam. Não abras as regras de escrita para toda a gente para fazer a aplicação funcionar. Para produção, configura autenticação e regras adequadas ou usa credenciais seguras no servidor. A memória não é literalmente infinita: esta versão lê no máximo `MAX_MEMORY_ITEMS` entradas por pedido.

## Notas

- O histórico de conversas é guardado no `localStorage` do navegador; não é sincronizado entre dispositivos.
- A geração de imagens depende do serviço externo Pollinations e pode falhar ou mudar.
- A Wikipedia é uma fonte de referência, não um motor de raciocínio. Se a API de IA não estiver configurada e a pesquisa falhar, a aplicação explica a limitação.
- A configuração de builds/rotas da Vercel pode precisar de ajustes se o projeto existente tiver outra estrutura. Testa primeiro num branch ou deployment de preview.


## Integração Gemini

As respostas conversacionais são geradas pela API Gemini a partir do backend Python.
Configura `GEMINI_API_KEY` nas Environment Variables da Vercel. Opcionalmente,
define `GEMINI_MODEL` (por defeito `gemini-2.5-flash`). Nunca coloques a chave no
HTML, JavaScript, GitHub ou num ficheiro público. O histórico recente é enviado
ao modelo para manter o contexto da conversa.

A geração de imagens continua a utilizar Pollinations nesta versão; esta alteração
integra Gemini para respostas de texto, não para geração de imagens.
