"""Documenta (com evidencia executavel) as divergencias do motor original.

O motor original NAO e alterado: ele e apenas importado como referencia.
Cada teste afirma o comportamento atual do original e o comportamento correto do simulador.
Se um dia o original for corrigido, estes testes vao falhar e indicar que a documentacao deve mudar.
"""

import logging
import time

import numpy as np
import pytest

from simulador.avaliador import avaliar
from simulador.cartas import cartas
from simulador.equity import simular, enumerar
from simulador.ranges import Range

pytestmark = [pytest.mark.comparacao,
              pytest.mark.filterwarnings("ignore::DeprecationWarning")]  # np.random.random_integers no original
logging.disable(logging.CRITICAL)


@pytest.fixture(scope="module")
def MonteCarlo():
    from poker.decisionmaker.montecarlo_python import MonteCarlo as MC  # pylint: disable=import-outside-toplevel
    return MC


def _orig(MonteCarlo, mao, board, jogadores, faixa=1.0, n=4000, semente=0):
    np.random.seed(semente)
    m = MonteCarlo()
    m.run_montecarlo(logging.getLogger("t"), [mao.split()], board.split() if board else [], player_amount=jogadores,
                     ui=None, max_runs=n, timeout=time.time() + 300, ghost_cards="", opponent_range=faixa)
    return m.equity


def test_original_conta_empate_como_vitoria(MonteCarlo):
    orig = _orig(MonteCarlo, "2C 3D", "AS KS QS JS TS", 2)
    novo = enumerar(["2C 3D", "9H 9D"], board="AS KS QS JS TS").equity()
    assert novo == 0.5
    assert orig > 0.6                       # deveria ser 0,5
    # explicado pelo defeito do straight flush: o robo so "perde" se o vilao tiver uma espada (8 restantes)
    assert orig == pytest.approx(741 / 1081, abs=0.03)       # C(39,2)/C(47,2) = 0,685


def test_original_straight_flush_usa_carta_extra(MonteCarlo):
    m = MonteCarlo()
    board = ["AS", "KS", "QS", "JS", "TS"]
    com_9s = m.calc_score(board + ["9S", "2D"])
    sem = m.calc_score(board + ["2C", "3D"])
    assert com_9s[:2] > sem[:2]             # original: "vence"
    assert avaliar(cartas("AS KS QS JS TS 9S 2D")) == avaliar(cartas("AS KS QS JS TS 2C 3D"))  # correto: empate


def test_original_quadra_no_board_desempata_errado(MonteCarlo):
    m = MonteCarlo()
    board = ["2S", "2D", "2H", "2C", "KH"]
    heroi, vilao = m.calc_score(["KC", "4D"] + board), m.calc_score(["8D", "5H"] + board)
    assert heroi[:2] < vilao[:2]            # original: heroi perde
    assert avaliar(cartas("KC 4D 2S 2D 2H 2C KH")) == avaliar(cartas("8D 5H 2S 2D 2H 2C KH"))  # correto: empate


def test_original_vaza_maos_fora_do_range(MonteCarlo):
    np.random.seed(0)
    m = MonteCarlo()
    m.use_range_of_range = False
    permitido = m.get_opponent_allowed_cards_list(0.1)
    dentro = 0
    n = 4000
    for _ in range(n):
        jogadores, _, _ = m.distribute_cards_to_players(m.create_card_deck(), 2, [["AS", "AH"]], [], permitido, 0)
        c1, c2 = m.get_two_short_notation(jogadores[1])
        dentro += (c1 in permitido or c2 in permitido)
    assert 0.75 < dentro / n < 0.9          # ~17% fora do range
    assert len(permitido) == 16             # 16 classes = 7,8% das combinacoes
    assert Range.top(0.1, modo="classes").fracao_combos == pytest.approx(104 / 1326)


def test_original_coincide_onde_nao_ha_empate(MonteCarlo):
    """Hipotese descartada: o Monte Carlo original nao esta errado em geral."""
    orig = _orig(MonteCarlo, "AS AH", "", 2, n=8000, semente=1)
    novo = simular(["AS AH", None], iteracoes=8000, semente=1)
    assert abs(orig - novo.equity()) < 0.02
