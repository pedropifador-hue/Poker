import sys, json, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, sys.argv[1])
import numpy as np
from poker.decisionmaker.curvefitting import Curvefitting
s = json.load(open(sys.argv[1] + '/auditoria/estrategias_snapshot.json', encoding='utf-8'))['Trial 2']
bb = s['bigBlind']
print("Estrategia BB =", bb)
for st in ['PreFlop', 'Flop', 'Turn', 'River']:
    mx = 0.95 if st == 'PreFlop' else 1
    for kind, me, pw, top in [('call', s[st+'MinCallEquity'], s[st+'CallPower'], s['initialFunds']),
                              ('bet', s[st+'MinBetEquity'], s[st+'BetPower'], s['initialFunds2'])]:
        maxeq = s['PreFlopMaxBetEquity'] if (st == 'PreFlop' and kind == 'bet') else 1
        eqs = np.array([0.55, 0.65, 0.75, 0.85, 0.95])
        y = Curvefitting(eqs, 0, bb*2, top, me, maxeq, mx, int(pw)).y
        print(f"{st:7s} {kind:4s} minEq={me:.2f} power={int(pw):2d} | " + " ".join(f"eq{e:.2f}->{v:6.2f}" for e, v in zip(eqs, y)))
