import { auth } from "./firebase-config.js";

import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js";

let resolveLogin;

const authenticated = new Promise(resolve => {
  resolveLogin = resolve;
});

function showLogin() {
  if (document.getElementById("alpha-auth-gate")) return;

  const gate = document.createElement("div");
  gate.id = "alpha-auth-gate";

  gate.innerHTML = `
    <style>
      #alpha-auth-gate {
        position:fixed;
        inset:0;
        z-index:99999;
        background:#090b13;
        color:white;
        display:grid;
        place-items:center;
        padding:20px;
        font-family:inherit;
      }
      .alpha-auth-card {
        width:100%;
        max-width:390px;
        padding:28px;
        border:1px solid #30364b;
        border-radius:18px;
        background:#111522;
      }
      .alpha-auth-card h2 {margin:0 0 8px}

      .auth-brand{display:flex;align-items:center;gap:12px}
      .auth-brand img{width:46px;height:46px;object-fit:contain}
      .auth-brand h2{margin:0}
      .auth-company{margin-top:22px;text-align:center;color:#8e9ab3;font-size:12px}

      .alpha-auth-card p {color:#aab2c5}
      .alpha-auth-card input {
        box-sizing:border-box;
        width:100%;
        padding:14px;
        margin:8px 0;
        border:1px solid #394158;
        border-radius:9px;
        background:#090d18;
        color:white;
      }
      .alpha-auth-card button {
        width:100%;
        padding:13px;
        margin-top:12px;
        border:0;
        border-radius:9px;
        background:#6558ed;
        color:white;
        font-weight:bold;
      }
      #alpha-auth-toggle {
        background:transparent;
        border:1px solid #394158;
      }
      #alpha-auth-error {
        color:#ff8d8d;
        font-size:13px;
      }
    </style>

    <div class="alpha-auth-card">
      <div class="auth-brand"><img src="/static/assets/alphai-icon.webp" alt="Alpha"><h2>Alpha</h2></div>
      <p id="alpha-auth-description">
        Entra na tua conta para continuar.
      </p>

      <form id="alpha-auth-form">
        <input id="alpha-email" type="email"
          placeholder="O teu email" required autocomplete="email">

        <input id="alpha-password" type="password"
          placeholder="Palavra-passe (mínimo 6 caracteres)"
          required minlength="6" autocomplete="current-password">

        <div id="alpha-auth-error" role="alert"></div>

        <button id="alpha-auth-submit" type="submit">
          Iniciar sessão
        </button>
      </form>

      <button id="alpha-auth-toggle" type="button">
        Criar uma conta
      </button>
    <div class="auth-company">Alpha Technologies</div>
    </div>
  `;

  document.body.appendChild(gate);

  let registerMode = false;

  const form = gate.querySelector("#alpha-auth-form");
  const toggle = gate.querySelector("#alpha-auth-toggle");
  const submit = gate.querySelector("#alpha-auth-submit");
  const error = gate.querySelector("#alpha-auth-error");

  toggle.addEventListener("click", () => {
    registerMode = !registerMode;

    submit.textContent = registerMode
      ? "Criar conta"
      : "Iniciar sessão";

    toggle.textContent = registerMode
      ? "Já tenho uma conta"
      : "Criar uma conta";

    gate.querySelector("#alpha-auth-description").textContent =
      registerMode
        ? "Cria a tua conta Alpha."
        : "Entra na tua conta para continuar.";

    error.textContent = "";
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const email = gate.querySelector("#alpha-email").value.trim();
    const password = gate.querySelector("#alpha-password").value;

    submit.disabled = true;
    error.textContent = "";

    try {
      if (registerMode) {
        await createUserWithEmailAndPassword(auth, email, password);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
    } catch (e) {
      const messages = {
        "auth/email-already-in-use": "Este email já tem uma conta.",
        "auth/invalid-email": "Email inválido.",
        "auth/weak-password": "A palavra-passe é demasiado fraca.",
        "auth/invalid-credential": "Email ou palavra-passe incorretos.",
        "auth/network-request-failed": "Erro de ligação. Tenta novamente.",
        "auth/too-many-requests": "Demasiadas tentativas. Aguarda um pouco."
      };

      error.textContent =
        messages[e.code] || "Não foi possível autenticar. Verifica os dados.";
    } finally {
      submit.disabled = false;
    }
  });
}

onAuthStateChanged(auth, user => {
  if (user) {
    document.getElementById("alpha-auth-gate")?.remove();
    resolveLogin(user);
  } else {
    showLogin();
  }
});

window.alphaGetIdToken = async () => {
  const user = auth.currentUser;
  return user ? await user.getIdToken() : null;
};

window.alphaSignOut = () => signOut(auth);

export function initAlphaAuth() {
  return authenticated;
}
