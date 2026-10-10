// Bus Buddy (web app) — tout se passe sur le téléphone : aucune communication avec le conducteur.
import { a11y, register, speechService, vibrationService, wakeLockService } from './a11y.js';
import { goesTo, alarmPhase } from './logic.js';
import { languageName, loadLanguages, makeT, speechLang } from './i18n.js';
import { SimulatedPosition } from './position.js';
import { LANGS, demo, params, save, speedSeconds, store } from './store.js';
import { alarmHtml, renderView } from './views.js';

const screen = document.getElementById('screen');
const overlay = document.getElementById('overlay');

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
  const { view, params } = current();
  const c = context();
  document.documentElement.lang = store.lang;
  const keepScroll = screen.dataset.view === view ? screen.querySelector('main')?.scrollTop : 0;
  screen.innerHTML = renderView(view, params, c);
  screen.dataset.view = view;
  const main = screen.querySelector('main');
  if (main && keepScroll) main.scrollTop = keepScroll;
  if (view === 'picker') initCarousel(c);
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
    return go('answer', { stop: stop.id, yes }, { replace: true });
  }
  setDestination(stop.id);
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
    a11y.feedback('alarm');
    say(`${c.t(`alarm.${phase}.title`)} ${c.t(`alarm.${phase}.sub`, { stop: stopName })}`);
  }
  if (['home', 'mystop'].includes(current().view)) draw(); // mise à jour calme, sans animation
}

// --- actions ----------------------------------------------------------------------------------------------
const actions = {
  back,
  noop() {},
  voice() {
    store.voice = !store.voice;
    save();
    if (store.voice) say(makeT(store.lang)('common.voice_on'));
    else a11y.stop();
    draw();
  },
  lang(code) {
    store.lang = code;
    save();
    draw();
    say(languageName(code), code); // il dit le nom de la langue, dans cette langue
  },
  line(number) {
    chooseLine(number);
    history.replaceState({ view: 'home', params: {}, depth: 0 }, '', '#/home');
    draw();
  },
  pick,
  'alarm-ok'() {
    overlay.innerHTML = '';
    a11y.stop();
  },
  'demo-next'() {
    position.advance();
  },
};

document.getElementById('app').addEventListener('click', (event) => {
  const el = event.target.closest('[data-say],[data-nav],[data-act]');
  if (!el || el.closest('.track')) return; // le carrousel gère ses propres touches
  if (el.dataset.say) say(el.dataset.say); // « parle dès le toucher »
  if (!el.dataset.nav && !el.dataset.act) return;
  a11y.feedback('tap');
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
  chooseLine(store.line);
  if (!line) store.line = null;
  if (!history.state) history.replaceState({ view: line ? 'home' : 'lines', params: {}, depth: 0 }, '', `#/${line ? 'home' : 'lines'}`);
  // Aperçu / captures d'écran : ?view=picker&p={"need":"ramp"} ouvre directement un écran.
  if (line && params.get('dest') && line.stops.some((s) => s.id === params.get('dest'))) setDestination(params.get('dest'));
  const previewView = params.get('view');
  if (previewView && line) {
    history.replaceState({ view: previewView, params: JSON.parse(params.get('p') || '{}'), depth: 1 }, '', `#/${previewView}`);
  }
  draw();

  // Pour la démo : bouton + touche N pour faire avancer le bus ; ?speed=20 pour l'avance automatique.
  if (demo) {
    const button = document.createElement('button');
    button.className = 'demo';
    button.dataset.act = 'demo-next';
    button.textContent = `▶ ${makeT(store.lang)('demo.next')}`;
    document.getElementById('app').append(button);
  }
  window.addEventListener('keydown', (e) => e.key === 'n' && position?.advance());

  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
}

start();
