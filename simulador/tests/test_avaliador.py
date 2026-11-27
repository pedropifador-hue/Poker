"""Validacao do avaliador independente contra resultados combinatorios conhecidos."""

from collections import Counter
from itertools import combinations

import pytest

from simulador.avaliador import avaliar
from simulador.cartas import cartas


def v(txt):
    return avaliar(cartas(txt))


# Contagem exata das 2.598.960 maos de 5 cartas (resultado matematico classico).
CONTAGEM_5_CARTAS = {
    8: 40,         # straight flush (inclui 4 royal flush)
    7: 624,        # quadra
    6: 3744,       # full house
    5: 5108,       # flush
    4: 10200,      # sequencia
    3: 54912,      # trinca
    2: 123552,     # dois pares
    1: 1098240,    # par
    0: 1302540,    # carta alta
}


@pytest.mark.lento
def test_contagem_exata_de_todas_as_maos_de_5_cartas():
    contagem = Counter(avaliar(m)[0] for m in combinations(range(52), 5))
    assert sum(contagem.values()) == 2598960
    assert dict(contagem) == CONTAGEM_5_CARTAS


@pytest.mark.parametrize("melhor, pior", [
    ("AS KS QS JS TS", "9S 9H 9D 9C AS"),          # royal > quadra
    ("5S 4S 3S 2S AS", "KH KD KC KS 2D"),          # straight flush roda > quadra
    ("9S 9H 9D 9C 2S", "8S 8H 8D 8C AS"),          # quadra mais alta vence
    ("AS AH AD KS KH", "KS KH KD AS AH"),          # full: trinca mais alta vence
    ("AS 9S 7S 5S 3S", "KS QS JS TS 8S"),          # flush: carta mais alta
    ("6S 5H 4D 3C 2S", "5H 4D 3C 2S AS"),          # sequencia 6 > roda
    ("AS AH QD QC 2S", "AS AH JD JC 2S"),          # dois pares: 2o par
    ("AS AH KD 4C 3S", "AS AH QD JC TS"),          # par: kicker
    ("AS KH QD JC 9S", "AS KH QD JC 8S"),          # carta alta: 5o kicker
])
def test_ordem_entre_maos(melhor, pior):
    assert v(melhor) > v(pior)


def test_roda_e_a_menor_sequencia():
    assert v("5H 4D 3C 2S AS") == (4, 3)


def test_sete_cartas_escolhe_melhor_combinacao():
    # Board com royal flush: qualquer mao empata (vale o board).
    board = "AS KS QS JS TS"
    assert v("2C 3D " + board) == v("9H 9D " + board) == (8, 12)


def test_straight_flush_com_seis_cartas_do_naipe_nao_usa_setima_carta():
    # Defeito do motor original: 9S extra "desempatava" o royal. Aqui deve empatar.
    board = "AS KS QS JS TS"
    assert v("9S 2D " + board) == v("2C 3D " + board)


def test_dois_pares_com_tres_pares_usa_melhor_kicker():
    # AA KK QQ 2: dois pares AA KK com kicker Q
    assert v("AS AH KS KH QS QH 2D") == (2, 12, 11, 10)


def test_full_house_com_duas_trincas():
    assert v("AS AH AD KS KH KD 2C") == (6, 12, 11)


def test_quadra_kicker_vem_de_qualquer_carta():
    assert v("9S 9H 9D 9C KS KH 2C") == (7, 7, 11)


def test_kickers_irrelevantes_empatam():
    # Par de ases com kickers K Q J; a 6a e 7a cartas nao contam
    assert v("AS AH KD QC JS 3H 2D") == v("AD AC KS QH JD 4S 2C")


@pytest.mark.parametrize("entrada", ["AS", "1S", "AX", "AS AS KD QC JS"])
def test_entradas_invalidas(entrada):
    with pytest.raises(ValueError):
        avaliar(cartas(entrada))
