"""Configuracao dos testes do simulador: rede SEMPRE bloqueada."""

import pytest

from simulador.seguranca import rede_bloqueada


def pytest_configure(config):
    config.addinivalue_line("markers", "lento: teste exaustivo que leva mais tempo (dezenas de segundos)")
    config.addinivalue_line("markers", "comparacao: compara com o motor original do PokerBot")


@pytest.fixture(autouse=True)
def _sem_rede():
    with rede_bloqueada():
        yield
