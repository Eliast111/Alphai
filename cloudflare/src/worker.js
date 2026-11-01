const MAX_MESSAGE_CHARS = 2000;
const MAX_CONTEXT_MESSAGES = 12;

const SYSTEM_PROMPT = [
  "És a AlphAI ULTRA, uma assistente digital avançada.",
  "Responde em português claro, natural e profissional.",
  "Sê honesta sobre incertezas.",
  "Não inventes fontes nem afirmes ter feito ações que não fizeste.",
  "Usa o contexto recente quando for relevante.",
  "Se não souberes algo, explica a limitação."
].join(" ");

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store"
    }
  });
}

function normalize(text) {
  return text.toLocaleLowerCase("pt-PT").replace(/\s+/g, " ").trim();
}

function isGreeting(text) {
  const value = normalize(text).replace(/[!.,?…]+$/g, "");

  return [
    "ola", "olá", "oi", "oie", "hey", "hi", "hello",
    "bom dia", "boa tarde", "boa noite",
    "ola alphai", "olá alphai", "oi alphai"
  ].includes(value);
}

function isThanks(text) {
  const value = normalize(text);

  return [
    "obrigado", "obrigada", "muito obrigado",
    "valeu", "agradeço"
  ].some(item => value.includes(item));
}

function imagePrompt(text) {
  const triggers = [
    "gera imagem de",
    "gera uma imagem de",
    "gerar imagem de",
    "gerar uma imagem de",
    "crie imagem de",
    "cria imagem de",
    "cria uma imagem de",
    "crie uma imagem de",
    "desenha",
    "desenhe",
    "imagem de",
    "faz uma imagem de"
  ];

  const lower = text.toLocaleLowerCase("pt-PT");

  for (const trigger of triggers) {
    const position = lower.indexOf(trigger);

    if (position >= 0) {
      const prompt = text
        .slice(position + trigger.length)
        .trim()
        .replace(/^[ \t:,\-.]+/, "");

      if (prompt.length >= 2) {
        return prompt.slice(0, 500);
      }
    }
  }

  return null;
}

function makeImageUrl(prompt) {
  return "https://image.pollinations.ai/prompt/" +
    encodeURIComponent(prompt) +
    "?width=1024&height=1024&nologo=true&enhance=true";
}

function cleanHistory(history) {
  if (!Array.isArray(history)) return [];

  return history
    .slice(-MAX_CONTEXT_MESSAGES)
    .filter(item =>
      item &&
      ["user", "assistant"].includes(item.role) &&
      typeof item.content === "string"
    )
    .map(item => ({
      role: item.role,
      content: item.content.trim().slice(0, MAX_MESSAGE_CHARS)
    }))
    .filter(item => item.content.length > 0);
}

async function askGroq(question, history, env) {
  if (!env.GROQ_API_KEY) return null;

  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    ...history,
    { role: "user", content: question }
  ];

  try {
    const response = await fetch(
      "https://api.groq.com/openai/v1/chat/completions",
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.GROQ_API_KEY}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: env.GROQ_MODEL || "openai/gpt-oss-120b",
          messages,
          temperature: 0.6,
          max_completion_tokens: 1200
        }),
        signal: AbortSignal.timeout(45000)
      }
    );

    if (!response.ok) {
      console.error("Groq HTTP error:", response.status);
      return null;
    }

    const data = await response.json();
    const answer = data.choices?.[0]?.message?.content;

    if (typeof answer !== "string" || !answer.trim()) return null;

    return {
      text: answer.trim().slice(0, 8000),
      sources: [],
      provider: "Groq"
    };
  } catch (error) {
    console.error("Groq request failed:", error.message);
    return null;
  }
}

async function askGemini(question, history, env) {
  if (!env.GEMINI_API_KEY) return null;

  const model = env.GEMINI_MODEL || "gemini-3.8-flash";

  const contents = [];

  for (const item of history) {
    const role = item.role === "assistant" ? "model" : "user";

    if (!contents.length && role === "model") continue;

    if (contents.length && contents.at(-1).role === role) {
      contents.at(-1).parts[0].text += "\n" + item.content;
    } else {
      contents.push({
        role,
        parts: [{ text: item.content }]
      });
    }
  }

  if (contents.length && contents.at(-1).role === "user") {
    contents.at(-1).parts[0].text += "\n" + question;
  } else {
    contents.push({
      role: "user",
      parts: [{ text: question }]
    });
  }

  const url =
    `https://generativelanguage.googleapis.com/v1beta/models/` +
    `${encodeURIComponent(model)}:generateContent`;

  const payload = {
    systemInstruction: {
      parts: [{ text: SYSTEM_PROMPT }]
    },
    contents,
    generationConfig: {
      maxOutputTokens: 1024
    }
  };

  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": env.GEMINI_API_KEY
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(90000)
      });

      if ([429, 500, 502, 503, 504].includes(response.status)) {
        console.error("Gemini temporary error:", response.status);

        if (attempt < 2) {
          await new Promise(resolve =>
            setTimeout(resolve, attempt === 0 ? 2000 : 5000)
          );
          continue;
        }

        return null;
      }

      if (!response.ok) {
        console.error("Gemini HTTP error:", response.status);
        return null;
      }

      const data = await response.json();

      const answer = (data.candidates?.[0]?.content?.parts || [])
        .map(part => typeof part.text === "string" ? part.text : "")
        .join("\n")
        .trim();

      if (!answer) return null;

      return {
        text: answer.slice(0, 8000),
        sources: [],
        provider: "Gemini"
      };
    } catch (error) {
      console.error("Gemini request failed:", error.message);

      if (attempt === 2) return null;

      await new Promise(resolve =>
        setTimeout(resolve, attempt === 0 ? 2000 : 5000)
      );
    }
  }

  return null;
}

async function askAI(question, history, env) {
  const groq = await askGroq(question, history, env);
  if (groq) return groq;

  return await askGemini(question, history, env);
}

async function handleAsk(request, env) {
  let payload;

  try {
    payload = await request.json();
  } catch {
    return json({ error: "JSON inválido." }, 400);
  }

  const question = payload?.q;

  if (typeof question !== "string" || !question.trim()) {
    return json({ error: "Escreve uma mensagem." }, 400);
  }

  if (question.length > MAX_MESSAGE_CHARS) {
    return json({ error: "Mensagem demasiado longa." }, 413);
  }

  const q = question.trim();
  const history = cleanHistory(payload.history);

  const image = imagePrompt(q);

  if (image) {
    return json({
      text: "A tua imagem está pronta para ser gerada.",
      image_url: makeImageUrl(image),
      prompt: image,
      sources: []
    });
  }

  if (isGreeting(q)) {
    return json({
      text: "Olá! Sou a AlphAI ULTRA. Como posso ajudar-te hoje?",
      sources: []
    });
  }

  if (isThanks(q)) {
    return json({
      text: "De nada! Estou aqui para ajudar.",
      sources: []
    });
  }

  const result = await askAI(q, history, env);

  if (result) return json(result);

  return json({
    text: "Neste momento não consegui obter uma resposta. Verifica a configuração dos modelos e tenta novamente.",
    sources: []
  }, 503);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return json({
        status: "ok",
        service: "AlphAI ULTRA",
        ai: Boolean(env.GROQ_API_KEY || env.GEMINI_API_KEY)
      });
    }

    if (request.method === "POST" && url.pathname === "/ask") {
      return handleAsk(request, env);
    }

    if (url.pathname === "/ask" && request.method !== "POST") {
      return json({ error: "Método não permitido." }, 405);
    }

    if (url.pathname === "/health" && request.method !== "GET") {
      return json({ error: "Método não permitido." }, 405);
    }

    if (url.pathname.startsWith("/api/")) {
      return json({ error: "Rota não encontrada." }, 404);
    }

    return env.ASSETS.fetch(request);
  }
};
