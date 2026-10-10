// Services d'accessibilité BRANCHABLES (voix, vibration, écran allumé...).
//
// Ajouter une fonction d'accessibilité (lecture en langue des signes, flash lumineux, commande vocale...) =
// écrire un objet { name, speak?, feedback?, stop? } et l'enregistrer avec `register()` dans main.js.
// Les écrans ne parlent qu'à `a11y` : ils n'ont rien à changer.
//
//   a11y.speak(text, lang)   dire ce texte à voix haute (touche d'un bouton, phrase à montrer...)
//   a11y.feedback(kind)      retour sensoriel : "tap" | "confirm" | "yes" | "no" | "stopped" | "soon" | "arrive"
//                            (chaque service choisit ce qu'il fait ; la vibration respecte le réglage « Vibration »)
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

// --- Vibration (Android ; ignorée ailleurs, ex. iPhone) ---------------------------------------
// Un « langage » de motifs, du plus discret au plus fort, pour savoir ce qui se passe sans regarder :
//   tap      1 pulsation très courte    je touche un bouton
//   confirm  2 pulsations courtes       choix enregistré (mon arrêt, une demande)
//   yes      2 pulsations courtes       « oui, c'est le bon bus »  (vert)
//   no       1 longue pulsation         « non, ce n'est pas le bon bus »  (rouge)
//   stopped  1 pulsation moyenne        le bus vient de s'arrêter à un arrêt
//   soon     2 pulsations moyennes      orange : mon arrêt est le prochain, je me prépare
//   arrive   3 longues + 1 très longue  rouge : C'EST MON ARRÊT, je descends (répété jusqu'à « OK »)
export const vibrationService = {
  name: 'vibration',
  patterns: {
    tap: 15,
    confirm: [70, 60, 70],
    yes: [70, 60, 70],
    no: 350,
    stopped: 120,
    soon: [250, 150, 250],
    arrive: [600, 200, 600, 200, 600, 200, 1000],
  },
  get available() {
    return typeof navigator.vibrate === 'function';
  },
  feedback(kind) {
    if (!store.vibration || !this.available || !this.patterns[kind]) return;
    navigator.vibrate(this.patterns[kind]);
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
