"""Comparacao 'antes x depois': motor original (referencia, intacto) x simulador offline.

Executar (na pasta do projeto):
    .venv\\Scripts\\python.exe -m simulador.comparacao

Gera auditoria/fase2_comparacao.md. A rede fica bloqueada durante toda a execucao.
O motor original e apenas importado e chamado; nenhum arquivo dele e alterado.
"""

import logging
import os
import random
import sys
import time
from collections import Counter

import numpy as np

from .avaliador import avaliar
from .cartas import cartas, textos, classe_da_mao
from .equity import simular, enumerar
from .ranges import Range
from .seguranca import rede_bloqueada

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logging.disable(logging.CRITICAL)


def motor_original():
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    from poker.decisionmaker.montecarlo_python import MonteCarlo  # pylint: disable=import-outside-toplevel
    return MonteCarlo


def equity_original(mao, board, jogadores, faixa=1.0, n=20000, semente=0):
    np.random.seed(semente)
    m = motor_original()()
    m.run_montecarlo(logging.getLogger("orig"), [mao.split()], board.split() if board else [],
                     player_amount=jogadores, ui=None, max_runs=n, timeout=time.time() + 600,
                     ghost_cards="", opponent_range=faixa)
    return m.equity


def vazamento_de_range_original(fracao=0.1, n=20000, semente=0):
    """Fracao das maos do oponente (motor original) que caem dentro do range pedido."""
    np.random.seed(semente)
    m = motor_original()()
    m.use_range_of_range = False
    permitido = m.get_opponent_allowed_cards_list(fracao)
    dentro = 0
    divergentes = 0
    for _ in range(n):
        deck = m.create_card_deck()
        jogadores, _, _ = m.distribute_cards_to_players(deck, 2, [["AS", "AH"]], [], permitido, 0)
        c1, c2 = m.get_two_short_notation(jogadores[1])
        dentro += (c1 in permitido or c2 in permitido)
    return dentro / n, len(permitido)


def frequencia_cartas_oponente_original(n=40000, semente=0):
    """Com range total, conta quantas vezes cada carta vai para o oponente (deveria ser uniforme)."""
    np.random.seed(semente)
    m = motor_original()()
    m.use_range_of_range = False
    permitido = m.get_opponent_allowed_cards_list(1.0)
    cont = Counter()
    for _ in range(n):
        deck = m.create_card_deck()
        jogadores, _, _ = m.distribute_cards_to_players(deck, 2, [["2C", "3D"]], [], permitido, 0)
        cont.update(jogadores[1])
    return cont


def diferencial_avaliadores(n=200000, semente=0):
    """Compara o vencedor (heroi x vilao) segundo o avaliador original e o novo em n confrontos aleatorios."""
    m = motor_original()()
    rng = random.Random(semente)
    divergencias = Counter()
    exemplos = []
    for _ in range(n):
        cs = rng.sample(range(52), 9)
        heroi, vilao, board = cs[:2], cs[2:4], cs[4:]
        a, b = avaliar(heroi + board), avaliar(vilao + board)
        novo = (a > b) - (a < b)
        sa = m.calc_score(textos(heroi + board))
        sb = m.calc_score(textos(vilao + board))
        orig = ((sa[0], sa[1]) > (sb[0], sb[1])) - ((sa[0], sa[1]) < (sb[0], sb[1]))
        if novo != orig:
            chave = f"{['perde', 'empata', 'vence'][novo + 1]} -> original diz {['perde', 'empata', 'vence'][orig + 1]}"
            divergencias[chave] += 1
            if len(exemplos) < 5:
                exemplos.append((textos(heroi), textos(vilao), textos(board), chave))
    return divergencias, exemplos


def gerar_relatorio(rapido=False):
    n = 5000 if rapido else 20000
    linhas = ["# Fase 2 — Comparacao motor original x simulador offline", "",
              f"Gerado por `python -m simulador.comparacao` (rede bloqueada). Iteracoes Monte Carlo: {n}.", ""]

    # 1) Empates
    orig_royal = equity_original("2C 3D", "AS KS QS JS TS", 2, n=4000)
    novo_royal = simular(["2C 3D", None], board="AS KS QS JS TS", iteracoes=4000, semente=1)
    orig_72 = equity_original("7S 2H", "", 2, n=n, semente=2)
    novo_72 = simular(["7S 2H", None], iteracoes=n, semente=2)
    linhas += ["## 1. Empates e potes divididos", "",
               "| Cenario | Esperado | Original (antes) | Simulador (depois) |", "|---|---|---|---|",
               f"| 2c3d vs aleatoria, board AsKsQsJsTs (empate garantido) | 0,500 | {orig_royal:.3f} | {novo_royal.equity():.3f} (empate {novo_royal.prob_empate():.0%}) |",
               f"| 72o vs 1 aleatoria | ~0,346 | {orig_72:.3f} | {novo_72.equity():.3f} (vitoria {novo_72.prob_vitoria():.3f} + empate {novo_72.prob_empate():.3f}) |",
               "",
               f"Verificacao da hipotese: no original, 72o = {orig_72:.3f} ~ vitoria + empate do simulador "
               f"= {novo_72.prob_vitoria() + novo_72.prob_empate():.3f} → **os empates contam como vitoria inteira**.",
               "No board de royal flush o original nao da 1,0 porque um 2o defeito faz o vilao com qualquer espada "
               "\"vencer\" (ranks extras nao sao cortados no straight flush): P(vilao tem espada) = 1 − C(39,2)/C(47,2) = 0,315 "
               f"→ original ≈ 0,685 (medido {orig_royal:.3f}).", ""]

    # 2) Avaliador
    div, exemplos = diferencial_avaliadores(n=50000 if rapido else 200000)
    total = 50000 if rapido else 200000
    linhas += ["## 2. Avaliador de maos (teste diferencial)", "",
               f"{total} confrontos aleatorios heroi x vilao com board completo. "
               f"Divergencias: **{sum(div.values())}** ({sum(div.values()) / total:.3%}).", "",
               "| Resultado correto → resultado do original | Ocorrencias |", "|---|---|"]
    linhas += [f"| {k} | {v} |" for k, v in div.most_common()] or ["| (nenhuma) | 0 |"]
    linhas += ["", "Causa: todas as divergencias ocorrem com **quadra no board**. No original (`calc_score`, linhas 79-82) "
               "a mao e representada pelos dois maiores ranks distintos das 7 cartas (ex.: board 2222K + 84 vira (K, 8)), "
               "o que pode descartar o rank da quadra e usar uma carta que nao entra na melhor mao; "
               "o empate correto vira vitoria/derrota."]
    if exemplos:
        linhas += ["", "Exemplos:", ""]
        linhas += [f"- heroi {' '.join(h)} x vilao {' '.join(v)}, board {' '.join(b)}: {k}" for h, v, b, k in exemplos]
    linhas.append("")

    # 3) Ranges
    dentro, classes = vazamento_de_range_original(0.1, n=n)
    faixa = Range.top(0.1, modo="classes")
    r_novo = Range.top(0.1)
    linhas += ["## 3. Respeito aos ranges", "",
               "| Medida | Original (antes) | Simulador (depois) |", "|---|---|---|",
               f"| Maos do oponente dentro do range top 10% | {dentro:.1%} | 100% (teste `test_todas_as_maos_sorteadas_estao_no_range`) |",
               f"| Definicao de top 10% | {classes} classes = {faixa.fracao_combos:.1%} das combinacoes | {len(r_novo.classes)} classes = {r_novo.fracao_combos:.1%} das combinacoes |",
               "",
               "Causa (original, `distribute_cards_to_players`, linhas 224-225): `deck.pop(random_card1)` desloca os indices "
               "antes de `deck.pop(random_card2)`; quando o 2o indice e maior que o 1o, sai uma carta diferente da validada.", ""]

    from scipy.stats import chisquare  # pylint: disable=import-outside-toplevel
    cont = frequencia_cartas_oponente_original(n=n * 2)
    p = chisquare(list(cont.values())).pvalue
    media = sum(cont.values()) / len(cont)
    menor = min(cont, key=cont.get)
    veredito = "nao ha evidencia de vies (p > 0,01)" if p > 0.01 else "**distribuicao nao uniforme (p ≤ 0,01)**"
    linhas += [f"Uniformidade das cartas do oponente (original, range total, {n * 2} distribuicoes): "
               f"qui-quadrado p = {p:.3f} → {veredito}. Extremos: {menor} = {cont[menor] / media:.0%} da media, "
               f"{max(cont, key=cont.get)} = {max(cont.values()) / media:.0%} da media.", ""]

    # 4) Numero de jogadores
    orig_aa4 = equity_original("AS AH", "", 4, n=n, semente=4)
    orig_aa2 = equity_original("AS AH", "", 2, n=n, semente=5)
    novo_aa6 = simular(["AS AH"] + [None] * 5, iteracoes=n, semente=6)
    linhas += ["## 4. Numero de adversarios (6-max, 5 adversarios na mao)", "",
               "| Situacao | Jogadores simulados | Equity de AA |", "|---|---|---|",
               f"| Original, pre-flop (sempre heads-up) | 2 | {orig_aa2:.3f} |",
               f"| Original, pos-flop (limite `total_players − 2`) | 4 | {orig_aa4:.3f} |",
               f"| Simulador (correto) | 6 | {novo_aa6.equity():.3f} (referencia 0,492) |", ""]

    # 5) Hipoteses descartadas
    orig_aa1 = equity_original("AS AH", "", 2, n=n, semente=7)
    novo_aa1 = simular(["AS AH", None], iteracoes=n, semente=7)
    orig_aa_r = equity_original("AS AH", "", 2, faixa=0.1, n=n, semente=8)
    novo_aa_r = simular(["AS AH", Range.top(0.1, modo="classes")], iteracoes=n, semente=8)
    linhas += ["## 5. Hipoteses verificadas e descartadas", "",
               f"- *O Monte Carlo original esta errado em geral*: **descartada**. AA vs 1 aleatoria: original {orig_aa1:.3f}, "
               f"simulador {novo_aa1.equity():.3f}, referencia 0,852. A diferenca so aparece onde ha empates.",
               f"- *A equity de AA vs top 10% (0,849) era anomala*: **descartada**. Simulador com o mesmo range de 16 classes: "
               f"{novo_aa_r.equity():.3f}; original {orig_aa_r:.3f}. AA domina quase todas as classes do top 10%.", ""]
    return "\n".join(linhas)


def main():
    rapido = "--rapido" in sys.argv
    with rede_bloqueada():
        texto = gerar_relatorio(rapido=rapido)
    destino = os.path.join(RAIZ, "auditoria", "fase2_comparacao.md")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    print(texto)
    print(f"\nRelatorio salvo em {destino}")


if __name__ == "__main__":
    main()
