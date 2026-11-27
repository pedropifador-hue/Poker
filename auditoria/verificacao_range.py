import sys, socket
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rede bloqueada"))
sys.path.insert(0, sys.argv[1])
from poker.decisionmaker.montecarlo_python import MonteCarlo
m = MonteCarlo(); m.use_range_of_range = False
allowed = m.get_opponent_allowed_cards_list(0.1)
inside = 0; N = 5000
for _ in range(N):
    deck = m.create_card_deck()
    players, _, _ = m.distribute_cards_to_players(deck, 2, [['AS', 'AH']], [], allowed, 0)
    c1, c2 = m.get_two_short_notation(players[1])
    inside += (c1 in allowed or c2 in allowed)
print(f"range pedido: top 10% ({len(allowed)} combinacoes de notacao); maos do oponente dentro do range: {inside/N:.1%}")
