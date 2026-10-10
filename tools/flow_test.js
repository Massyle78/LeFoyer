// Parcours complet à exécuter dans la console du navigateur sur /?line=8&lang=en&demo=1&speed=0 (écran d'accueil, sans arrêt choisi).
// Vérifie : carrousel, retour, aide, rappel d'arrêt, bande verte/orange/rouge, alarmes, vibrations, réglages, langue.
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const out = [];
  const check = (name, ok, info = '') => out.push(`${ok ? 'OK  ' : 'FAIL'} ${name} ${info}`);
  const view = () => document.getElementById('screen').dataset.view;
  const click = async (selector, ms = 300) => { document.querySelector(selector).click(); await wait(ms); };
  const bg = (el) => getComputedStyle(el).backgroundColor;
  const spoken = [];
  const vib = [];
  const synth = window.speechSynthesis;
  const origSpeak = synth.speak.bind(synth);
  synth.speak = (u) => { spoken.push(u.text); };
  navigator.vibrate = (p) => { vib.push(JSON.stringify(p)); return true; };
  const settings = () => JSON.parse(localStorage.getItem('busbuddy.v2'));
  try {
    await wait(500);
    check('accueil', view() === 'home', view());
    check('pas de bande de couleur sans arrêt choisi', !document.querySelector('.band'));

    // Vérifier la destination du bus : carrousel, réponse verte
    await click('[data-nav*="picker"][data-nav*="check"]');
    const cards = [...document.querySelectorAll('.scard')];
    check('7 arrêts dans le carrousel', cards.length === 7, String(cards.length));
    await click('[data-act="car-next"]', 900);
    check('suivant -> 2e actif', cards[1].classList.contains('active'));
    check('nom prononcé', spoken.some((s) => /Parc/.test(s)), JSON.stringify(spoken));
    await click('[data-act="car-prev"]', 900);
    check('précédent -> 1er actif', cards[0].classList.contains('active'));
    for (let i = 0; i < 6; i++) await click('[data-act="car-next"]', 500);
    vib.length = 0;
    await click('.cta');
    check('réponse "oui" (verte)', view() === 'answer' && !!document.querySelector('.card.tone-ok') && /yes/i.test(document.querySelector('.big').textContent));
    check('vibration "oui"', vib.includes('[70,60,70]'), vib.join(' '));
    await click('[data-act="back"]', 400);
    check('retour -> accueil', view() === 'home', view());

    // Aide > Descendre > Rampe : carte orange
    await click('[data-nav*="help"]', 200);
    await click('[data-nav*="out"]', 200);
    await click('[data-nav*="ramp"]');
    await click('.cta');
    check('carte rampe orange', view() === 'card' && !!document.querySelector('.card.tone-warn'));
    let guard = 0;
    while (view() !== 'home' && guard++ < 6) await click('[data-act="back"]');
    check('retours -> accueil', view() === 'home', view());

    // Mon arrêt (Lac) : vert, orange puis rouge, vibrations
    await click('[data-nav*="help"]', 200);
    await click('[data-nav*="out"]', 200);
    await click('[data-nav*="remind"]');
    for (let i = 0; i < 5; i++) await click('[data-act="car-next"]', 500);
    await click('.cta');
    check('mon arrêt', view() === 'mystop', view());
    const band = () => document.querySelector('.band');
    check('bande verte', band()?.classList.contains('tone-ok') && bg(band()) === 'rgb(19, 128, 63)', band()?.className);
    const seen = [];
    vib.length = 0;
    for (let i = 0; i < 14 && !document.querySelector('#overlay .alarm.now'); i++) {
      const alarm = document.querySelector('#overlay .alarm');
      if (alarm) { seen.push(`${alarm.classList[1]}:${bg(alarm)}`); await click('#overlay [data-act="alarm-ok"]', 100); }
      await click('[data-act="demo-next"]', 250);
    }
    const now = document.querySelector('#overlay .alarm.now');
    if (now) seen.push(`now:${bg(now)}`);
    check('alarme orange puis rouge', seen.join(' ') === 'approaching:rgb(245, 162, 27) now:rgb(200, 16, 46)', seen.join(' '));
    check('vibrations orange et rouge', vib.includes('[250,150,250]') && vib.includes('[600,200,600,200,600,200,1000]'), vib.join(' '));
    await click('#overlay [data-act="alarm-ok"]', 200);
    check('bande rouge', band()?.classList.contains('tone-stop'), band()?.textContent.trim());

    // Réglages
    await click('.gear');
    check('réglages', view() === 'settings', view());
    vib.length = 0;
    await click('[data-arg="vibration"]', 200);
    check('vibration coupée : silence et mémorisée', settings().vibration === false && vib.length === 0, vib.join(' '));
    await click('[data-arg="vibration"]', 200);
    check('vibration remise : petit essai', settings().vibration === true && vib.includes('[70,60,70]'), vib.join(' '));
    await click('[data-arg="colors"]', 200);
    check('couleurs coupées : tout violet', document.documentElement.classList.contains('no-colors') && settings().colors === false);
    await click('[data-arg="colors"]', 200);
    check('couleurs remises', !document.documentElement.classList.contains('no-colors') && settings().colors === true);

    // Langue
    await click('.lang[data-arg="fr"]');
    check('français', /Réglages/.test(document.getElementById('screen').textContent), document.documentElement.lang);
  } catch (e) {
    out.push(`EXC ${e.message}`);
  }
  synth.speak = origSpeak;
  return out.join('\n');
})();
