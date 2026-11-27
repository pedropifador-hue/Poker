"""Simulacoes Monte Carlo offline com a rede bloqueada (prova de execucao sem servidor)."""
import logging, socket, sys, time

def _blocked(*a, **k):
    raise RuntimeError("REDE BLOQUEADA: tentativa de conexao externa")
socket.socket.connect = _blocked
socket.create_connection = _blocked

sys.path.insert(0, sys.argv[1])
from poker.decisionmaker.montecarlo_python import MonteCarlo

log = logging.getLogger('x')

def run(cards, table, players, rng=1.0, runs=20000):
    m = MonteCarlo()
    m.run_montecarlo(log, cards, table, player_amount=players, ui=None, max_runs=runs,
                     ghost_cards='', timeout=time.time() + 60, opponent_range=rng)
    return round(m.equity, 3)

print("AA vs 1 aleatorio (referencia ~0.85):", run([['AS', 'AH']], [], 2))
print("AA vs 5 aleatorios (referencia ~0.49):", run([['AS', 'AH']], [], 6))
print("72o vs 1 aleatorio (referencia ~0.35):", run([['7S', '2H']], [], 2))
print("AA vs 1 no top 10% (range=0.1):", run([['AS', 'AH']], [], 2, rng=0.1))
print("Board com royal flush (empate garantido, equity real de 'vitoria' = 0):",
      run([['2C', '3D']], ['AS', 'KS', 'QS', 'JS', 'TS'], 2, runs=2000))
