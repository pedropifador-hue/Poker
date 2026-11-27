"""Validacao matematica do motor de equity independente."""

import math
from collections import Counter

import pytest
from scipy.stats import chisquare

from simulador.cartas import cartas, classe_da_mao
from simulador.equity import distribuir, enumerar, simular, _normalizar
from simulador.ranges import Range, COMBOS_POR_CLASSE

import random


# ---------------------------------------------------------------- vitoria (formula fechada)

def test_outs_no_turn_formula_fechada():
    """AhKh vs QsQd em 2h 7h Qc 3s: heroi so vence com copas que nao pareia o board.
    Copas restantes: 9; Qh (quadra do vilao) e 3h (full house do vilao) nao servem -> 7/44."""
    r = enumerar(["AH KH", "QS QD"], board="2H 7H QC 3S")
    assert r.iteracoes == 44
    assert r.equity(0) == pytest.approx(7 / 44, abs=1e-12)
    assert r.prob_empate(0) == 0


def test_set_contra_overpair_no_flop_formula_fechada():
    """AA vs KK em 2c 7d 9h: KK vence com pelo menos um K entre turn/river, exceto K+A.
    Boards com K: 990 - C(43,2) = 87; com K e A: 2*2 = 4 -> KK vence 83/990."""
    r = enumerar(["AS AH", "KD KC"], board="2C 7D 9H")
    assert r.iteracoes == math.comb(45, 2)
    assert r.equity(1) == pytest.approx(83 / 990, abs=1e-12)
    assert r.equity(0) == pytest.approx(907 / 990, abs=1e-12)


# ---------------------------------------------------------------- empates e potes divididos

def test_board_royal_flush_empate_total():
    r = enumerar(["2C 3D", "9H 9D"], board="AS KS QS JS TS")
    assert r.prob_vitoria(0) == 0 and r.prob_empate(0) == 1
    assert r.equity(0) == pytest.approx(0.5)


def test_pote_dividido_em_tres():
    # Board faz sequencia A-K-Q-J-T; tres jogadores sem melhorar -> cada um 1/3
    r = enumerar(["2C 3D", "4H 5S", "6C 7S"], board="AS KD QH JC TS")
    for i in range(3):
        assert r.equity(i) == pytest.approx(1 / 3)
        assert r.prob_empate(i) == 1


def test_empate_parcial_com_um_vencedor():
    # Heroi (AsKs) faz flush; os outros dois empatariam entre si mas perdem
    r = enumerar(["AS KS", "2C 3D", "2D 3C"], board="QS JS 4S 9H 8D")
    assert r.equity(0) == 1 and r.equity(1) == 0 and r.equity(2) == 0


def test_soma_das_equities_e_um_multiway():
    r = simular(["AS AH", "KD KC", None, None, None, None], iteracoes=4000, semente=7)
    assert sum(r.equity(i) for i in range(6)) == pytest.approx(1.0, abs=1e-9)


def test_espelho_aa_contra_aa():
    """AsAh vs AdAc pre-flop: simetria -> equity 0,5 para cada; empate domina (~95%)."""
    r = simular(["AS AH", "AD AC"], iteracoes=20000, semente=11)
    assert r.equity(0) == pytest.approx(0.5, abs=0.01)
    assert 0.93 < r.prob_empate(0) < 0.97


# ---------------------------------------------------------------- valores de referencia conhecidos

# Equity de AA contra k maos aleatorias (tabelas classicas de equity pre-flop).
AA_REFERENCIA = {1: 0.852, 2: 0.735, 3: 0.639, 4: 0.559, 5: 0.492}


@pytest.mark.parametrize("adversarios", [1, 2, 3, 4, 5])
def test_aa_contra_n_aleatorios_2_a_6_jogadores(adversarios):
    r = simular(["AS AH"] + [None] * adversarios, iteracoes=20000, semente=100 + adversarios)
    assert abs(r.equity() - AA_REFERENCIA[adversarios]) < max(0.012, 4 * r.erro_padrao())


def test_72o_contra_aleatorio():
    r = simular(["7S 2H", None], iteracoes=30000, semente=5)
    assert r.equity() == pytest.approx(0.346, abs=0.012)
    assert r.prob_empate() > 0.03  # empates sao frequentes com 72o (tabuleiro joga)


@pytest.mark.lento
def test_aa_contra_kk_pre_flop_enumeracao_exata():
    """1.712.304 boards. Valor classico ~82%; comparado tambem ao Monte Carlo."""
    exato = enumerar(["AS AH", "KD KC"])
    assert exato.iteracoes == math.comb(48, 5)
    assert exato.equity() == pytest.approx(0.82, abs=0.01)
    mc = simular(["AS AH", "KD KC"], iteracoes=20000, semente=3)
    assert abs(mc.equity() - exato.equity()) < 4 * mc.erro_padrao()


def test_monte_carlo_bate_com_enumeracao_no_flop():
    board = "JH 8S 2D"
    exato = enumerar(["AH KH", "8C 8D"], board=board)
    mc = simular(["AH KH", "8C 8D"], board=board, iteracoes=20000, semente=21)
    assert abs(mc.equity() - exato.equity()) < 4 * mc.erro_padrao()


# ---------------------------------------------------------------- distribuicao e unicidade das cartas

def test_cartas_unicas_em_mesa_6_max():
    specs, board, conhecidas = _normalizar(["AS AH", Range.top(0.2), None, None, Range.top(0.5), None], "2C 7D")
    rng = random.Random(1)
    for _ in range(3000):
        maos, b = distribuir(specs, board, conhecidas, rng)
        todas = [c for m in maos for c in m] + b
        assert len(todas) == 17 and len(set(todas)) == 17
        assert maos[0] == cartas("AS AH") and b[:2] == cartas("2C 7D")


def test_distribuicao_uniforme_das_cartas_do_board():
    specs, board, conhecidas = _normalizar(["AS AH", None], [])
    rng = random.Random(2)
    contagem = Counter()
    n = 50 * 1000
    for _ in range(n // 5):
        _, b = distribuir(specs, board, conhecidas, rng)
        contagem.update(b)
    observadas = [contagem[c] for c in range(52) if c not in conhecidas]
    assert len(observadas) == 50
    assert chisquare(observadas).pvalue > 0.001


# ---------------------------------------------------------------- respeito aos ranges

@pytest.mark.parametrize("fracao", [0.05, 0.1, 0.25, 0.5])
def test_todas_as_maos_sorteadas_estao_no_range(fracao):
    faixa = Range.top(fracao)
    specs, board, conhecidas = _normalizar(["AS AH", faixa, faixa], [])
    rng = random.Random(3)
    for _ in range(3000):
        maos, _ = distribuir(specs, board, conhecidas, rng)
        assert faixa.contem(*maos[1]) and faixa.contem(*maos[2])


def test_frequencia_das_classes_proporcional_as_combinacoes():
    faixa = Range(["AA", "AKS", "AKO"])  # 6 + 4 + 12 combos (sem cartas bloqueadas)
    specs, board, conhecidas = _normalizar(["2C 3D", faixa], [])
    rng = random.Random(4)
    contagem = Counter()
    n = 22000
    for _ in range(n):
        maos, _ = distribuir(specs, board, conhecidas, rng)
        contagem[classe_da_mao(*maos[1])] += 1
    observadas = [contagem["AA"], contagem["AKS"], contagem["AKO"]]
    esperadas = [n * 6 / 22, n * 4 / 22, n * 12 / 22]
    assert chisquare(observadas, esperadas).pvalue > 0.001


def test_range_por_combinacoes_vs_por_classes():
    por_combos = Range.top(0.1)
    por_classes = Range.top(0.1, modo="classes")
    assert 0.09 <= por_combos.fracao_combos <= 0.12
    assert len(por_classes.classes) == 16           # 10% de 169 classes, como no original
    assert por_classes.fracao_combos < 0.09         # ...mas so ~7,8% das combinacoes


def test_range_reduz_equity_de_mao_media():
    contra_qualquer = simular(["QS JS", None], iteracoes=15000, semente=8)
    contra_top10 = simular(["QS JS", Range.top(0.1)], iteracoes=15000, semente=8)
    assert contra_top10.equity() < contra_qualquer.equity() - 0.1


def test_combos_bloqueados_sao_respeitados():
    faixa = Range(["AA"])
    r = simular(["AS AH", faixa], iteracoes=2000, semente=9)  # vilao so pode ter AdAc
    assert r.prob_empate() > 0.9


def test_range_impossivel_gera_erro():
    with pytest.raises(RuntimeError):
        simular(["AS AH", Range(["AA"]), Range(["AA"])], iteracoes=10, semente=1)


# ---------------------------------------------------------------- reprodutibilidade e convergencia

def test_mesma_semente_mesmo_resultado():
    a = simular(["AS KD", Range.top(0.3), None], iteracoes=3000, semente=42)
    b = simular(["AS KD", Range.top(0.3), None], iteracoes=3000, semente=42)
    assert [a.equity(i) for i in range(3)] == [b.equity(i) for i in range(3)]


def test_sementes_diferentes_resultados_compativeis():
    a = simular(["AS KD", None], iteracoes=5000, semente=1)
    b = simular(["AS KD", None], iteracoes=5000, semente=2)
    assert a.equity() != b.equity()
    assert abs(a.equity() - b.equity()) < 4 * math.hypot(a.erro_padrao(), b.erro_padrao())


def test_convergencia_erro_padrao_cai_com_raiz_de_n():
    board = "TH 9H 2C"
    exato = enumerar(["AH 5H", "TS TC"], board=board).equity()
    erros = []
    for n in (1000, 4000, 16000):
        r = simular(["AH 5H", "TS TC"], board=board, iteracoes=n, semente=n)
        assert abs(r.equity() - exato) < 4 * r.erro_padrao()
        erros.append(r.erro_padrao())
    # quadruplicar n deve reduzir o erro padrao pela metade (razao ~2)
    assert 1.7 < erros[0] / erros[1] < 2.3
    assert 1.7 < erros[1] / erros[2] < 2.3


# ---------------------------------------------------------------- validacoes de entrada

@pytest.mark.parametrize("jogadores, board", [
    (["AS AH", "AS KD"], None),        # carta repetida
    (["AS AH", None], "AS 2C 3D"),     # carta da mao no board
    (["AS"], None),                    # 1 jogador
    (["AS AH", None], "2C 3D 4H 5S 6C 7D"),  # board > 5
])
def test_entradas_invalidas(jogadores, board):
    with pytest.raises(ValueError):
        simular(jogadores, board=board, iteracoes=10, semente=1)
