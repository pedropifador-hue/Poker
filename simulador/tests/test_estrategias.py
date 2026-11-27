"""Posicoes 6-max, ranges de abertura do autor e perfil de estudo."""

import pytest

from simulador.equity import simular
from simulador.estrategias import (POSICOES, carregar_perfil, posicao_por_utg_plus, ranges_de_abertura_do_autor,
                                   ranges_do_perfil, tabela_preflop_do_autor, utg_plus_por_posicao)


def _utg_plus_original(dealer_position, total_players=6):
    """Mesma formula de poker/scraper/table_screen_based.py:396 (0 = eu sou o dealer)."""
    return (total_players + 3 - dealer_position) % total_players


@pytest.mark.parametrize("dealer, posicao", [(0, "BTN"), (5, "SB"), (4, "BB"), (3, "UTG"), (2, "HJ"), (1, "CO")])
def test_mapeamento_de_posicoes_igual_ao_original(dealer, posicao):
    assert posicao_por_utg_plus(_utg_plus_original(dealer)) == posicao
    assert utg_plus_por_posicao(posicao) == _utg_plus_original(dealer)


@pytest.fixture(scope="module")
def autor():
    return ranges_de_abertura_do_autor()


def test_ranges_do_autor_alargam_com_a_posicao(autor):
    fracoes = [autor[p].fracao_combos for p in POSICOES[:5]]
    assert fracoes == sorted(fracoes)                 # UTG < HJ < CO < BTN < SB
    assert 0.14 < fracoes[0] < 0.20                   # UTG ~17%
    assert 0.35 < fracoes[3] < 0.45                   # BTN ~40%


def test_premium_sempre_abre(autor):
    for pos in POSICOES[:5]:
        assert {"AA", "KK", "QQ", "AKS", "AKO"} <= autor[pos].classes


def test_anomalias_da_tabela_sao_registradas():
    anomalias = []
    tabela_preflop_do_autor(anomalias=anomalias)
    assert ("5C2", "A3") in anomalias and ("5C2", "K7") in anomalias


def test_perfil_de_estudo():
    perfil = carregar_perfil()
    assert perfil["mesa"] == {"small_blind": 0.05, "big_blind": 0.10, "max_jogadores": 6, "stack_max_bb": 200}
    assert perfil["iteracoes"]["heads_up"] >= 5000
    ranges = ranges_do_perfil(perfil)
    assert set(ranges) == set(POSICOES[:5])


def test_equity_contra_range_utg_menor_que_contra_btn(autor):
    utg = simular(["AS JD", autor["UTG"]], iteracoes=6000, semente=1).equity()
    btn = simular(["AS JD", autor["BTN"]], iteracoes=6000, semente=1).equity()
    assert utg < btn - 0.03
