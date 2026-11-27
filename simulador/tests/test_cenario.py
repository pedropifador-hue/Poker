"""Testes do cenario de estudo: mesa 6-max 0,05/0,10, 200 BB, stacks efetivos e rake hipotetico."""

import pytest

from simulador.cenario import (ConfigMesa, ESTRUTURAS_RAKE_HIPOTETICAS, MESA_REFERENCIA, Rake,
                               equity_necessaria, estudar_allin, ev_call, ev_call_allin,
                               odds_do_pote, stack_efetivo)
from simulador.ranges import Range


def test_mesa_de_referencia():
    m = MESA_REFERENCIA
    assert (m.small_blind, m.big_blind, m.max_jogadores, m.stack_max_bb) == (0.05, 0.10, 6, 200)
    assert m.stack_max == pytest.approx(20.0)
    assert m.em_bb(2.5) == pytest.approx(25)


@pytest.mark.parametrize("stack", [0, -1, 20.01, 50])
def test_stack_fora_do_limite(stack):
    with pytest.raises(ValueError):
        MESA_REFERENCIA.validar_stack(stack)


@pytest.mark.parametrize("n, ok", [(1, False), (2, True), (6, True), (7, False)])
def test_numero_de_jogadores_6_max(n, ok):
    if ok:
        assert MESA_REFERENCIA.validar_jogadores(n) == n
    else:
        with pytest.raises(ValueError):
            MESA_REFERENCIA.validar_jogadores(n)


def test_stack_efetivo():
    assert stack_efetivo(20, 7.5) == 7.5
    assert stack_efetivo(5, 20) == 5
    assert stack_efetivo(10, 3, 12, 4) == 10      # multiway: limitado pelo maior vilao
    assert stack_efetivo(10, 3, 4) == 4


def test_rake_percentual_teto_e_sem_flop():
    r = Rake(0.05, 0.30)
    assert r.calcular(2.00) == pytest.approx(0.10)
    assert r.calcular(10.00) == pytest.approx(0.30)     # teto
    assert r.calcular(10.00, viu_flop=False) == 0       # no flop, no drop
    assert Rake(0.05, 0.30, sem_flop_sem_rake=False).calcular(1.0, viu_flop=False) == pytest.approx(0.05)
    assert Rake().calcular(100) == 0


def test_estruturas_hipoteticas_disponiveis():
    assert set(ESTRUTURAS_RAKE_HIPOTETICAS) >= {"sem_rake", "5%_teto_3bb", "4,5%_sem_teto"}
    assert ESTRUTURAS_RAKE_HIPOTETICAS["4,5%_sem_teto"].calcular(40) == pytest.approx(1.8)


def test_odds_do_pote_e_equity_necessaria():
    assert odds_do_pote(1.0, 0.5) == pytest.approx(1 / 3)
    sem = equity_necessaria(1.0, 0.5)
    com = equity_necessaria(1.0, 0.5, Rake(0.05, 0.30))
    assert sem == pytest.approx(1 / 3)
    assert com == pytest.approx(0.5 / (1.5 - 0.075))
    assert com > sem                                    # rake exige mais equity


def test_ev_zero_no_ponto_de_equilibrio():
    rake = Rake(0.05, 0.30)
    e = equity_necessaria(2.0, 1.0, rake)
    assert ev_call(e, 2.0, 1.0, rake) == pytest.approx(0, abs=1e-12)
    assert ev_call(e + 0.01, 2.0, 1.0, rake) > 0 > ev_call(e - 0.01, 2.0, 1.0, rake)


def test_allin_usa_somente_stack_efetivo():
    # Heroi no BB (investiu 0,10) com 20,00; vilao no SB empurra 10,00. Sem dinheiro morto.
    a = ev_call_allin(0.5, stack_heroi=20, stack_vilao=10, investido_heroi=0.10)
    assert a.stack_efetivo == 10 and a.pote_final == 20
    assert a.custo_call == pytest.approx(9.90)
    assert a.ev == pytest.approx(0.5 * 20 - 9.90)
    assert a.ev_bb == pytest.approx(1.0)


def test_stacks_efetivos_diferentes_mudam_o_ev():
    evs = [ev_call_allin(0.6, s, 20, investido_heroi=0.10).ev for s in (5, 10, 20)]
    assert evs[0] < evs[1] < evs[2]                     # com vantagem, mais fichas em jogo = mais EV


def test_rake_reduz_ev_do_allin():
    base = ev_call_allin(0.55, 20, 20, investido_heroi=0.10, dinheiro_morto=0.05)
    com_rake = ev_call_allin(0.55, 20, 20, investido_heroi=0.10, dinheiro_morto=0.05,
                             rake=ESTRUTURAS_RAKE_HIPOTETICAS["5%_teto_3bb"])
    assert com_rake.rake == pytest.approx(0.30)
    assert com_rake.ev == pytest.approx(base.ev - 0.55 * 0.30)
    assert com_rake.equity_necessaria > base.equity_necessaria


def test_estudo_allin_aa_contra_top_10_porcento():
    a, res = estudar_allin("AS AH", Range.top(0.1), 20, 20, investido_heroi=0.10, dinheiro_morto=0.05,
                           rake=ESTRUTURAS_RAKE_HIPOTETICAS["5%_teto_3bb"], iteracoes=5000, semente=1)
    assert res.equity() > 0.75
    assert a.ev_bb > 100                                # ~ +110 BB com 200 BB efetivos


def test_estudo_allin_mao_fraca_tem_ev_negativo():
    a, _ = estudar_allin("7S 2H", Range.top(0.1), 20, 20, investido_heroi=0.10, iteracoes=5000, semente=2)
    assert a.ev < 0


def test_config_alternativa():
    m = ConfigMesa(small_blind=0.25, big_blind=0.50, stack_max_bb=100)
    assert m.stack_max == pytest.approx(50)
