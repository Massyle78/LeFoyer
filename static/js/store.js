// État de l'application, gardé sur le téléphone (localStorage). Rien n'est envoyé nulle part.

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
export const store = read();

// Réglages venant de l'adresse (QR code du bus : /?line=8) ; ?lang=fr ; ?demo=1 ; ?speed=20 (secondes)
if (params.get('lang') && LANGS.includes(params.get('lang'))) store.lang = params.get('lang');
if (!store.lang) {
  const guess = (navigator.language || 'en').slice(0, 2);
  store.lang = LANGS.includes(guess) ? guess : 'en';
}
if (params.get('line') && params.get('line') !== store.line) {
  store.line = params.get('line');
  store.dest = null; // un autre bus : l'ancien arrêt n'a plus de sens
}

export const demo = params.get('demo') === '1';
export const speedSeconds = Number(params.get('speed') ?? (demo ? 0 : 30));

export function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(store));
  } catch {
    /* mode privé : on continue sans mémoire */
  }
}
