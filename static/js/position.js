// Position du bus. Tout est local au téléphone : aucune communication avec le conducteur.
//
// Choix « le plus simple pour le moment » : position SIMULÉE qui avance doucement.
// Pour un vrai suivi, écrire un autre fournisseur avec la même interface
// (next, atStop, reset(count), start(ms), stop(), onChange) — par exemple via
// navigator.geolocation et les coordonnées des arrêts.

export class SimulatedPosition {
  constructor(count, onChange = () => {}) {
    this.onChange = onChange;
    this.timer = null;
    this.reset(count);
  }

  reset(count = this.count) {
    this.count = count;
    // Démo : « entre le 1er et le 2e arrêt, prochain arrêt = le 2e »
    this.next = Math.min(1, count - 1);
    this.atStop = false;
  }

  get state() {
    return { next: this.next, atStop: this.atStop };
  }

  advance() {
    if (this.atStop) {
      if (this.next >= this.count - 1) return false; // terminus : on reste en place
      this.next += 1;
      this.atStop = false;
    } else {
      this.atStop = true;
    }
    this.onChange(this.state);
    return true;
  }

  start(ms) {
    this.stop();
    if (ms > 0) this.timer = setInterval(() => this.advance(), ms);
  }

  stop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }
}
