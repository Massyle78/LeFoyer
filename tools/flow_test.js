// Test de parcours à coller dans la console du navigateur (ou via CDP) : renvoie la liste des vérifications.
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const out = [];
  const check = (name, ok, info = '') => out.push(`${ok ? 'OK  ' : 'FAIL'} ${name} ${info}`);
  const view = () => document.getElementById('screen').dataset.view;
  const spoken = [];
  const synth = window.speechSynthesis;
  const origSpeak = synth.speak.bind(synth);
  synth.speak = (u) => { spoken.push(u.text); };

  await wait(500);
  check('accueil', view() === 'home', view());
  document.querySelector('[data-nav*="picker"][data-nav*="check"]').click();
  await wait(300);
  check('sélecteur ouvert', view() === 'picker', view());
  const cards = [...document.querySelectorAll('.scard')];
  check('7 arrêts dans le carrousel', cards.length === 7, String(cards.length));
  check('premier arrêt actif', cards[0].classList.contains('active'));
  document.querySelector('[data-act="car-next"]').click();
  await wait(900);
  check('suivant -> 2e actif', cards[1].classList.contains('active'), cards.map((c) => c.classList.contains('active') ? 1 : 0).join(''));
  check('nom prononcé', spoken.some((s) => /Park|Parc/.test(s)), JSON.stringify(spoken));
  document.querySelector('[data-act="car-prev"]').click();
  await wait(900);
  check('précédent -> 1er actif', cards[0].classList.contains('active'));
  // aller au dernier arrêt (Jardin Botanique) puis choisir
  for (let i = 0; i < 6; i++) { document.querySelector('[data-act="car-next"]').click(); await wait(500); }
  check('dernier actif', cards[6].classList.contains('active'));
  document.querySelector('.cta').click();
  await wait(300);
  check('réponse affichée', view() === 'answer', view());
  check('réponse "oui" pour le terminus', /Yes|yes/.test(document.querySelector('.big').textContent), document.querySelector('.big').textContent);
  document.querySelector('[data-act="back"]').click();
  await wait(400);
  check('retour -> accueil (la réponse remplaçait le sélecteur)', view() === 'home', view());

  // Aide > Descendre > Rampe
  document.querySelector('[data-nav*="help"]').click(); await wait(200);
  check('aide', view() === 'help', view());
  document.querySelector('[data-nav*="out"]').click(); await wait(200);
  check('descendre', view() === 'out', view());
  document.querySelector('[data-nav*="ramp"]').click(); await wait(300);
  check('sélecteur rampe', view() === 'picker');
  document.querySelector('.cta').click(); await wait(300);
  check('carte rampe', view() === 'card', view());
  check('phrase rampe', /ramp/i.test(document.querySelector('.big').textContent), document.querySelector('.big').textContent);

  // retours successifs jusqu'à l'accueil
  let guard = 0;
  while (view() !== 'home' && guard++ < 6) { document.querySelector('[data-act="back"]').click(); await wait(300); }
  check('retours -> accueil', view() === 'home', view());

  // Rappel de mon arrêt
  document.querySelector('[data-nav*="help"]').click(); await wait(200);
  document.querySelector('[data-nav*="out"]').click(); await wait(200);
  document.querySelector('[data-nav*="remind"]').click(); await wait(300);
  for (let i = 0; i < 5; i++) { document.querySelector('[data-act="car-next"]').click(); await wait(500); }
  document.querySelector('.cta').click(); await wait(300);
  check('mon arrêt', view() === 'mystop', view());
  const text = () => document.querySelector('.left').textContent;
  check('arrêts restants', /\d/.test(text()), text());
  // Alarme : avancer le bus jusqu'à l'arrêt visé (lac = index 5)
  const log = [];
  for (let i = 0; i < 8; i++) {
    document.querySelector('[data-act="demo-next"]').click(); await wait(250);
    const a = document.querySelector('#overlay .alarm');
    log.push(a ? a.className : '-');
  }
  check('alarme apparaît', log.some((x) => x !== '-'), log.join(' | '));
  document.getElementById('overlay').querySelector('[data-act="alarm-ok"]')?.click();
  // Langue
  document.querySelector('.lang[data-arg="fr"]').click(); await wait(300);
  check('passage en français', /Bienvenue|Aide|Mon arrêt|Parler/.test(document.getElementById('screen').textContent), document.documentElement.lang);
  synth.speak = origSpeak;
  return out.join('\n');
})();
