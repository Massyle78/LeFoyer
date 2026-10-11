// État de l'application, gardé sur le téléphone (localStorage). Rien n'est envoyé nulle part.
import { parseDemo } from './logic.js';

const KEY = 'busbuddy.v2';
export const LANGS = ['en', 'fr', 'de', 'it'];

// voice / colors / vibration : réglages de l'écran « Réglages » (tous activés par défaut)
const defaults = { lang: null, line: null, dest: null, voice: true, colors: true, vibration: true };

function read() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(KEY) || '{}') };
  } catch {
    return { ...defaults };
  }
}

export const params = new URLSearchParams(location.search);
// La démo automatique tourne toujours depuis la configuration par défaut et n'écrit rien : elle ne laisse aucune trace
// (langue, arrêt, réglages) dans le navigateur, pour la personne qui ouvrirait ensuite l'application sur le même appareil.
const demoMode = parseDemo(params.get('demo')) > 0;
export const store = demoMode ? { ...defaults } : read();

// Réglages venant de l'adresse (QR code du bus : /?line=8) ; ?lang=fr ; ?demo=2 ; ?speed=20 (secondes)
if (params.get('lang') && LANGS.includes(params.get('lang'))) store.lang = params.get('lang');
if (!store.lang) {
  const guess = (navigator.language || 'en').slice(0, 2);
  store.lang = LANGS.includes(guess) ? guess : 'en';
}
if (params.get('line') && params.get('line') !== store.line) {
  store.line = params.get('line');
  store.dest = null; // un autre bus : l'ancien arrêt n'a plus de sens
}

// ?demo=x : démo automatique (x = vitesse : 1 normale, 2 deux fois plus vite...) ; &loop=1 la rejoue en boucle ;
// &autostart=1 la lance sans toucher l'écran. ?manual=1 : bandeau « arrêt suivant » pour faire avancer le bus à la main.
export const demoSpeed = parseDemo(params.get('demo'));
export const demo = demoSpeed > 0;
export const demoLoop = params.get('loop') === '1';
// &tour=pitch : la démo courte d'une minute (bonjour, vérifier, acheter, aide, notifications) ; sinon le tour complet
export const demoTour = params.get('tour') === 'pitch' ? 'pitch' : 'full';
export const demoAutostart = params.get('autostart') === '1';
// &intro=it : la démo démarre dans cette langue (on y dit bonjour) puis passe à la langue demandée par ?lang= (ex. ?lang=fr&intro=it)
export const demoFinalLang = store.lang;
export const demoIntro = demo && LANGS.includes(params.get('intro')) && params.get('intro') !== store.lang ? params.get('intro') : null;
if (demoIntro) store.lang = demoIntro;
export const manual = params.get('manual') === '1';
export const speedSeconds = Number(params.get('speed') ?? (manual || demo ? 0 : 30));

export function save() {
  if (demoMode) return;
  try {
    localStorage.setItem(KEY, JSON.stringify(store));
  } catch {
    /* mode privé : on continue sans mémoire */
  }
}
