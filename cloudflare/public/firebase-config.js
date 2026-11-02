// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js";
import { getDatabase } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-database.js";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyD_7AEVjzNn1gyjCnHYdN2FbJp2DdGB5tI",
  authDomain: "alphai-ultra.firebaseapp.com",
  databaseURL: "https://alphai-ultra-default-rtdb.firebaseio.com",
  projectId: "alphai-ultra",
  storageBucket: "alphai-ultra.firebasestorage.app",
  messagingSenderId: "663507487904",
  appId: "1:663507487904:web:4b83932267d5ce72154dc5"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getDatabase(app);
