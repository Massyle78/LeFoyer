// Bus Buddy (web app) — tout se passe sur le téléphone : aucune communication avec le conducteur.
import { a11y, register, speechService, vibrationService, wakeLockService } from './a11y.js';
import { createDemo } from './demo.js';
import { goesTo, alarmPhase, lineFromQr } from './logic.js';
import { languageName, loadLanguages, makeT, speechLang } from './i18n.js';
import { SimulatedPosition } from './position.js';
import { LANGS, demo, demoAutostart, demoLoop, demoSpeed, manual, params, save, speedSeconds, store } from './store.js';
import { alarmHtml, demoCaptionHtml, demoStartHtml, renderView, statusBandHtml } from './views.js';

const screen = document.getElementById('screen');
const overlay = document.getElementById('overlay');
const captionBar = document.getElementById('democap');

let allLines = [];
let line = null;
let position = null;
const shownAlarms = new Set();

// --- contexte donné aux vues ---------------------------------------------------------------------
function context() {
  const t = makeT(store.lang);
  const stops = line?.stops ?? [];
  const destIndex = stops.findIndex((s) => s.id === store.dest);
  return {
    t,
    lang: store.lang,
    allLines,
    line,
    stops,
    count: stops.length,
    pos: position ? position.state : { next: 0, atStop: false },
    destIndex: destIndex >= 0 ? destIndex : null,
    voice: store.voice,
    colors: store.colors,
    vibration: store.vibration,
    canVibrate: vibrationService.available,
    canScan: canScanQr(),
    manual,
    demoCaption: demoCaptionKey ? t(demoCaptionKey) : '',
    languages: LANGS.map((code) => ({ code, name: languageName(code) })),
  };
}

const say = (text, lang = store.lang) => a11y.speak(text, speechLang(lang));

// --- navigation (l'historique du navigateur = le bouton « retour » du téléphone) ---------------
const current = () => history.state ?? { view: line ? 'home' : 'lines', params: {}, depth: 0 };

function go(view, params = {}, { replace = false } = {}) {
  const depth = replace ? current().depth : current().depth + 1;
  const state = { view, params, depth };
  if (replace) history.replaceState(state, '', `#/${view}`);
  else history.pushState(state, '', `#/${view}`);
  draw();
}

function back() {
  if (current().depth > 0) history.back();
}

window.addEventListener('popstate', draw);

// --- affichage ---------------------------------------------------------------------------------------
function draw() {
  const state = current();
  const { params } = state;
  // Sans bus choisi, seul le choix de la ligne (et les réglages) a un sens, même si l'historique propose autre chose.
  const view = !line && !['lines', 'settings'].includes(state.view) ? 'lines' : state.view;
  const c = context();
  document.documentElement.lang = store.lang;
  document.documentElement.classList.toggle('no-colors', !store.colors); // réglage « Couleurs »
  const keepScroll = screen.dataset.view === view ? screen.querySelector('main')?.scrollTop : 0;
  screen.innerHTML = renderView(view, params, c);
  screen.dataset.view = view;
  const main = screen.querySelector('main');
  if (main && keepScroll) main.scrollTop = keepScroll;
  if (view === 'picker') initCarousel(c);
  if (view === 'scan') startScanner();
  else stopScanner();
  refreshCaption();
}

// --- choix du bus par QR code : scanner intégré (Chrome Android...) ; sinon l'appareil photo du téléphone ouvre l'adresse du QR ---
const canScanQr = () => window.isSecureContext && 'BarcodeDetector' in window && !!navigator.mediaDevices?.getUserMedia;
let scanStream = null;
let scanTimer = null;

function stopScanner() {
  clearInterval(scanTimer);
  scanTimer = null;
  scanStream?.getTracks().forEach((track) => track.stop());
  scanStream = null;
}

async function startScanner() {
  stopScanner();
  const video = screen.querySelector('#scanvideo');
  const message = screen.querySelector('#scanmsg');
  const t = makeT(store.lang);
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    if (screen.dataset.view !== 'scan') return stream.getTracks().forEach((track) => track.stop()); // parti entre-temps
    scanStream = stream;
    video.srcObject = stream;
    await video.play();
    const detector = new BarcodeDetector({ formats: ['qr_code'] });
    scanTimer = setInterval(async () => {
      try {
        const codes = await detector.detect(video);
        if (!codes.length) return;
        const number = lineFromQr(codes[0].rawValue, allLines.map((l) => l.number));
        if (number) {
          a11y.feedback('confirm');
          actions.line(number);
        } else {
          message.textContent = t('scan.unknown');
        }
      } catch {
        /* image pas prête : on réessaie */
      }
    }, 300);
  } catch {
    message.textContent = t('scan.denied');
  }
}

// --- démo automatique (?demo=x) -----------------------------------------------------------------------
let demoRun = null;
let demoCaptionKey = null;

function refreshCaption() {
  captionBar.hidden = !demoRun;
  if (demoRun) captionBar.innerHTML = demoCaptionHtml(context());
}

const demoApi = {
  caption(key) {
    demoCaptionKey = key;
    refreshCaption();
  },
  view: () => screen.dataset.view,
  advanceBus: () => position?.advance(),
  lang: () => store.lang,
  reset: () => leaveLine(),
};

function startDemo() {
  overlay.innerHTML = '';
  demoRun = createDemo({ speed: demoSpeed, loop: demoLoop, api: demoApi });
  refreshCaption();
  demoRun.start();
}

function stopDemo() {
  demoRun?.stop();
  demoRun = null;
  demoCaptionKey = null;
  refreshCaption();
}

// --- changer de bus : retour au choix de la ligne -------------------------------------------------------
function leaveLine() {
  stopAlarmFeedback();
  overlay.innerHTML = '';
  position?.stop();
  position = null;
  line = null;
  store.line = null;
  store.dest = null;
  save();
  const url = new URL(location.href);
  url.searchParams.delete('line');
  url.hash = '#/lines';
  history.replaceState({ view: 'lines', params: {}, depth: 0 }, '', url);
  draw();
}

// --- carrousel d'arrêts : un arrêt à la fois, les voisins en transparence ---------------------------
function initCarousel(c) {
  const track = screen.querySelector('.track');
  const cards = [...track.children];
  let active = 0;
  const mark = (i) => cards.forEach((card, k) => card.classList.toggle('active', k === i));
  const scrollTo = (i, behavior = 'smooth') => {
    const card = cards[i];
    track.scrollTo({ left: card.offsetLeft + card.offsetWidth / 2 - track.clientWidth / 2, behavior });
  };
  const nearest = () => {
    const mid = track.scrollLeft + track.clientWidth / 2;
    let best = 0;
    let dist = Infinity;
    cards.forEach((card, i) => {
      const d = Math.abs(card.offsetLeft + card.offsetWidth / 2 - mid);
      if (d < dist) [dist, best] = [d, i];
    });
    return best;
  };
  let timer = null;
  track.addEventListener('scroll', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const i = nearest();
      if (i === active) return;
      active = i;
      track.dataset.active = String(i);
      mark(i);
      say(cards[i].querySelector('.spill').textContent); // il dit le nom de l'arrêt dès qu'il est au centre
    }, 110);
  });
  track.addEventListener('click', (event) => {
    const card = event.target.closest('.scard');
    if (!card) return;
    const i = cards.indexOf(card);
    if (i === active) pick(track.closest('.car').dataset.need);
    else scrollTo(i);
  });
  screen.querySelector('[data-act="car-prev"]').addEventListener('click', () => active > 0 && scrollTo(active - 1));
  screen.querySelector('[data-act="car-next"]').addEventListener('click', () => active < cards.length - 1 && scrollTo(active + 1));
  requestAnimationFrame(() => scrollTo(0, 'instant'));
  // Dire le premier arrêt pour que l'utilisateur sache où il se trouve.
  say(cards[0].querySelector('.spill').textContent);
}

// --- choix d'un arrêt -----------------------------------------------------------------------------------
function pick(need) {
  const track = screen.querySelector('.track');
  const card = track.children[Number(track.dataset.active)];
  const stop = line.stops.find((s) => s.id === card.dataset.stop);
  const t = makeT(store.lang);
  const stopIndex = line.stops.indexOf(stop);
  if (need === 'check') {
    const yes = goesTo({ count: line.stops.length, ...position.state }, stopIndex);
    say(t(yes ? 'answer.yes' : 'answer.no', { stop: stop.name }));
    a11y.feedback(yes ? 'yes' : 'no');
    return go('answer', { stop: stop.id, yes }, { replace: true });
  }
  setDestination(stop.id);
  a11y.feedback('confirm');
  if (need === 'remind') {
    say(`${t('mystop.title')}: ${stop.name}`);
    return go('mystop', {}, { replace: true });
  }
  const icons = { ramp: 'ramp', front_door: 'front_door', more_time: 'more_time', ticket: 'ticket_buy' };
  say(t(`phrase.${need}`, { stop: stop.name }));
  return go('card', { phrase: need, icon: icons[need], stop: stop.id }, { replace: true });
}

function setDestination(stopId) {
  store.dest = stopId;
  shownAlarms.clear();
  stopAlarmFeedback();
  save();
}

// --- alarme « mon arrêt approche » ----------------------------------------------------------------
function onPosition(state) {
  const destIndex = line.stops.findIndex((s) => s.id === store.dest);
  const phase = alarmPhase({ ...state, dest: destIndex >= 0 ? destIndex : null });
  if (phase === 'passed') {
    store.dest = null;
    save();
  } else if (phase && !shownAlarms.has(phase)) {
    shownAlarms.add(phase);
    const c = context();
    const stopName = line.stops[destIndex].name;
    overlay.innerHTML = alarmHtml(c, phase, stopName);
    say(`${c.t(`alarm.${phase}.title`)} ${c.t(`alarm.${phase}.sub`, { stop: stopName })}`);
    startAlarmFeedback(phase);
  } else if (state.atStop && phase !== 'passed' && destIndex >= 0) {
    a11y.feedback('stopped'); // le bus vient de s'arrêter à un arrêt (pas le mien)
  }
  if (['home', 'mystop'].includes(current().view)) draw(); // mise à jour calme, sans animation
  else refreshBand(); // les autres écrans gardent leur état (ex. carrousel) : on ne met à jour que la bande de couleur
}

// Orange : une série de vibrations. Rouge : « C'est mon arrêt » vibre fort et recommence jusqu'à ce qu'on touche OK.
let alarmTimer = null;
function startAlarmFeedback(phase) {
  stopAlarmFeedback();
  const kind = phase === 'now' ? 'arrive' : 'soon';
  a11y.feedback(kind);
  if (phase === 'now') alarmTimer = setInterval(() => a11y.feedback(kind), 6000);
}
function stopAlarmFeedback() {
  clearInterval(alarmTimer);
  alarmTimer = null;
}

function refreshBand() {
  const html = statusBandHtml(context());
  const old = screen.querySelector('.band');
  if (old) old.outerHTML = html;
  else if (html) screen.querySelector('header')?.insertAdjacentHTML('afterend', html);
}

// --- actions ----------------------------------------------------------------------------------------------
const actions = {
  back,
  noop() {},
  /** Interrupteurs de l'écran Réglages (et haut-parleur du bandeau) : voice | colors | vibration. */
  toggle(name) {
    if (!['voice', 'colors', 'vibration'].includes(name)) return;
    store[name] = !store[name];
    save();
    draw();
    const t = makeT(store.lang);
    const state = t(store[name] ? 'settings.on' : 'settings.off');
    if (name === 'voice' && !store.voice) a11y.stop();
    else say(`${t(`settings.${name}`)} : ${state}`);
    if (name === 'vibration') a11y.feedback('confirm'); // on le sent tout de suite
  },
  lang(code) {
    store.lang = code;
    save();
    draw();
    say(languageName(code), code); // il dit le nom de la langue, dans cette langue
  },
  line(number) {
    stopScanner();
    chooseLine(number);
    // L'adresse garde le bus choisi (?line=8) : recharger la page reprend le trajet, comme le QR code du bus.
    const url = new URL(location.href);
    url.searchParams.set('line', number);
    url.hash = '#/home';
    history.replaceState({ view: 'home', params: {}, depth: 0 }, '', url);
    draw();
  },
  'change-line': leaveLine,
  'demo-start': startDemo,
  'demo-stop': stopDemo,
  pick,
  'alarm-ok'() {
    overlay.innerHTML = '';
    stopAlarmFeedback();
    a11y.stop();
    navigator.vibrate?.(0); // coupe la vibration en cours
  },
  'demo-next'() {
    position?.advance();
  },
};

document.getElementById('app').addEventListener('click', (event) => {
  const el = event.target.closest('[data-say],[data-nav],[data-act]');
  if (!el || el.closest('.track')) return; // le carrousel gère ses propres touches
  if (el.dataset.say) say(el.dataset.say); // « parle dès le toucher »
  if (!el.dataset.nav && !el.dataset.act) return;
  if (el.dataset.act !== 'toggle') a11y.feedback('tap'); // les interrupteurs font leur propre retour
  if (el.dataset.nav) {
    const { view, params } = JSON.parse(el.dataset.nav);
    go(view, params);
  } else {
    actions[el.dataset.act]?.(el.dataset.arg);
  }
});

// --- démarrage -----------------------------------------------------------------------------------------
function chooseLine(number) {
  line = allLines.find((l) => l.number === number) ?? null;
  if (line) {
    if (store.line !== number) store.dest = null;
    store.line = number;
    position = new SimulatedPosition(line.stops.length, onPosition);
    position.start(speedSeconds * 1000);
    shownAlarms.clear();
    save();
  }
}

async function start() {
  await loadLanguages();
  allLines = (await (await fetch('static/data/lines.json')).json()).lines;
  register(speechService);
  register(vibrationService);
  register(wakeLockService);
  speechService.init();
  wakeLockService.init();
  // Page d'accueil = choix du bus. Un QR code (…/?line=8) y répond d'avance et ouvre directement le bus ;
  // sans QR code, on choisit la ligne dans la liste (ou avec le scanner intégré).
  chooseLine(params.get('line'));
  if (!line) {
    store.line = null;
    store.dest = null;
  }
  if (!history.state) history.replaceState({ view: line ? 'home' : 'lines', params: {}, depth: 0 }, '', `#/${line ? 'home' : 'lines'}`);
  // Aperçu / captures d'écran : ?view=picker&p={"need":"ramp"} ouvre directement un écran.
  if (line && params.get('dest') && line.stops.some((s) => s.id === params.get('dest'))) setDestination(params.get('dest'));
  const previewView = params.get('view');
  if (previewView && line) {
    history.replaceState({ view: previewView, params: JSON.parse(params.get('p') || '{}'), depth: 1 }, '', `#/${previewView}`);
  }
  draw();

  // Démo automatique (?demo=2) : un écran de départ (un toucher autorise la voix et la vibration), ou &autostart=1.
  if (demo) {
    if (demoAutostart) startDemo();
    else overlay.innerHTML = demoStartHtml(context(), demoSpeed);
  }
  // Démo à la main (?manual=1) : bandeau « arrêt suivant » + touche N pour faire avancer le bus ; ?speed=20 pour l'avance automatique.
  window.addEventListener('keydown', (e) => e.key === 'n' && position?.advance());

  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
}

start();
