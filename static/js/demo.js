// Démo automatique (?demo=x, x = vitesse). Elle ne triche pas : elle « touche » les vrais boutons de l'application
// (mise en évidence puis clic), donc elle montre exactement ce que verrait un utilisateur : voix, couleurs, vibrations.
//
//   api.caption(clé)   affiche le bandeau explicatif (clé i18n « demo.c.* »)
//   api.view()         écran affiché
//   api.advanceBus()   fait avancer le bus simulé d'un cran
//   api.reset()        retour au choix de la ligne, voyage vide
//   api.lang()         langue courante
//   api.defaultLine()  clé de la ligne par défaut (lines.json)

const STOP = Symbol('demo-stop');

export function createDemo({ speed, loop, api }) {
  let stopped = false;

  /** Pause de `ms` (divisée par la vitesse), jamais plus courte que `min` (les animations ont une durée incompressible). */
  const sleep = (ms, min = 0) =>
    new Promise((resolve, reject) =>
      setTimeout(() => (stopped ? reject(STOP) : resolve()), Math.max(ms / speed, min)),
    );

  async function waitFor(selector) {
    for (let i = 0; i < 25; i++) {
      const el = document.querySelector(selector);
      if (el) return el;
      await sleep(200, 120);
    }
    throw new Error(`démo : élément introuvable ${selector}`);
  }

  /** « Toucher » un bouton : on le met en évidence, puis on clique. */
  async function tap(selector, { after = 800, min = 350 } = {}) {
    const el = await waitFor(selector);
    el.scrollIntoView?.({ block: 'nearest' });
    el.classList.add('demo-hl');
    try {
      await sleep(1000, 280);
    } finally {
      el.classList.remove('demo-hl');
    }
    el.click();
    await sleep(after, min);
  }

  const say = async (key, reading = 2200) => {
    api.caption(key);
    await sleep(reading, 500);
  };

  /** Arrêt affiché au centre du carrousel (le défilement doux est plus ou moins lent selon le téléphone). */
  const activeStop = () => Math.max([...document.querySelectorAll('.scard')].findIndex((card) => card.classList.contains('active')), 0);

  async function carouselNext(times) {
    for (let i = 0; i < times; i++) {
      const target = activeStop() + 1;
      await tap('[data-act="car-next"]', { after: 100, min: 100 });
      // on attend que l'arrêt soit vraiment arrivé au centre ; sinon on retouche la flèche (2 essais de plus)
      for (let attempt = 0; attempt < 3 && activeStop() !== target; attempt++) {
        if (attempt > 0) document.querySelector('[data-act="car-next"]')?.click();
        for (let k = 0; k < 20 && activeStop() !== target; k++) await sleep(100, 100);
      }
      await sleep(400, 300);
    }
  }

  async function backToHome() {
    const depth = () => history.state?.depth ?? 0;
    for (let guard = 0; api.view() !== 'home' && depth() > 0 && guard < 6; guard++) {
      const before = depth();
      await tap('[data-act="back"]', { after: 100, min: 100 });
      // le retour du navigateur est asynchrone : on attend qu'il soit fait avant de retoucher (sinon on sortirait de l'appli)
      for (let k = 0; k < 40 && depth() === before; k++) await sleep(100, 100);
      await sleep(300, 250);
    }
  }

  async function tour() {
    api.reset();
    await say('demo.c.line', 3000);
    await tap(`[data-act="line"][data-arg="${api.defaultLine()}"]`, { after: 1400 }); // la ligne par défaut (701)

    // 1. tout parle dès le toucher
    await say('demo.c.hello', 1800);
    await tap('[data-nav*="hello"]', { after: 2000 });
    await backToHome();

    // 2. est-ce le bon bus ? rouge puis vert
    await say('demo.c.check_no', 1500);
    await tap('[data-nav*="check"]', { after: 1300 });
    await tap('.cta', { after: 2600 });
    await backToHome();
    await say('demo.c.check_yes', 1200);
    await tap('[data-nav*="check"]', { after: 1300 });
    await carouselNext(2);
    await tap('.cta', { after: 2600 });
    await backToHome();

    // 3. de l'aide pour descendre (orange), une urgence (rouge)
    await say('demo.c.help', 1800);
    await tap('[data-nav*="help"]');
    await tap('[data-nav*="out"]');
    await tap('[data-nav*="ramp"]', { after: 1300 });
    await carouselNext(2);
    await tap('.cta', { after: 3000 });
    await backToHome();
    await say('demo.c.unwell', 1200);
    await tap('[data-nav*="help"]');
    await tap('[data-nav*="unwell"]', { after: 2600 });
    await backToHome();

    // 4. communiquer avec les personnes autour
    await say('demo.c.repeat', 1500);
    await tap('.bubble');
    await tap('[data-nav*="repeat"]', { after: 2200 });
    await backToHome();

    // 5. mon arrêt : vert, orange (préparez-vous), rouge (descendez) avec vibrations
    await say('demo.c.remind', 1800);
    await tap('[data-nav*="help"]');
    await tap('[data-nav*="out"]');
    await tap('[data-nav*="remind"]', { after: 1300 });
    await carouselNext(1);
    await tap('.cta', { after: 1200 });
    await say('demo.c.calm', 2800);
    api.advanceBus(); // le bus s'arrête à l'arrêt précédent le mien
    await sleep(2200, 700);
    api.caption('demo.c.soon');
    api.advanceBus(); // mon arrêt est le prochain : orange
    await sleep(3600, 1200);
    await tap('#overlay [data-act="alarm-ok"]', { after: 600 });
    api.caption('demo.c.now');
    api.advanceBus(); // le bus est à mon arrêt : rouge
    await sleep(4000, 1400);
    await tap('#overlay [data-act="alarm-ok"]', { after: 1500 });

    // 6. réglages : couleurs puis vibration
    await say('demo.c.settings', 1500);
    await tap('.gear', { after: 1200 });
    await tap('[data-arg="colors"]', { after: 2200 });
    await tap('[data-arg="colors"]', { after: 1200 });
    await tap('[data-arg="vibration"]', { after: 1200 });
    await tap('[data-arg="vibration"]', { after: 1200 });

    // 7. changer de langue
    const original = api.lang();
    const other = original === 'en' ? 'fr' : 'en';
    await say('demo.c.lang', 1500);
    await tap(`.lang[data-arg="${other}"]`, { after: 2400 });
    await tap(`.lang[data-arg="${original}"]`, { after: 1400 });

    // fin
    api.reset();
    await say('demo.c.end', 4000);
  }

  return {
    async start() {
      stopped = false;
      try {
        do {
          await tour();
        } while (loop);
      } catch (error) {
        if (error !== STOP) console.warn(error);
      } finally {
        document.querySelectorAll('.demo-hl').forEach((el) => el.classList.remove('demo-hl'));
      }
    },
    stop() {
      stopped = true;
    },
  };
}
