"""Teste da janela do simulador em modo invisivel (offscreen)."""

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from simulador.janela import Janela  # noqa: E402  pylint: disable=wrong-import-position


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _esperar(app, cond, limite=60):
    fim = time.time() + limite
    while not cond() and time.time() < fim:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()
    return cond()


def test_iniciar_pausar_continuar_e_concluir(app):
    j = Janela()
    j.ed_mao.setText("AS AH")
    j.sp_iter.setValue(4000)
    j.cb_range.setCurrentIndex(0)  # qualquer mao
    j.iniciar()
    assert _esperar(app, lambda: j.resultado is not None)
    j.pausar()
    assert j.trabalho.pausado and j.bt_pausar.text() == "Continuar"
    parado_em = j.resultado.iteracoes
    time.sleep(0.4)
    app.processEvents()
    assert j.resultado.iteracoes <= parado_em + 500       # no maximo o lote em andamento
    j.pausar()
    assert _esperar(app, lambda: j.trabalho.isFinished() and j.bt_iniciar.isEnabled())
    assert j.resultado.iteracoes == 4000
    assert 0.82 < j.resultado.equity() < 0.89           # AA x 1 aleatoria ~0,852
    assert "Equity" in j.lb_resultado.text() and "EV" in j.lb_resultado.text()
    assert "AA ESTA no range de abertura" in j.lb_resultado.text()   # posicao padrao BTN


def test_parar_interrompe(app):
    j = Janela()
    j.sp_iter.setValue(200000)
    j.iniciar()
    assert _esperar(app, lambda: j.resultado is not None)
    j.parar()
    assert _esperar(app, lambda: j.trabalho.isFinished() and j.bt_iniciar.isEnabled())
    assert j.resultado.iteracoes < 200000


def test_entrada_invalida_nao_inicia(app, monkeypatch):
    avisos = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *a, **k: avisos.append(a))
    j = Janela()
    j.ed_mao.setText("AS XX")
    j.iniciar()
    assert avisos and j.trabalho is None


def test_relatorios_carregam(app):
    j = Janela()
    for i in range(j.cb_rel.count()):
        j.cb_rel.setCurrentIndex(i)
        assert j.tx_rel.toPlainText().strip()
