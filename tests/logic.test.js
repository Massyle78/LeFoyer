import test from 'node:test';
import assert from 'node:assert/strict';
import { stopStrip, stopsLeft, alarmPhase, aheadIndexes, goesTo } from '../static/js/logic.js';
import { SimulatedPosition } from '../static/js/position.js';

const shape = (items) => items.map((i) => (i.type === 'gap' ? `…${i.hidden}` : String(i.index)));

test('short line: every stop up to my stop is shown', () => {
  const items = stopStrip({ count: 7, next: 1, atStop: false, dest: 3 });
  assert.deepEqual(shape(items), ['1', '2', '3']);
  assert.equal(items[0].isNext, true);
  assert.equal(items[2].isTarget, true);
});

test('long line: three dots stand for the hidden stops', () => {
  const items = stopStrip({ count: 7, next: 1, atStop: false, dest: 6 });
  assert.deepEqual(shape(items), ['1', '2', '…3', '6']);
  assert.equal(items.at(-1).isTarget, true);
});

test('exactly maxNodes stops: no dots', () => {
  assert.deepEqual(shape(stopStrip({ count: 8, next: 0, atStop: false, dest: 3 })), ['0', '1', '2', '3']);
  assert.deepEqual(shape(stopStrip({ count: 8, next: 0, atStop: false, dest: 4 })), ['0', '1', '…2', '4']);
});

test('without my stop, the strip goes to the terminus', () => {
  const items = stopStrip({ count: 7, next: 2, atStop: false, dest: null });
  assert.deepEqual(shape(items), ['2', '3', '…2', '6']);
  assert.equal(items.at(-1).isTerminus, true);
  assert.equal(items.at(-1).isTarget, false);
});

test('single node when my stop is the next one', () => {
  const items = stopStrip({ count: 7, next: 3, atStop: false, dest: 3 });
  assert.deepEqual(shape(items), ['3']);
  assert.equal(items[0].isNext && items[0].isTarget, true);
});

test('stops left', () => {
  assert.equal(stopsLeft({ next: 1, atStop: false, dest: 3 }), 3); // Parc, Hôpital, Lac
  assert.equal(stopsLeft({ next: 1, atStop: true, dest: 3 }), 2);
  assert.equal(stopsLeft({ next: 3, atStop: false, dest: 3 }), 1);
  assert.equal(stopsLeft({ next: 3, atStop: true, dest: 3 }), 0);
  assert.equal(stopsLeft({ next: 4, atStop: false, dest: 3 }), null);
  assert.equal(stopsLeft({ next: 1, atStop: false, dest: null }), null);
});

test('alarm phases', () => {
  assert.equal(alarmPhase({ next: 2, atStop: false, dest: 3 }), null);
  assert.equal(alarmPhase({ next: 3, atStop: false, dest: 3 }), 'approaching');
  assert.equal(alarmPhase({ next: 3, atStop: true, dest: 3 }), 'now');
  assert.equal(alarmPhase({ next: 4, atStop: false, dest: 3 }), 'passed');
  assert.equal(alarmPhase({ next: 1, atStop: false, dest: null }), null);
});

test('stops ahead / right bus', () => {
  assert.deepEqual(aheadIndexes({ count: 4, next: 1, atStop: false }), [1, 2, 3]);
  assert.deepEqual(aheadIndexes({ count: 4, next: 1, atStop: true }), [2, 3]);
  assert.equal(goesTo({ count: 4, next: 1, atStop: false }, 0), false); // déjà passé
  assert.equal(goesTo({ count: 4, next: 1, atStop: false }, 3), true);
});

test('simulated bus runs to the terminus and stops there', () => {
  const seen = [];
  const pos = new SimulatedPosition(4, (s) => seen.push(s));
  assert.deepEqual(pos.state, { next: 1, atStop: false });
  for (let i = 0; i < 20; i++) pos.advance();
  assert.deepEqual(pos.state, { next: 3, atStop: true });
  assert.equal(pos.advance(), false);
  assert.equal(seen[0].atStop, true);
});
