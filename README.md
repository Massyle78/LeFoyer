# Bus Buddy — web app

Application web (PWA) pour aider une personne en situation de handicap à faire un trajet en bus de façon autonome.
Tout se passe **sur le téléphone** : aucune communication avec le conducteur, rien n'est envoyé au serveur.
Charte graphique : violet #1D05A9, violet clair #9C7EC3, rose #FEDADA.

## Lancer

```
pip install -r requirements.txt
python app.py                 # http://localhost:5000
```

- `http://localhost:5000/` : la **page d'accueil est le choix du bus** (scanner le QR code du bus, ou choisir sa ligne dans la liste).
- `http://localhost:5000/?demo=2` : **démo automatique** (voir ci-dessous).
- `http://localhost:5000/?manual=1` : démo à la main (bandeau « arrêt suivant » sous l'en-tête, ou touche **N**, pour faire avancer le bus).
- `http://localhost:5000/qr` : un **QR code par ligne** (à imprimer et coller dans les bus). Le QR ouvre `/?line=8`.
  Pour qu'un téléphone puisse les scanner, il doit être sur le même Wi-Fi ; l'adresse de l'ordinateur sur le réseau est détectée
  automatiquement. En production : `BUSBUDDY_PUBLIC_URL=https://mon-site.org python app.py`.
- Paramètres d'adresse : `?line=8` (ouvre directement ce bus, c'est le QR code) · `?lang=fr|en|de|it` · `?demo=x` · `&autostart=1` · `&loop=1` ·
  `?manual=1` · `?speed=20` (le bus avance tout seul toutes les 20 s).
- `/preview?q=lang%3Dfr%26line%3D8&q=...&scale=0.66` : plusieurs écrans côte à côte en taille téléphone (outil de développement ;
  `?view=help`, `?view=picker&p={"need":"ramp"}`, `&dest=lac` ouvrent directement un écran).

## Démo automatique : `?demo=x`

`x` est la **vitesse** : `?demo=1` normale (environ 3 min), `?demo=2` deux fois plus vite, `?demo=4` en moins d'une minute (de 0,5 à 8).
Un écran de départ demande un toucher (nécessaire pour que le navigateur autorise la voix et la vibration), puis l'application
« touche » elle-même les vrais boutons, avec une mise en évidence jaune et un bandeau noir qui explique ce qui est montré :
choix de la ligne · tout parle dès le toucher · bon / mauvais bus (vert / rouge) · aide pour descendre (orange) et urgence (rouge) ·
« répétez doucement » · rappel de mon arrêt avec alarmes orange puis rouge et vibrations · réglages · changement de langue.
La croix du bandeau l'arrête à tout moment.

- `&autostart=1` : démarre sans l'écran de départ (voix et vibration peuvent alors être bloquées par le navigateur) ;
- `&loop=1` : rejoue la démo en boucle (stand, salon…) ;
- exemple : `/?demo=2&lang=fr&loop=1`.

## Parcours

1. **Page d'accueil = choix du bus** : scan du QR du bus (appareil photo du téléphone : le QR ouvre `/?line=8` et l'app s'ouvre
   directement sur la ligne ; ou bouton **Scanner le QR code** intégré quand le navigateur sait lire les QR codes, en HTTPS ou sur
   `localhost`), ou choix de la ligne dans la liste. Le numéro de ligne en haut (ou Réglages › Changer de bus) ramène à ce choix.
2. Accueil : **Dire bonjour**, **Vérifier la destination du bus**, **Acheter un billet**, **Aide**.
3. Un toucher sur une tuile **le dit à voix haute** puis ouvre la catégorie. Les choix d'arrêts se font dans un carrousel
   horizontal (un arrêt à la fois, voisins en transparence ; le nom est dit quand il arrive au centre).
4. Aide : *Descendre* (rampe, porte avant, plus de temps, **me rappeler mon arrêt**), *Montrer mon billet aux contrôleurs*, *Je suis perdu(e)*, *Je ne me sens pas bien*.
   Ces demandes s'affichent en grand et se disent à voix haute **pour les personnes autour**.
5. Bulle « Répétez doucement » (en bas à droite) : *Répétez doucement* / *Une place assise*.
6. **Mon arrêt** : photo, nombre d'arrêts restants, frise avec « ··· » (au plus 4 repères affichés) ; alarme plein écran
   (« Préparez-vous » puis « C'est votre arrêt ») avec voix, vibration et écran maintenu allumé.
7. Bouton **retour** partout (et le retour du téléphone fonctionne aussi). En bas : **⚙ Réglages** puis les langues (english · français · deutsch · italiano).

## Couleurs et vibrations

Trois moments, toujours doublés d'une icône et d'un texte (la couleur n'est jamais la seule information) :

| Couleur | Sens | Exemples |
|---|---|---|
| **Vert** | tout va bien, j'attends | bande « Tout va bien. Patientez. » · « oui, ce bus va à… » · phrases polies (bonjour, billet, place assise…) |
| **Orange** | je me prépare / j'ai besoin d'aide | « Préparez-vous » (mon arrêt est le prochain) · rampe, porte avant, plus de temps, je suis perdu(e) |
| **Rouge** | j'agis maintenant | « Descendez maintenant ! » (alarme rouge qui pulse) · « non, ce n'est pas le bon bus » · je ne me sens pas bien |

La bande de couleur apparaît sous le bandeau dès qu'un arrêt est choisi ; la bordure du bloc « Mon arrêt » suit la même couleur.

**Écran Réglages (⚙)** : trois interrupteurs mémorisés sur le téléphone — **Voix**, **Couleurs** (coupées : tout redevient violet) et **Vibration** (remise en marche : petit essai). Le haut-parleur du bandeau coupe/rétablit la voix rapidement.

| Vibration | Moment |
|---|---|
| 1 très courte | je touche un bouton |
| 2 courtes | choix enregistré (mon arrêt, une demande) · « oui, bon bus » |
| 1 longue | « non, ce n'est pas le bon bus » |
| 1 moyenne | le bus vient de s'arrêter à un arrêt (quand j'ai choisi mon arrêt) |
| 2 moyennes | **orange** : mon arrêt est le prochain |
| 3 longues + 1 très longue | **rouge : c'est mon arrêt** — recommence toutes les 6 s jusqu'à ce qu'on touche « OK » |

Les motifs sont dans `static/js/a11y.js` (`vibrationService.patterns`). La vibration web fonctionne sur Android (Chrome, Firefox) ; **pas sur iPhone** (Safari ne l'autorise pas) : l'écran Réglages l'indique.

## Où modifier / étendre

| Pour… | Fichier |
|---|---|
| Ajouter une **langue** | `static/i18n/xx.json` (copier `en.json`) + ajouter le code dans `LANGS` (`static/js/store.js`) et la voix dans `_speech` |
| Changer les **lignes / arrêts** | `static/data/lines.json` (`photo` optionnelle dans `static/img/stops/`) |
| Ajouter un **service d'accessibilité** (lecture, haptique, braille…) | `static/js/a11y.js` : créer un objet `{ name, speak?, feedback?, stop? }` et l'enregistrer avec `register()` dans `main.js` |
| Brancher la **vraie position** (GPS / API temps réel) | remplacer `SimulatedPosition` (`static/js/position.js`) : il suffit de fournir `state = { next, atStop }` et d'appeler `onChange` |
| Couleurs, tailles | variables en tête de `static/css/app.css` |
| Régénérer **icônes et photos** depuis la charte | `python tools/build_assets.py` (nécessite pillow) |

## Tests

```
node --test tests/                                   # logique pure (frise « ··· », alarme, arrêts restants)
python -m unittest discover -s tests -p "test_*.py"  # serveur, QR codes, langues complètes
```
`tools/flow_test.js` est un parcours complet (carrousel, retour, aide, alarme, langue) à exécuter dans la console du navigateur sur `/?lang=en&manual=1` (après `localStorage.clear()`). La démo automatique (`?demo=x`) joue un parcours équivalent toute seule.

## Limites connues / points ouverts

- Une web app **ne peut pas sonner de façon fiable en arrière-plan** : l'alarme fonctionne tant que l'app est ouverte (écran maintenu allumé grâce à Wake Lock).
- Le mode hors-ligne (service worker) exige HTTPS (ou `localhost`) ; en HTTP sur une adresse locale l'app fonctionne mais sans cache hors-ligne.
- Le scanner de QR code intégré dépend du navigateur (BarcodeDetector : Chrome Android surtout) et demande HTTPS ; sinon, utiliser l'appareil photo du téléphone.
- La position du bus est **simulée** (pas de GPS ni de flux temps réel).
- Traductions allemand / italien non relues ; icônes et photos d'arrêts issues de la charte / de photos provisoires.
- La synthèse vocale dépend des voix installées sur le téléphone.
