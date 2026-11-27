"""Janela do Simulador Offline (PyQt6) — estudo de equity, pot odds, stacks e rake.

Abre com dois cliques em "Abrir Simulador.bat". Funciona sem internet e sem o servidor
do desenvolvedor. Nao controla mouse, nao le a tela e nao se conecta a salas de poker.
"""

import os
import sys

from PyQt6.QtCore import QProcess, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
                             QProgressBar, QPushButton, QSpinBox, QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from .cartas import cartas as _parse_cartas, classe_da_mao
from .cenario import ConfigMesa, ESTRUTURAS_RAKE_HIPOTETICAS, equity_necessaria, ev_call, ev_call_allin, odds_do_pote
from .equity import Resultado, ResultadoJogador, simular
from .estrategias import POSICOES, carregar_perfil, ranges_do_perfil
from .ranges import Range

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOTE = 500

RELATORIOS = {
    "Manual de uso": "MANUAL.md",
    "Estrategias em simulacao (Fase 3)": "auditoria/fase3_estrategias.md",
    "Motor original x simulador (Fase 2)": "auditoria/fase2_comparacao.md",
    "Situacao do projeto": "PROJECT_STATUS.md",
    "Historico de mudancas": "CHANGELOG.md",
}


class Trabalhador(QThread):
    """Executa a simulacao em lotes, permitindo pausar e parar."""
    progresso = pyqtSignal(object)
    terminou = pyqtSignal(object, bool)
    falhou = pyqtSignal(str)

    def __init__(self, jogadores, board, iteracoes, semente):
        super().__init__()
        self.jogadores, self.board, self.iteracoes, self.semente = jogadores, board, iteracoes, semente
        self.pausado = False
        self.parar = False

    def run(self):
        total = Resultado(iteracoes=0, jogadores=[ResultadoJogador() for _ in self.jogadores])
        lote_n = 0
        try:
            while total.iteracoes < self.iteracoes and not self.parar:
                if self.pausado:
                    self.msleep(150)
                    continue
                n = min(LOTE, self.iteracoes - total.iteracoes)
                r = simular(self.jogadores, board=self.board, iteracoes=n, semente=self.semente * 100003 + lote_n)
                lote_n += 1
                total.iteracoes += n
                for acc, novo in zip(total.jogadores, r.jogadores):
                    acc.vitorias += novo.vitorias
                    acc.empates += novo.empates
                    acc.participacao += novo.participacao
                    acc.soma_quadrados += novo.soma_quadrados
                self.progresso.emit(total)
        except Exception as e:  # pylint: disable=broad-except
            self.falhou.emit(str(e))
            return
        self.terminou.emit(total, self.parar)


class Janela(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador Offline — estudo de Texas Hold'em (sem conexao)")
        self.resize(980, 720)
        self.perfil = carregar_perfil()
        self.ranges_pos = ranges_do_perfil(self.perfil)
        m = self.perfil["mesa"]
        self.mesa = ConfigMesa(m["small_blind"], m["big_blind"], m["max_jogadores"], m["stack_max_bb"])
        self.trabalho = None
        self.resultado = None

        abas = QTabWidget()
        abas.addTab(self._aba_simulacao(), "Simulacao")
        abas.addTab(self._aba_relatorios(), "Relatorios e manual")
        abas.addTab(self._aba_testes(), "Testes")
        self.setCentralWidget(abas)
        self.statusBar().showMessage(
            f"Perfil: {self.perfil['nome']} · mesa {m['small_blind']:.2f}/{m['big_blind']:.2f} · "
            f"{m['max_jogadores']}-max · ate {m['stack_max_bb']} BB · OFFLINE")

    # ------------------------------------------------------------------ aba simulacao
    def _aba_simulacao(self):
        w = QWidget()
        grade = QGridLayout(w)

        maos = QGroupBox("1. Maos e mesa")
        f = QFormLayout(maos)
        self.ed_mao = QLineEdit("AS KD")
        self.ed_mao.setToolTip("Duas cartas: valor (2-9, T, J, Q, K, A) + naipe (S espadas, H copas, D ouros, C paus)")
        self.ed_board = QLineEdit("")
        self.ed_board.setPlaceholderText("opcional: 3 a 5 cartas, ex.: 7H 8D 2C")
        self.cb_pos = QComboBox()
        self.cb_pos.addItems(POSICOES)
        self.cb_pos.setCurrentText("BTN")
        self.sp_adv = QSpinBox()
        self.sp_adv.setRange(1, self.mesa.max_jogadores - 1)
        self.sp_adv.setValue(1)
        self.cb_range = QComboBox()
        self.cb_range.addItems(["Qualquer mao"] + [f"Abertura {p} ({self.perfil['ranges_abertura_pct'][p]}%)"
                                                   for p in POSICOES[:5]] + ["Top X% (abaixo)"])
        self.cb_range.setCurrentIndex(4)
        self.sp_top = QSpinBox()
        self.sp_top.setRange(1, 100)
        self.sp_top.setValue(20)
        self.sp_top.setSuffix(" %")
        f.addRow("Sua mao:", self.ed_mao)
        f.addRow("Cartas na mesa:", self.ed_board)
        f.addRow("Sua posicao:", self.cb_pos)
        f.addRow("Adversarios na mao:", self.sp_adv)
        f.addRow("Range dos adversarios:", self.cb_range)
        f.addRow("Top X%:", self.sp_top)

        aposta = QGroupBox("2. Pote, stacks e rake (em BB; 1 BB = R$ 0,10)")
        g = QFormLayout(aposta)
        self.sp_pote = self._spin(6.0, 0, 400)
        self.sp_call = self._spin(3.0, 0, 200)
        self.sp_stack_h = self._spin(100.0, 1, self.mesa.stack_max_bb)
        self.sp_stack_v = self._spin(100.0, 1, self.mesa.stack_max_bb)
        self.cb_rake = QComboBox()
        for chave, r in ESTRUTURAS_RAKE_HIPOTETICAS.items():
            self.cb_rake.addItem(r.nome, chave)
        self.cb_rake.setCurrentIndex(list(ESTRUTURAS_RAKE_HIPOTETICAS).index(self.perfil["rake_padrao"]))
        g.addRow("Pote antes do seu call:", self.sp_pote)
        g.addRow("Valor para pagar (call):", self.sp_call)
        g.addRow("Seu stack:", self.sp_stack_h)
        g.addRow("Stack do adversario:", self.sp_stack_v)
        g.addRow("Rake (hipotetico):", self.cb_rake)

        controle = QGroupBox("3. Simulacao")
        h = QFormLayout(controle)
        self.sp_iter = QSpinBox()
        self.sp_iter.setRange(1000, 500000)
        self.sp_iter.setSingleStep(1000)
        self.sp_iter.setValue(self.perfil["iteracoes"]["heads_up"])
        self.sp_semente = QSpinBox()
        self.sp_semente.setRange(0, 999999)
        self.sp_semente.setValue(self.perfil["semente"])
        self.sp_semente.setToolTip("Mesma semente = mesmo resultado (reprodutivel)")
        botoes = QHBoxLayout()
        self.bt_iniciar = QPushButton("Iniciar")
        self.bt_pausar = QPushButton("Pausar")
        self.bt_parar = QPushButton("Parar")
        self.bt_pausar.setEnabled(False)
        self.bt_parar.setEnabled(False)
        self.bt_iniciar.clicked.connect(self.iniciar)
        self.bt_pausar.clicked.connect(self.pausar)
        self.bt_parar.clicked.connect(self.parar)
        for b in (self.bt_iniciar, self.bt_pausar, self.bt_parar):
            botoes.addWidget(b)
        self.barra = QProgressBar()
        h.addRow("Iteracoes:", self.sp_iter)
        h.addRow("Semente:", self.sp_semente)
        h.addRow(botoes)
        h.addRow(self.barra)

        saida = QGroupBox("4. Resultado")
        v = QVBoxLayout(saida)
        self.lb_resultado = QLabel("Preencha os campos e clique em Iniciar.")
        self.lb_resultado.setTextFormat(Qt.TextFormat.RichText)
        self.lb_resultado.setWordWrap(True)
        self.lb_resultado.setAlignment(Qt.AlignmentFlag.AlignTop)
        v.addWidget(self.lb_resultado)

        grade.addWidget(maos, 0, 0)
        grade.addWidget(aposta, 0, 1)
        grade.addWidget(controle, 1, 0)
        grade.addWidget(saida, 1, 1)
        grade.setRowStretch(1, 1)
        return w

    @staticmethod
    def _spin(valor, minimo, maximo):
        s = QDoubleSpinBox()
        s.setRange(minimo, maximo)
        s.setDecimals(1)
        s.setValue(valor)
        s.setSuffix(" BB")
        return s

    def _range_adversario(self):
        i = self.cb_range.currentIndex()
        if i == 0:
            return None
        if 1 <= i <= 5:
            return self.ranges_pos[POSICOES[i - 1]]
        return Range.top(self.sp_top.value() / 100)

    def iniciar(self):
        try:
            mao = self.ed_mao.text().strip()
            board = self.ed_board.text().strip() or None
            if board and len(board.split()) not in (3, 4, 5):
                raise ValueError("A mesa deve ter 3, 4 ou 5 cartas (ou ficar vazia).")
            jogadores = [mao] + [self._range_adversario()] * self.sp_adv.value()
            simular(jogadores, board=board, iteracoes=1, semente=0)  # valida as entradas
        except (ValueError, RuntimeError) as e:
            QMessageBox.warning(self, "Entrada invalida", f"Verifique os campos.\n\n{e}\n\n"
                                "Exemplo de mao: AS KD (As de espadas, Rei de ouros).")
            return
        self.trabalho = Trabalhador(jogadores, board, self.sp_iter.value(), self.sp_semente.value())
        self.trabalho.progresso.connect(self.atualizar)
        self.trabalho.terminou.connect(self.concluir)
        self.trabalho.falhou.connect(lambda m: (QMessageBox.critical(self, "Erro na simulacao", m), self._botoes(False)))
        self.barra.setMaximum(self.sp_iter.value())
        self.barra.setValue(0)
        self._botoes(True)
        self.trabalho.start()

    def pausar(self):
        if not self.trabalho:
            return
        self.trabalho.pausado = not self.trabalho.pausado
        self.bt_pausar.setText("Continuar" if self.trabalho.pausado else "Pausar")
        self.statusBar().showMessage("Simulacao pausada" if self.trabalho.pausado else "Simulando...")

    def parar(self):
        if self.trabalho:
            self.trabalho.parar = True
            self.trabalho.pausado = False

    def _botoes(self, rodando):
        self.bt_iniciar.setEnabled(not rodando)
        self.bt_pausar.setEnabled(rodando)
        self.bt_parar.setEnabled(rodando)
        self.bt_pausar.setText("Pausar")

    def atualizar(self, r):
        self.barra.setValue(r.iteracoes)
        self.resultado = r
        self.lb_resultado.setText(self._texto(r))

    def concluir(self, r, interrompido):
        self._botoes(False)
        if r.iteracoes:
            self.atualizar(r)
        self.statusBar().showMessage(f"Simulacao {'interrompida' if interrompido else 'concluida'}: "
                                     f"{r.iteracoes} iteracoes")

    def _texto(self, r):
        bb = self.mesa.big_blind
        rake = ESTRUTURAS_RAKE_HIPOTETICAS[self.cb_rake.currentData()]
        pote, call = self.sp_pote.value() * bb, self.sp_call.value() * bb
        eq = r.equity()
        linhas = [f"<b>Equity: {eq:.1%}</b> (± {2 * r.erro_padrao():.1%} com 95% de confianca)",
                  f"Vitoria: {r.prob_vitoria():.1%} · Empate: {r.prob_empate():.1%} · Iteracoes: {r.iteracoes}"]
        pos = self.cb_pos.currentText()
        try:
            c1, c2 = _parse_cartas(self.ed_mao.text())
            classe = classe_da_mao(c1, c2)
            if pos in self.ranges_pos:
                dentro = self.ranges_pos[pos].contem(c1, c2)
                linhas.append(f"Posicao {pos}: {classe} {'ESTA' if dentro else 'NAO esta'} no range de abertura "
                              f"({self.perfil['ranges_abertura_pct'][pos]}% das maos, tabela do desenvolvedor)")
            else:
                linhas.append(f"Posicao {pos}: o BB nao abre o pote (so defende); sem range de abertura.")
        except ValueError:
            pass
        if call > 0:
            necessaria = equity_necessaria(pote, call, rake)
            ev = ev_call(eq, pote, call, rake)
            linhas += ["", f"Odds do pote: {odds_do_pote(pote, call):.1%} · Equity necessaria com rake: {necessaria:.1%}",
                       f"EV do call: <b>{ev / bb:+.2f} BB</b> (R$ {ev:+.2f}) → "
                       + ("<span style='color:green'>lucrativo no longo prazo</span>" if ev > 0
                          else "<span style='color:#b00'>nao lucrativo</span>")]
        if self.sp_adv.value() == 1:
            a = ev_call_allin(eq, self.sp_stack_h.value() * bb, self.sp_stack_v.value() * bb,
                              rake=rake, mesa=self.mesa)
            linhas += ["", f"All-in heads-up: stack efetivo {a.stack_efetivo / bb:.0f} BB · rake {a.rake / bb:.2f} BB · "
                           f"equity necessaria {a.equity_necessaria:.1%} · EV <b>{a.ev_bb:+.1f} BB</b>"]
        else:
            linhas += ["", f"Multiway com {self.sp_adv.value()} adversarios: EV all-in nao calculado (so heads-up)."]
        linhas += ["", "<i>Estudo teorico offline. Nao e recomendacao de aposta.</i>"]
        return "<br>".join(linhas)

    # ------------------------------------------------------------------ aba relatorios
    def _aba_relatorios(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.cb_rel = QComboBox()
        self.cb_rel.addItems(RELATORIOS)
        self.cb_rel.currentTextChanged.connect(self._abrir_relatorio)
        self.tx_rel = QTextBrowser()
        self.tx_rel.setOpenExternalLinks(False)
        v.addWidget(self.cb_rel)
        v.addWidget(self.tx_rel)
        self._abrir_relatorio(self.cb_rel.currentText())
        return w

    def _abrir_relatorio(self, nome):
        caminho = os.path.join(RAIZ, RELATORIOS[nome])
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                self.tx_rel.setMarkdown(f.read())
        else:
            self.tx_rel.setPlainText(f"Arquivo nao encontrado: {caminho}")

    # ------------------------------------------------------------------ aba testes
    def _aba_testes(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Executa os testes automaticos offline (cerca de 1 minuto). Nada e enviado pela internet."))
        self.bt_testes = QPushButton("Rodar testes offline")
        self.bt_testes.clicked.connect(self._rodar_testes)
        self.tx_testes = QPlainTextEdit()
        self.tx_testes.setReadOnly(True)
        v.addWidget(self.bt_testes)
        v.addWidget(self.tx_testes)
        self.proc = None
        return w

    def _rodar_testes(self):
        self.tx_testes.clear()
        self.bt_testes.setEnabled(False)
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(RAIZ)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(
            lambda: self.tx_testes.appendPlainText(bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")))
        self.proc.finished.connect(self._fim_testes)
        python = sys.executable.replace("pythonw.exe", "python.exe")
        self.proc.start(python, ["-m", "simulador.testes", "offline"])

    def _fim_testes(self, codigo, _status):
        self.bt_testes.setEnabled(True)
        self.tx_testes.appendPlainText("\nRESULTADO: " + ("TODOS OS TESTES PASSARAM" if codigo == 0
                                                          else f"HA FALHAS (codigo {codigo}) - veja acima"))


def main():
    app = QApplication(sys.argv)
    j = Janela()
    j.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
