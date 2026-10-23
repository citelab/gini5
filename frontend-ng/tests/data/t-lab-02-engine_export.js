// Export what the reference engine computes for every level x version x start, plus the codes
// the golden checks try by hand, so the Python port can be checked against it without node.
'use strict';
const path = require('node:path');
const E = require(path.resolve(process.argv[2]));
const L = Object.fromEntries(E.LEVELS.map((l) => [l.id, l]));

const EXTRA = {
  lost: [
    ['lock-one-side', [['acq', 'p1', 'p2', 'p3', 'rel'], ['c1', 'c2', 'c3']]],
    ['no-release', [['acq', 'p1', 'p2', 'p3'], ['acq', 'c1', 'c2', 'c3', 'rel']]],
  ],
  lockvar: [
    ['tas-no-release', [['tas', 'cs'], ['tas', 'cs', 'z']]],
  ],
  rdv: [
    ['signal-then-wait', [['a1', 'sa', 'wb', 'a2'], ['b1', 'sb', 'wa', 'b2']]],
    ['asymmetric', [['a1', 'sa', 'wb', 'a2'], ['b1', 'wa', 'sb', 'b2']]],
    ['a2-above-wait', [['a1', 'a2', 'wb', 'sa'], ['b1', 'sb', 'wa', 'b2']]],
  ],
  buffer: [
    ['fixed', [['pwe', 'pwm', 'ins', 'psm', 'psf'], ['cwf', 'cwm', 'rem', 'csm', 'cse']]],
    ['early-release', [['pwe', 'pwm', 'psm', 'ins', 'psf'], ['cwf', 'cwm', 'rem', 'csm', 'cse']]],
    ['insert-first', [['ins', 'pwe', 'pwm', 'psm', 'psf'], ['cwf', 'cwm', 'rem', 'csm', 'cse']]],
    ['no-waits', [['pwm', 'ins', 'psm', 'psf'], ['cwm', 'rem', 'csm', 'cse']]],
  ],
};
// Hand-played schedules whose trace the golden checks read row by row.
const PLAYED = {
  lost: { instr: [[0, 0, 1, 1, 0, 1]], locked: [[0, 1], [0, 1, 0, 0, 0, 0, 1]] },
  lockvar: { plain: [[0, 1, 0, 1], [0, 0, 1]] },
  rdv: { bad: [[0, 0, 1, 1]] },
  buffer: { swapped: [[0, 0, 1, 1]] },
};

function rows(lv, code, moves, start) {
  const r = E.replay(lv, code, moves, start);
  return { rows: r.rows.map((x) => [x.t, x.text, x.kind, x.state, x.note, !!x.bad]),
           path: r.path, done: r.done, deadlock: r.deadlock };
}
function sortedPts(o) { return Object.keys(o).map((k) => k.split(',').map(Number)).sort((a, b) => a[0] - b[0] || a[1] - b[1]); }

const cases = [];
for (const lv of E.LEVELS) {
  const starts = lv.starts ? lv.starts.map((_, i) => i) : [0];
  const codes = [];
  for (const v of lv.versionOrder) codes.push([v, lv.versions[v].code]);
  for (const [name, code] of EXTRA[lv.id] || []) codes.push([name, code]);
  for (const [name, code] of codes) {
    for (const start of starts) {
      const r = E.explore(lv, code, start);
      const replays = {};
      if (r.deadlock) replays['deadlock'] = rows(lv, code, r.deadlock, start);
      if (r.violation) replays['violation'] = rows(lv, code, r.violation, start);
      r.outcomes.forEach((o, i) => { replays['outcome' + i] = rows(lv, code, o.moves, start); });
      for (const moves of (PLAYED[lv.id] || {})[name] || []) replays['played ' + moves.join('')] = rows(lv, code, moves, start);
      cases.push({
        level: lv.id, code_name: name, code, start,
        explore: {
          total: r.total, dlPaths: r.dlPaths, certified: r.certified,
          deadlock: r.deadlock, violation: r.violation,
          outcomes: r.outcomes.map((o) => ({ label: o.label, correct: o.correct, paths: o.paths, moves: o.moves })),
          points: sortedPts(r.points), dlPoints: sortedPts(r.dlPoints),
        },
        replays,
      });
    }
  }
}
process.stdout.write(JSON.stringify({ cases }, null, 1) + '\n');
