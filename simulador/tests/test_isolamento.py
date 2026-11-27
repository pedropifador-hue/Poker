"""Garante que o simulador e isolado: sem rede, sem conluio, sem controle de tela/mouse, sem o PokerBot."""

import os
import re
import socket
import subprocess
import sys

import pytest

from simulador.seguranca import RedeBloqueada

PASTA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(PASTA)
# comparacao.py importa o motor original APENAS como referencia (com a rede bloqueada)
MODULOS = [f for f in os.listdir(PASTA) if f.endswith(".py") and f not in ("comparacao.py", "seguranca.py")]

PROIBIDO = re.compile(r"\b(requests|urllib|http\.client|socket|collusion|conluio|pymouse|pyautogui|"
                      r"mouse_mover|vbox|mongo|game_logger|ImageGrab|from poker|import poker)\b")


@pytest.mark.parametrize("arquivo", MODULOS)
def test_modulos_nao_usam_rede_conluio_ou_pokerbot(arquivo):
    with open(os.path.join(PASTA, arquivo), encoding="utf-8") as f:
        codigo = "\n".join(l for l in f.read().splitlines() if not l.lstrip().startswith("#"))
    # ignora docstrings que apenas mencionam as palavras
    codigo = re.sub(r'"""[\s\S]*?"""', "", codigo)
    assert not PROIBIDO.search(codigo), f"{arquivo}: uso proibido -> {PROIBIDO.search(codigo).group(0)}"


def test_importar_simulador_nao_carrega_o_pokerbot():
    codigo = ("import sys, simulador.equity, simulador.cenario, simulador.ranges;"
              "print(sorted(m for m in sys.modules if m == 'poker' or m.startswith('poker.') or m == 'requests'))")
    saida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    assert saida.stdout.strip() == "[]"


def test_rede_bloqueada_durante_os_testes():
    with pytest.raises(RedeBloqueada):
        socket.create_connection(("example.com", 443), timeout=1)
    with pytest.raises(RedeBloqueada):
        socket.getaddrinfo("example.com", 443)
