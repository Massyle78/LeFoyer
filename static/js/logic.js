// Logique pure (sans DOM) : testable avec `node --test tests/`.

/**
 * Arrêts à afficher sur la frise. Pour une longue ligne on ne montre que quelques arrêts et
 * trois points « ··· » (avec le nombre d'arrêts cachés) :
 *   [prochain] [suivant] ··· [mon arrêt / terminus]
 * @param {{count:number,next:number,atStop:boolean,dest:(number|null),maxNodes?:number}} p
 */
export function stopStrip({ count, next, atStop, dest = null, maxNodes = 4 }) {
  const last = count - 1;
  const hasDest = dest !== null && dest >= next && dest <= last;
  const target = hasDest ? dest : last;
  const node = (index) => ({
    type: 'stop',
    index,
    isNext: index === next,
    atStop: index === next && atStop,
    isTarget: hasDest && index === target,
    isTerminus: index === last,
  });
  const span = target - next + 1;
  const items = [];
  if (span <= maxNodes) {
    for (let i = next; i <= target; i++) items.push(node(i));
  } else {
    items.push(node(next), node(next + 1));
    items.push({ type: 'gap', hidden: span - 3 });
    items.push(node(target));
  }
  return items;
}

/** Nombre d'arrêts avant mon arrêt (0 = j'y suis, 1 = c'est le prochain). null si pas d'arrêt choisi. */
export function stopsLeft({ next, atStop, dest }) {
  if (dest === null || dest === undefined || dest < next) return null;
  return dest - next + (atStop ? 0 : 1);
}

/** Phase de l'alarme : 'approaching' (mon arrêt est le prochain), 'now' (le bus y est), 'passed', ou null. */
export function alarmPhase({ next, atStop, dest }) {
  if (dest === null || dest === undefined) return null;
  if (next > dest) return 'passed';
  if (next === dest) return atStop ? 'now' : 'approaching';
  return null;
}

/**
 * « Où en suis-je ? » en trois moments, pour les couleurs :
 *   'calm' (vert : tout va bien, j'attends) · 'soon' (orange : mon arrêt est le prochain, je me prépare) ·
 *   'now' (rouge : j'y suis, je descends). null : pas d'arrêt choisi, ou arrêt déjà dépassé.
 */
export function tripStatus({ next, atStop, dest }) {
  const phase = alarmPhase({ next, atStop, dest });
  if (phase === 'now') return 'now';
  if (phase === 'approaching') return 'soon';
  if (phase === null && dest !== null && dest !== undefined) return 'calm';
  return null;
}

/** Index des arrêts encore devant le bus (ceux qu'on peut demander / où l'on peut descendre). */
export function aheadIndexes({ count, next, atStop }) {
  const out = [];
  for (let i = atStop ? next + 1 : next; i < count; i++) out.push(i);
  return out;
}

/** « Est-ce le bon bus ? » : oui si l'arrêt est encore devant le bus. */
export function goesTo({ count, next, atStop }, stopIndex) {
  return aheadIndexes({ count, next, atStop }).includes(stopIndex);
}

/**
 * ?demo=x : x = vitesse de la d�mo automatique. Absent / 0 / false = pas de d�mo ; 1 = vitesse normale ;
 * 2 = deux fois plus vite... (born� entre 0,5 et 8). Une valeur non num�rique (ex. demo=true) vaut 1.
 */
export function parseDemo(raw) {
  if (raw === null || raw === undefined) return 0;
  const text = String(raw).trim().toLowerCase();
  if (text === '' || text === '0' || text === 'false' || text === 'off') return 0;
  const n = Number(text.replace(',', '.'));
  if (!Number.isFinite(n)) return 1;
  return n <= 0 ? 0 : Math.min(8, Math.max(0.5, n));
}

/** Num�ro de ligne contenu dans un QR code : une adresse � �/?line=8 � ou simplement � 8 �. null si inconnu. */
export function lineFromQr(raw, knownNumbers) {
  const text = String(raw ?? '').trim();
  let candidate = text;
  try {
    candidate = new URL(text).searchParams.get('line') ?? '';
  } catch {
    /* pas une adresse : on essaie le texte brut */
  }
  return knownNumbers.includes(candidate) ? candidate : null;
}
