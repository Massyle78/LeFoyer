// Page de présentation : photos de l'équipe | démo automatique et interactive | QR code de la ligne 701.
//   /present          (ou static/present.html)
//   ?demo=1           vitesse de la démo (1 normale, 2 deux fois plus vite…)       [défaut 1]
//   ?lang=en|fr|de|it langue de la démo et des textes de la page                    [défaut en]
//   ?tour=full        le tour complet (environ 3 min) au lieu de la démo courte d'une minute (par défaut)
//   ?intro=it         la démo démarre dans cette langue (bonjour en italien) puis passe à ?lang=  (ex. ?lang=fr&intro=it)
//   ?qr=local         QR code du serveur qui sert la page (adresse réseau en local) au lieu du site déployé (par défaut)
//   ?loop=0           ne pas rejouer la démo en boucle                              [défaut : en boucle]
//   ?autostart=1      lance la démo sans l'écran de départ (mais la voix peut être bloquée par le navigateur)
//   ?rec=1            masque les commandes (enregistrement) ; touches : F plein écran, R relancer, L langue
const params = new URLSearchParams(location.search);
const LANGS = ['en', 'fr', 'de', 'it'];
const TEXTS = {
  en: { tagline: 'Take the bus on your own.', team: 'Le Foyer × HackaHealth', scan: 'Scan to try it', route: 'Morges ⇄ Lausanne',
        hint: 'Open your phone camera and point it at the code.', restart: 'Restart', full: 'Full screen' },
  fr: { tagline: 'Prendre le bus en toute autonomie.', team: 'Le Foyer × HackaHealth', scan: 'Scannez pour essayer', route: 'Morges ⇄ Lausanne',
        hint: "Ouvrez l'appareil photo de votre téléphone et visez le code.", restart: 'Relancer', full: 'Plein écran' },
  de: { tagline: 'Selbstständig mit dem Bus fahren.', team: 'Le Foyer × HackaHealth', scan: 'Scannen und ausprobieren', route: 'Morges ⇄ Lausanne',
        hint: 'Kamera des Telefons öffnen und auf den Code richten.', restart: 'Neu starten', full: 'Vollbild' },
  it: { tagline: "Prendere l'autobus in autonomia.", team: 'Le Foyer × HackaHealth', scan: 'Scansiona e prova', route: 'Morges ⇄ Lausanne',
        hint: 'Apri la fotocamera del telefono e inquadra il codice.', restart: 'Riavvia', full: 'Schermo intero' },
};

let lang = LANGS.includes(params.get('lang')) ? params.get('lang') : 'en';
const stage = document.getElementById('stage');
const frame = document.getElementById('demo');

// --- mise à l'échelle 16:9 de la scène ---------------------------------------------------------------
function fit() {
  const k = Math.min(innerWidth / 1920, innerHeight / 1080);
  stage.style.transform = `scale(${k}) translate(-50%, -50%)`;
}
addEventListener('resize', fit);
fit();

// --- démo ----------------------------------------------------------------------------------------------
function demoUrl() {
  const q = new URLSearchParams();
  q.set('demo', params.get('demo') || '1');
  q.set('lang', lang);
  q.set('tour', params.get('tour') === 'full' ? 'full' : 'pitch'); // par défaut : la démo courte d'une minute
  if (params.get('loop') !== '0') q.set('loop', '1');
  if (params.get('autostart') === '1') q.set('autostart', '1');
  if (params.get('intro')) q.set('intro', params.get('intro')); // ex. ?lang=fr&intro=it : bonjour en italien, puis la démo en français
  q.set('r', String(Date.now())); // jamais de version en cache
  return `../?${q}`;
}
const loadDemo = () => { frame.src = demoUrl(); };

// --- textes ----------------------------------------------------------------------------------------------
function applyTexts() {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = TEXTS[lang][el.dataset.i18n];
  document.getElementById('langname').textContent = lang.toUpperCase();
}

// --- diaporama des photos de l'équipe -----------------------------------------------------------------
const slides = [...document.querySelectorAll('#slides img')];
let current = 0;
function nextSlide() {
  const old = slides[current];
  slides.forEach((s) => s.classList.remove('prev'));
  old.classList.remove('on');
  old.classList.add('prev');
  current = (current + 1) % slides.length;
  const next = slides[current];
  next.style.animation = 'none'; void next.offsetWidth; next.style.animation = ''; // relance le lent zoom
  next.classList.add('on');
  setTimeout(() => old.classList.remove('prev'), 1600);
}

// --- commandes -----------------------------------------------------------------------------------------------
const actions = {
  restart: loadDemo,
  lang() { lang = LANGS[(LANGS.indexOf(lang) + 1) % LANGS.length]; applyTexts(); loadDemo(); },
  full() { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.(); },
};
document.getElementById('tools').addEventListener('click', (e) => actions[e.target.closest('[data-do]')?.dataset.do]?.());
addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const map = { f: 'full', r: 'restart', l: 'lang' };
  if (map[e.key.toLowerCase()]) actions[map[e.key.toLowerCase()]]();
});

if (params.get('qr') === 'local') document.getElementById('qr').src = '../qr/701.svg';
if (params.get('rec') === '1') document.body.classList.add('rec');
applyTexts();

// ?compose=base|0..4 : page « à vide » pour tools/record_demo.py (téléphone et photo en vert, ou une seule photo fixe)
const compose = params.get('compose');
if (compose !== null) {
  document.body.classList.add('compose', 'rec');
  if (params.get('key') === 'm') document.body.classList.add('key-m');
  slides.forEach((s) => s.classList.remove('on'));
  if (compose !== 'base') slides[Number(compose)]?.classList.add('on');
} else {
  setInterval(nextSlide, 5500);
  loadDemo();
}
