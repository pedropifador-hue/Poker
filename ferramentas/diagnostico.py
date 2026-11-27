"""Diagnostico do ambiente do PokerBot (para usuarios leigos).

Uso:
    python ferramentas\\diagnostico.py                 -> relatorio completo (tambem salvo em diagnostico.txt)
    python ferramentas\\diagnostico.py --antes-de-abrir -> verificacao rapida usada por "Abrir Pokerbot.bat"

A verificacao do servidor apenas tenta abrir uma conexao TCP com o endereco
configurado em poker/config.ini (chave "db"). Nenhum dado e enviado.
"""

import configparser
import importlib.util
import os
import socket
import sys
from urllib.parse import urlparse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RAIZ, "poker", "config.ini")
LOG_ERROS = os.path.join(RAIZ, "poker", "log", "deepmind_pokerbot_errors.log")

PACOTES = ["PyQt6", "numpy", "pandas", "matplotlib", "cv2", "tesserocr", "tensorflow", "lmfit",
           "requests", "openpyxl", "win32api", "fastapi", "uvicorn"]


def servidor():
    """(host, porta, alcancavel, mensagem)."""
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(CONFIG, encoding="utf-8")
    url = cfg.get("main", "db", fallback="")
    alvo = urlparse(url)
    host, porta = alvo.hostname, alvo.port or (443 if alvo.scheme == "https" else 80)
    if not host:
        return None, None, False, "Endereco do servidor ausente em poker/config.ini"
    try:
        with socket.create_connection((host, porta), timeout=6):
            return host, porta, True, "ok"
    except OSError as e:
        return host, porta, False, str(e)


def verificacoes():
    itens = []
    versao = sys.version.split()[0]
    itens.append(("Python 3.11", versao.startswith("3.11"), f"versao em uso: {versao}"))
    for p in PACOTES:
        itens.append((f"Biblioteca {p}", importlib.util.find_spec(p) is not None, ""))
    itens.append(("Dados do OCR (tessdata)", os.path.exists(os.path.join(RAIZ, "tessdata", "eng.traineddata")), ""))
    itens.append(("Arquivo poker/config.ini", os.path.exists(CONFIG), ""))
    host, porta, ok, msg = servidor()
    itens.append((f"Servidor do autor ({host}:{porta})", ok,
                  "conectado" if ok else f"inacessivel: {msg}. O PokerBot original nao abre sem ele."))
    itens.append(controle_configurado())
    return itens


def controle_configurado():
    """O botao Start do robo usa o 'control' do config.ini: maquina virtual ou mouse real."""
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(CONFIG, encoding="utf-8")
    controle = cfg.get("main", "control", fallback="")
    if controle == "Direct mouse control":
        return ("Controle do mouse", True,
                "'Direct mouse control': ao apertar Start o robo move o mouse REAL desta tela")
    vbox = any(os.path.exists(os.path.join(p, "Oracle", "VirtualBox", "VBoxManage.exe"))
               for p in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                         os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")))
    if not vbox:
        return ("Controle do mouse", False,
                f"configurado para a maquina virtual '{controle}', mas o VirtualBox nao esta instalado. "
                "Ao apertar Start o robo apenas registra erros ('Library not registered'). "
                "Isso so muda se voce escolher outro controle em Setup.")
    return ("Controle do mouse", True, f"maquina virtual '{controle}' (VirtualBox encontrado)")


def ultimos_erros(n=15):
    if not os.path.exists(LOG_ERROS) or os.path.getsize(LOG_ERROS) == 0:
        return []
    with open(LOG_ERROS, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()[-n:]


def relatorio():
    linhas = ["DIAGNOSTICO DO POKERBOT", "=" * 60]
    for nome, ok, detalhe in verificacoes():
        linhas.append(f"[{'OK ' if ok else 'ERRO'}] {nome}" + (f" - {detalhe}" if detalhe else ""))
    erros = ultimos_erros()
    linhas += ["", "Ultimas linhas do log de erros (poker/log/deepmind_pokerbot_errors.log):"]
    linhas += erros or ["(nenhum erro registrado)"]
    return "\n".join(linhas)


def aviso_grafico(titulo, texto):
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox  # pylint: disable=import-outside-toplevel
        app = QApplication.instance() or QApplication(sys.argv)
        caixa = QMessageBox()
        caixa.setIcon(QMessageBox.Icon.Warning)
        caixa.setWindowTitle(titulo)
        caixa.setText(texto)
        caixa.exec()
        del app
    except Exception:  # pylint: disable=broad-except
        print(titulo + "\n" + texto)


def main(argv):
    if "--antes-de-abrir" in argv:
        host, porta, ok, msg = servidor()
        if ok:
            return 0
        aviso_grafico(
            "PokerBot - servidor indisponivel",
            "O PokerBot original precisa do servidor do desenvolvedor para abrir "
            f"({host}:{porta}), e ele nao respondeu agora.\n\n"
            "Possiveis causas: sem internet, firewall/antivirus bloqueando, ou o servidor do autor fora do ar.\n\n"
            "Tente novamente mais tarde. Enquanto isso, voce pode usar o 'Abrir Simulador.bat', "
            "que funciona totalmente offline.\n\n"
            f"Detalhe tecnico: {msg}")
        return 10
    texto = relatorio()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    print(texto)
    with open(os.path.join(RAIZ, "diagnostico.txt"), "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
