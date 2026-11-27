"""Executor de testes por categoria.

Uso (na pasta do projeto):
    .venv\\Scripts\\python.exe -m simulador.testes listar
    .venv\\Scripts\\python.exe -m simulador.testes offline            # rapido (~1 min)
    .venv\\Scripts\\python.exe -m simulador.testes offline-completo   # inclui testes exaustivos (~4 min)
    .venv\\Scripts\\python.exe -m simulador.testes rede --confirmar    # SO LEITURA do servidor do autor
    .venv\\Scripts\\python.exe -m simulador.testes treino --confirmar  # treino de rede neural (> 25 min)
    (acrescente --incluir-falhas-conhecidas para tambem rodar o teste original desatualizado)

Categorias:
- offline: simulador/tests + testes originais que nao usam rede (test_outs, test_montecarlo).
- rede: testes originais que BAIXAM dados do servidor do autor (nao enviam).
- desativados: marcados com skip pelo autor (apenas listados).
- treino: treinamento de rede neural (longo).
- proibido: testes que ENVIAM dados ao servidor externo. Este executor se recusa a roda-los.
"""

import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = "poker/tests/"

CATEGORIAS = {
    "offline": {
        "descricao": "Unitarios offline (rede bloqueada no simulador)",
        "alvos": ["simulador/tests", T + "test_outs.py", T + "test_montecarlo.py"],
        "extra": ["-m", "not lento"],
    },
    "offline-completo": {
        "descricao": "Offline incluindo testes exaustivos (contagem de 2,6 mi de maos, AA x KK exato)",
        "alvos": ["simulador/tests", T + "test_outs.py", T + "test_montecarlo.py"],
        "extra": [],
    },
    "rede": {
        "descricao": "Dependentes de rede, SOMENTE leitura (baixam mapas de mesa e pesos)",
        "alvos": [T + "test_table_and_ocr.py", T + "test_tensorflow.py::test_load_nn_model"],
        "extra": [],
        "confirmar": True,
    },
    "treino": {
        "descricao": "Treinamento de rede neural de cartas (CPU, mais de 25 min; baixa dados do servidor)",
        "alvos": [T + "test_tensorflow.py::test_train_card_neural_network_and_predict"],
        "extra": [],
        "confirmar": True,
    },
}

DESATIVADOS = {
    T + "test_decision.py": "14 testes com @pytest.mark.skip(reason='Fix access issues') — dependem do servidor",
    T + "test_reverseTables.py": "1 teste com @pytest.mark.skip() — depende do servidor",
    T + "test_tableScreenBased.py": "arquivo sem testes",
}

PROIBIDOS = {
    T + "test_tensorflow.py::test_save_model": "ENVIA um modelo para o servidor do autor (save_model_to_db)",
}

FALHAS_CONHECIDAS = {
    # test_monteCarlo foi corrigido na Fase 3 (argumento maxRuns -> max_runs) e voltou a passar.
}


def listar():
    print("CATEGORIAS EXECUTAVEIS")
    for nome, c in CATEGORIAS.items():
        aviso = " (exige --confirmar)" if c.get("confirmar") else ""
        print(f"  {nome:17s} {c['descricao']}{aviso}")
        for a in c["alvos"]:
            print(f"      - {a}")
    print("\nDESATIVADOS PELO AUTOR (nao executados)")
    for a, m in DESATIVADOS.items():
        print(f"  - {a}: {m}")
    print("\nPROIBIDOS (nunca executados por este script)")
    for a, m in PROIBIDOS.items():
        print(f"  - {a}: {m}")
    print("\nFALHAS CONHECIDAS (nao causadas pelo ambiente)")
    for a, m in FALHAS_CONHECIDAS.items():
        print(f"  - {a}: {m}")


def executar(nome, confirmado=False, incluir_falhas=False):
    c = CATEGORIAS[nome]
    if c.get("confirmar") and not confirmado:
        print(f"A categoria '{nome}' acessa o servidor externo ou demora muito. Rode novamente com --confirmar.")
        return 2
    cmd = [sys.executable, "-m", "pytest", *c["alvos"], *c["extra"], "-p", "no:cacheprovider",
           "-o", "log_cli=false", "-W", "ignore::DeprecationWarning", "-q", "-rfEs"]
    for proibido in PROIBIDOS:
        cmd += ["--deselect", proibido]
    if not incluir_falhas:
        for falha, motivo in FALHAS_CONHECIDAS.items():
            print(f"Aviso: ignorando falha conhecida {falha} ({motivo}). Use --incluir-falhas-conhecidas para roda-la.")
            cmd += ["--deselect", falha]
    env = dict(os.environ, PYTHONPATH=RAIZ)
    print("Executando:", " ".join(cmd[1:]))
    return subprocess.call(cmd, cwd=RAIZ, env=env)


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "listar"):
        listar()
        return 0
    nome = argv[0]
    if nome not in CATEGORIAS:
        print(f"Categoria desconhecida: {nome}")
        listar()
        return 2
    return executar(nome, confirmado="--confirmar" in argv,
                    incluir_falhas="--incluir-falhas-conhecidas" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
