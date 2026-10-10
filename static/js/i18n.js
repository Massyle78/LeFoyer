// Traductions : un fichier JSON plat par langue dans static/i18n/.
// Ajouter une langue = déposer static/i18n/xx.json (+ l'ajouter à LANGS dans store.js).
// Clés manquantes -> anglais.
import { LANGS } from './store.js';

const tables = {};

export async function loadLanguages() {
  await Promise.all(
    LANGS.map(async (code) => {
      const res = await fetch(`static/i18n/${code}.json`);
      tables[code] = await res.json();
    }),
  );
}

export const languageName = (code) => tables[code]?._name ?? code;
export const speechLang = (code) => tables[code]?._speech ?? code;

export function makeT(lang) {
  return (key, vars = {}) => {
    let text = tables[lang]?.[key] ?? tables.en?.[key] ?? key;
    for (const [name, value] of Object.entries(vars)) text = text.replaceAll(`{${name}}`, value);
    return text;
  };
}
