// Écrans (HTML en chaîne). Chaque vue reçoit un contexte `c` :
//   { t, lang, line, stops, count, pos:{next,atStop}, destIndex, voice, languages:[{code,name}], demo }
// et renvoie du HTML. La navigation et les actions sont décrites par des attributs data-* :
//   data-say="texte"      dire ce texte dès le toucher
//   data-nav='{"view":..}' aller à un écran
//   data-act="nom"        action (voir main.js)
import { stopStrip, stopsLeft, aheadIndexes } from './logic.js';

const esc = (s) => String(s).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
const json = (o) => esc(JSON.stringify(o));

// Adresse absolue du dossier static/, valable à la racine d'un site comme dans un sous-dossier (GitHub Pages).
const ASSETS = new URL('static/', document.baseURI).href;

export const ico = (name, cls = '') =>
  `<span class="ico ${cls}" style="--i:url(${ASSETS}img/icons/${name}.png)" aria-hidden="true"></span>`;

const photoUrl = (stop) => (stop.photo ? `static/img/stops/${stop.photo}` : null);

// --- composants -------------------------------------------------------------------------------
function tile({ icon, label, say, nav, act, arg }) {
  const data = [
    say !== undefined ? `data-say="${esc(say)}"` : `data-say="${esc(label)}"`,
    nav ? `data-nav='${json(nav)}'` : '',
    act ? `data-act="${act}"` : '',
    arg !== undefined ? `data-arg="${esc(arg)}"` : '',
  ].join(' ');
  return `<button class="tile" type="button" ${data}>
    <span class="tico"><span class="disc">${ico(icon)}</span></span>
    <span class="pill">${esc(label)}</span>
  </button>`;
}

function strip(c, { compact = false } = {}) {
  const items = stopStrip({
    count: c.count,
    next: c.pos.next,
    atStop: c.pos.atStop,
    dest: c.destIndex,
  });
  const parts = items.map((it) => {
    if (it.type === 'gap') {
      return `<li class="gap"><span class="dots"><i></i><i></i><i></i></span><small>${esc(c.t('common.stops', { n: it.hidden }))}</small></li>`;
    }
    const cls = ['node', it.isNext && 'next', it.isTarget && 'target', it.atStop && 'here'].filter(Boolean).join(' ');
    return `<li class="${cls}"><i></i><span>${esc(c.stops[it.index].name)}</span></li>`;
  });
  return `<ol class="strip ${compact ? 'compact' : ''}">${parts.join('')}</ol>`;
}

function brand() {
  return `<div class="brand" aria-hidden="true">
    ${ico('logo', 'logo')}
    <svg viewBox="0 0 200 70" class="brand-text"><defs><path id="bb-arc" d="M8,52 Q100,44 192,12"/></defs>
      <text><textPath href="#bb-arc" startOffset="50%" text-anchor="middle">BUS BUDDY</textPath></text></svg>
  </div>`;
}

function heading(title, sub) {
  return `<div class="head"><div class="htext"><h1>${esc(title)}</h1>${sub ? `<p class="sub">${esc(sub)}</p>` : ''}</div>${brand()}</div>`;
}

function stopImage(stop) {
  const url = photoUrl(stop);
  return url ? `<img src="${url}" alt="" draggable="false">` : `<span class="noimg">${ico('front_door')}</span>`;
}

function header(c) {
  const voice = c.voice ? c.t('common.voice_on') : c.t('common.voice_off');
  const speaker = c.voice
    ? '<path d="M3 9v6h4l5 4V5L7 9H3z" fill="currentColor"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
    : '<path d="M3 9v6h4l5 4V5L7 9H3z" fill="currentColor"/><path d="M16 9l5 6M21 9l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>';
  const left = c.line
    ? `<div class="num">${esc(c.line.number)}</div>
       <div class="dir"><small>${esc(c.t('common.direction'))}</small><strong>${esc(c.stops.at(-1).name)}</strong></div>`
    : `<div class="num small">Bus</div><div class="dir"><strong>Bus Buddy</strong></div>`;
  return `<header class="top">${left}
    <button class="voice" type="button" data-act="voice" aria-label="${esc(voice)}" aria-pressed="${c.voice}">
      <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">${speaker}</svg></button>
  </header>`;
}

function bubble(c) {
  return `<button class="bubble" type="button" data-say="${esc(c.t('comm.title'))}" data-nav='${json({ view: 'comm' })}'
      aria-label="${esc(c.t('home.repeat'))}">
    <svg viewBox="0 0 200 200" aria-hidden="true"><defs><path id="bb-bub" d="M20,122 A84,84 0 0 1 150,34"/></defs>
      <text><textPath href="#bb-bub">${esc(c.t('home.repeat'))}</textPath></text></svg>
    ${ico('repeat', 'bubble-ico')}
  </button>`;
}

function footer(c) {
  const langs = c.languages
    .map((l) => `<button type="button" class="lang ${l.code === c.lang ? 'active' : ''}" data-act="lang" data-arg="${l.code}"
        ${l.code === c.lang ? 'aria-current="true"' : ''} lang="${l.code}">${esc(l.name)}</button>`)
    .join('');
  return `<footer class="foot"><span class="flabel">${esc(c.t('common.language'))}</span><div class="langs">${langs}</div></footer>`;
}

const backButton = (c) => `<button class="back" type="button" data-act="back">
  <svg viewBox="0 0 40 28" width="40" height="28" aria-hidden="true"><path d="M38 14H6M16 3L5 14l11 11" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>
  <span>${esc(c.t('common.back'))}</span></button>`;

/** Page complète : bandeau, contenu, retour, bulle « répétez doucement », choix de langue. */
function page(c, content, { back = true, withBubble = true, cls = '' } = {}) {
  return `${header(c)}<main class="${cls}">${content}</main>${back ? backButton(c) : ''}${withBubble ? bubble(c) : ''}${footer(c)}`;
}

// --- écrans ---------------------------------------------------------------------------------------
function myStopBanner(c) {
  if (c.destIndex === null) return '';
  const stop = c.stops[c.destIndex];
  const left = stopsLeft({ next: c.pos.next, atStop: c.pos.atStop, dest: c.destIndex });
  const leftText = leftLabel(c, left);
  return `<button class="mystop" type="button" data-say="${esc(`${c.t('mystop.title')}: ${stop.name}. ${leftText}`)}"
      data-nav='${json({ view: 'mystop' })}'>
    <span class="mphoto">${stopImage(stop)}</span>
    <span class="mtext"><small>${esc(c.t('mystop.title'))}</small><strong>${esc(stop.name)}</strong><em>${esc(leftText)}</em></span>
    ${strip(c, { compact: true })}
  </button>`;
}

function leftLabel(c, left) {
  if (left === null) return '';
  if (left === 0) return c.t('mystop.here');
  if (left === 1) return c.t('mystop.next_is_mine');
  return c.t('mystop.left.many', { n: left });
}

const views = {
  lines(c) {
    const rows = c.allLines
      .map((l) => `<button class="row" type="button" data-say="${esc(`${l.number}, ${l.stops.at(-1).name}`)}" data-act="line" data-arg="${esc(l.number)}">
          <b>${esc(l.number)}</b><span>${esc(l.stops.at(-1).name)}</span></button>`)
      .join('');
    return page(c, `${heading(c.t('lines.title'), c.t('lines.sub'))}<div class="rows">${rows}</div>
      <p class="hint">${esc(c.t('lines.qr'))}</p>`, { back: false, withBubble: false });
  },

  home(c) {
    const tiles = [
      tile({ icon: 'hello', label: c.t('home.hello'), say: c.t('phrase.hello'), nav: { view: 'card', params: { phrase: 'hello', icon: 'hello' } } }),
      tile({ icon: 'bus_check', label: c.t('home.check'), nav: { view: 'picker', params: { need: 'check' } } }),
      tile({ icon: 'ticket_buy', label: c.t('home.ticket'), nav: { view: 'picker', params: { need: 'ticket' } } }),
      tile({ icon: 'help_hand', label: c.t('home.help'), nav: { view: 'help' } }),
    ].join('');
    return page(c, `${heading(c.t('home.title'), c.t('home.sub'))}${myStopBanner(c)}<div class="grid">${tiles}</div>`, { back: false });
  },

  help(c) {
    const tiles = [
      tile({ icon: 'getting_out', label: c.t('help.out'), nav: { view: 'out' } }),
      tile({ icon: 'controller', label: c.t('help.control'), say: c.t('phrase.control'), nav: { view: 'card', params: { phrase: 'control', icon: 'controller' } } }),
      tile({ icon: 'lost', label: c.t('help.lost'), say: c.t('phrase.lost'), nav: { view: 'card', params: { phrase: 'lost', icon: 'lost' } } }),
      tile({ icon: 'unwell', label: c.t('help.unwell'), say: c.t('phrase.unwell'), nav: { view: 'card', params: { phrase: 'unwell', icon: 'unwell' } } }),
    ].join('');
    return page(c, `${heading(c.t('help.title'), c.t('home.sub'))}<div class="grid">${tiles}</div>`);
  },

  out(c) {
    const tiles = [
      tile({ icon: 'ramp', label: c.t('out.ramp'), nav: { view: 'picker', params: { need: 'ramp' } } }),
      tile({ icon: 'front_door', label: c.t('out.front_door'), nav: { view: 'picker', params: { need: 'front_door' } } }),
      tile({ icon: 'more_time', label: c.t('out.more_time'), nav: { view: 'picker', params: { need: 'more_time' } } }),
      tile({ icon: 'bell', label: c.t('out.remind'), nav: { view: 'picker', params: { need: 'remind' } } }),
    ].join('');
    return page(c, `${heading(c.t('out.title'), c.t('out.sub'))}<div class="grid">${tiles}</div>`);
  },

  comm(c) {
    const tiles = [
      tile({ icon: 'repeat', label: c.t('comm.repeat'), say: c.t('phrase.repeat'), nav: { view: 'card', params: { phrase: 'repeat', icon: 'repeat' } } }),
      tile({ icon: 'seat', label: c.t('comm.seat'), say: c.t('phrase.seat'), nav: { view: 'card', params: { phrase: 'seat', icon: 'seat' } } }),
    ].join('');
    return page(c, `${heading(c.t('comm.title'), c.t('comm.sub'))}<div class="grid">${tiles}</div>`, { withBubble: false });
  },

  /** Choix de l'arrêt : un seul arrêt à la fois, les voisins en transparence. */
  picker(c, { need }) {
    const indexes = need === 'check' ? c.stops.map((_, i) => i) : aheadIndexes({ count: c.count, next: c.pos.next, atStop: c.pos.atStop });
    const start = 0;
    const cards = indexes
      .map((i, k) => `<div class="scard ${k === start ? 'active' : ''}" data-i="${k}" data-stop="${esc(c.stops[i].id)}">
          <div class="simg">${stopImage(c.stops[i])}</div><div class="spill">${esc(c.stops[i].name)}</div></div>`)
      .join('');
    const body = `${heading(c.t(`stop.title.${need}`), c.t('stop.sub'))}
      <div class="car" data-need="${need}">
        <div class="track" data-active="${start}">${cards}</div>
        <button class="nav prev" type="button" data-act="car-prev" aria-label="${esc(c.t('stop.prev'))}">
          <svg viewBox="0 0 24 24" width="26" height="26"><path d="M15 4l-8 8 8 8" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        <button class="nav next" type="button" data-act="car-next" aria-label="${esc(c.t('stop.next'))}">
          <svg viewBox="0 0 24 24" width="26" height="26"><path d="M9 4l8 8-8 8" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      </div>
      <button class="cta" type="button" data-act="pick" data-arg="${need}">${esc(c.t('common.choose'))}</button>`;
    return page(c, body, { cls: 'picker' });
  },

  /** Phrase à montrer / dire aux personnes autour. */
  card(c, { phrase, icon, stop }) {
    const stopObj = stop ? c.stops.find((s) => s.id === stop) : null;
    const sentence = c.t(`phrase.${phrase}`, { stop: stopObj?.name ?? '' });
    const photo = stopObj ? `<div class="cstop"><div class="cphoto">${stopImage(stopObj)}</div><strong>${esc(stopObj.name)}</strong></div>` : '';
    const body = `<section class="card"><div class="cdisc">${ico(icon)}</div>
        <p class="big">${esc(sentence)}</p>${photo}
        <button class="say" type="button" data-say="${esc(sentence)}" data-act="noop">
          <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true"><path d="M3 9v6h4l5 4V5L7 9H3z" fill="currentColor"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          ${esc(c.t('common.say_again'))}</button>
      </section>`;
    return page(c, body, { withBubble: false, cls: 'cardpage' });
  },

  /** « Est-ce le bon bus ? » */
  answer(c, { stop, yes }) {
    const s = c.stops.find((x) => x.id === stop);
    const sentence = c.t(yes ? 'answer.yes' : 'answer.no', { stop: s.name });
    const mark = yes
      ? '<svg viewBox="0 0 100 100" class="mark"><circle cx="50" cy="50" r="46"/><path d="M27 52l16 16 31-34" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg>'
      : '<svg viewBox="0 0 100 100" class="mark no"><circle cx="50" cy="50" r="46"/><path d="M33 33l34 34M67 33L33 67" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round"/></svg>';
    const body = `<section class="card">${mark}<p class="big">${esc(sentence)}</p>
        <div class="cstop"><div class="cphoto">${stopImage(s)}</div><strong>${esc(s.name)}</strong></div>
        <p class="sub">${esc(c.t('answer.sub', { line: c.line.number, terminus: c.stops.at(-1).name }))}</p>
        <button class="say" type="button" data-say="${esc(sentence)}" data-act="noop">${esc(c.t('common.say_again'))}</button>
      </section>`;
    return page(c, body, { withBubble: false, cls: 'cardpage' });
  },

  /** Rappel de mon arrêt : photo, nombre d'arrêts restants, frise avec « ··· ». */
  mystop(c) {
    if (c.destIndex === null) return views.out(c);
    const stop = c.stops[c.destIndex];
    const left = stopsLeft({ next: c.pos.next, atStop: c.pos.atStop, dest: c.destIndex });
    const next = c.stops[c.pos.next];
    const where = c.pos.atStop ? c.t('mystop.at', { stop: next.name }) : c.t('mystop.next', { stop: next.name });
    const body = `${heading(c.t('mystop.title'), where)}
      <section class="bigstop">
        <div class="bphoto">${stopImage(stop)}</div>
        <div class="bpill">${esc(stop.name)}</div>
      </section>
      <p class="left ${left <= 1 ? 'soon' : ''}">${esc(leftLabel(c, left))}</p>
      ${strip(c)}`;
    return page(c, body, { cls: 'mystoppage' });
  },
};

export function renderView(name, params, c) {
  const view = views[name] ?? views.home;
  return view(c, params ?? {});
}

export function alarmHtml(c, phase, stopName) {
  const title = c.t(`alarm.${phase}.title`);
  const sub = c.t(`alarm.${phase}.sub`, { stop: stopName });
  return `<div class="alarm ${phase}" role="alertdialog" aria-live="assertive" aria-label="${esc(title)}">
    <div class="adisc">${ico(phase === 'now' ? 'getting_out' : 'bell')}</div>
    <h2>${esc(title)}</h2><p>${esc(sub)}</p>
    <button class="cta light" type="button" data-act="alarm-ok">${esc(c.t('common.ok'))}</button>
  </div>`;
}
