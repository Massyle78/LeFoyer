// Services d'accessibilité BRANCHABLES (voix, vibration, écran allumé...).
//
// Ajouter une fonction d'accessibilité (lecture en langue des signes, flash lumineux, commande vocale...) =
// écrire un objet { name, speak?, feedback?, stop? } et l'enregistrer avec `register()` dans main.js.
// Les écrans ne parlent qu'à `a11y` : ils n'ont rien à changer.
//
//   a11y.speak(text, lang)   dire ce texte à voix haute (touche d'un bouton, phrase à montrer...)
//   a11y.feedback(kind)      retour sensoriel : "tap" | "alarm"
//   a11y.stop()              couper ce qui est en cours
import { store } from './store.js';

const services = [];

export function register(service) {
  services.push(service);
}

function each(method, ...args) {
  for (const service of services) {
    try {
      service[method]?.(...args);
    } catch (error) {
      console.warn(`service d'accessibilité « ${service.name} » en erreur`, error);
    }
  }
}

export const a11y = {
  speak: (text, lang) => each('speak', text, lang),
  feedback: (kind) => each('feedback', kind),
  stop: () => each('stop'),
};

// --- Synthèse vocale (Web Speech API) : parle dès le toucher --------------------------------
export const speechService = {
  name: 'speech',
  voices: [],
  get available() {
    return 'speechSynthesis' in window;
  },
  init() {
    if (!this.available) return;
    const load = () => {
      this.voices = speechSynthesis.getVoices();
    };
    load();
    speechSynthesis.addEventListener?.('voiceschanged', load);
  },
  speak(text, lang) {
    if (!this.available || !store.voice || !text) return;
    speechSynthesis.cancel(); // la dernière phrase remplace la précédente
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = 0.9; // un peu plus lent : plus facile à comprendre
    const prefix = lang.slice(0, 2);
    const voice = this.voices.find((v) => v.lang === lang) ?? this.voices.find((v) => v.lang.startsWith(prefix));
    if (voice) utterance.voice = voice;
    speechSynthesis.speak(utterance);
  },
  stop() {
    if (this.available) speechSynthesis.cancel();
  },
};

// --- Vibration (Android ; ignorée ailleurs) ------------------------------------------------
export const vibrationService = {
  name: 'vibration',
  patterns: { tap: 20, alarm: [400, 200, 400, 200, 400] },
  feedback(kind) {
    if (navigator.vibrate && this.patterns[kind]) navigator.vibrate(this.patterns[kind]);
  },
};

// --- Écran allumé pendant le trajet (sinon le téléphone se verrouille et l'alarme n'est pas vue) ---
export const wakeLockService = {
  name: 'wake-lock',
  lock: null,
  init() {
    if (!('wakeLock' in navigator)) return;
    const acquire = async () => {
      try {
        this.lock = await navigator.wakeLock.request('screen');
      } catch {
        /* refusé (économie d'énergie...) : sans importance */
      }
    };
    acquire();
    document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && acquire());
  },
};
