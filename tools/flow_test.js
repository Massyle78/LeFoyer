// Parcours complet à exécuter dans la console du navigateur sur /?lang=en&manual=1 (après localStorage.clear()) :
// la page d'accueil est le choix de la ligne ; ?manual=1 ajoute le bandeau « arrêt suivant » pour avancer le bus à la main.
// (La démo automatique, elle, se lance avec ?demo=x.)
// Vérifie : choix de la ligne, changement de bus, carrousel, retour, aide, rappel d'arrêt, bande verte/orange/rouge, alarmes, vibrations, réglages, langue.
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const out = [];
  const check = (name, ok, info = '') => out.push(`${ok ? 'OK  ' : 'FAIL'} ${name} ${info}`);
  const view = () => document.getElementById('screen').dataset.view;
  const click = async (selector, ms = 300) => { document.querySelector(selector).click(); await wait(ms); };
  const bg = (el) => getComputedStyle(el).backgroundColor;
  const activeCard = () => [...document.querySelectorAll('.scard')].findIndex((c) => c.classList.contains('active'));
  // le défilement doux du carrousel est plus ou moins lent selon le navigateur : on attend que l'arrêt actif change vraiment
  const carousel = async (selector, delta) => {
    const target = Math.max(activeCard(), 0) + delta; // aucun repère « actif » tant que le carrousel n'a pas défilé : on part du 1er arrêt
    document.querySelector(selector).click();
    for (let i = 0; i < 40 && activeCard() !== target; i++) await wait(100);
    await wait(150);
  };
  const spoken = [];
  const vib = [];
  const synth = window.speechSynthesis;
  const origSpeak = synth.speak.bind(synth);
  synth.speak = (u) => { spoken.push(u.text); };
  navigator.vibrate = (p) => { vib.push(JSON.stringify(p)); return true; };
  const settings = () => JSON.parse(localStorage.getItem('busbuddy.v2'));
  try {
    await wait(500);
    // Page d'accueil = choix du bus (sans ?line=)
    check('accueil = choix de la ligne', view() === 'lines', view());
    check('liste des lignes', document.querySelectorAll('.row').length >= 2, String(document.querySelectorAll('.row').length));
    check('QR : bouton scanner ou indication', !!document.querySelector('.scanbtn, .qrhint'));
    await click('[data-act="line"][data-arg="8"]', 500);
    check('ligne choisie -> accueil du bus', view() === 'home' && /line=8/.test(location.search), view() + location.search);
    check('pas de bande de couleur sans arrêt choisi', !document.querySelector('.band'));
    check('démo manuelle : bandeau « arrêt suivant »', !!document.querySelector('.demobar'));

    // Vérifier la destination du bus : carrousel, réponse verte
    await click('[data-nav*="picker"][data-nav*="check"]');
    const cards = [...document.querySelectorAll('.scard')];
    check('7 arrêts dans le carrousel', cards.length === 7, String(cards.length));
    await carousel('[data-act="car-next"]', 1);
    check('suivant -> 2e actif', cards[1].classList.contains('active'));
    check('nom prononcé', spoken.some((s) => /Parc/.test(s)), JSON.stringify(spoken));
    await carousel('[data-act="car-prev"]', -1);
    check('précédent -> 1er actif', cards[0].classList.contains('active'));
    for (let i = 0; i < 6; i++) await carousel('[data-act="car-next"]', 1);
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
    for (let i = 0; i < 5; i++) await carousel('[data-act="car-next"]', 1);
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

    // Changer de bus : retour au choix de la ligne
    await click('.busid', 400);
    check('changer de bus -> choix de la ligne', view() === 'lines' && !/line=/.test(location.search) && settings().line === null, view() + location.search);
  } catch (e) {
    out.push(`EXC ${e.message}`);
  }
  synth.speak = origSpeak;
  return out.join('\n');
})();
