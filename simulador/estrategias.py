"""Posicoes 6-max, ranges de abertura por posicao e perfil de estudo.

Fonte dos ranges por posicao: a tabela do proprio desenvolvedor
`poker/decisionmaker/preflop.xlsx` (planilhas '1' a '5' = UTG..SB sem ninguem
ter entrado no pote). Essa tabela so e usada pelo robo quando `preflop_override = 1`
(na Trial 2 e na Official 1 esta desligado). Aqui ela e lida apenas como dado local.

Mapeamento de posicoes conferido no codigo original (table_screen_based.py:396):
position_utg_plus = (total_players + 3 - dealer_position) % total_players
=> 0 UTG, 1 HJ, 2 CO, 3 BTN, 4 SB, 5 BB (mesa 6-max).
"""

import json
import os

from .ranges import Range, normalizar_classe

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_PREFLOP = os.path.join(RAIZ, "poker", "decisionmaker", "preflop.xlsx")
PASTA_PERFIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perfis")
PERFIL_PADRAO = os.path.join(PASTA_PERFIS, "tag_6max_nl10.json")

POSICOES = ("UTG", "HJ", "CO", "BTN", "SB", "BB")


def posicao_por_utg_plus(n: int) -> str:
    return POSICOES[n]


def utg_plus_por_posicao(nome: str) -> int:
    return POSICOES.index(nome.upper())


def tabela_preflop_do_autor(arquivo: str = ARQUIVO_PREFLOP, anomalias: list = None) -> dict:
    """{planilha: {classe: (call, raise, fold)}} lida do preflop.xlsx local.

    Linhas com mao mal formatada (ex.: 'A3' sem S/O) sao ignoradas e, se `anomalias`
    for uma lista, registradas nela como (planilha, texto). O robo original tambem
    nunca encontra essas linhas, pois compara com 'A3S'/'A3O'.
    """
    import pandas as pd  # pylint: disable=import-outside-toplevel
    planilhas = pd.read_excel(arquivo, sheet_name=None, engine="openpyxl")
    tabela = {}
    for nome, df in planilhas.items():
        if "Hand" not in df.columns:
            continue
        linhas = {}
        for h, c, r, f in zip(df["Hand"], df["Call"], df["Raise"], df["Fold"]):
            try:
                linhas[normalizar_classe(str(h))] = (float(c), float(r), float(f))
            except ValueError:
                if anomalias is not None:
                    anomalias.append((str(nome), str(h)))
        tabela[str(nome)] = linhas
    return tabela


def ranges_de_abertura_do_autor(arquivo: str = ARQUIVO_PREFLOP) -> dict:
    """{posicao: Range} com as maos que a tabela do autor manda AUMENTAR em pote nao aberto."""
    tabela = tabela_preflop_do_autor(arquivo)
    ranges = {}
    for i, pos in enumerate(POSICOES[:5]):
        maos = [c for c, (_, r, _) in tabela[str(i + 1)].items() if r > 0]
        ranges[pos] = Range(maos)
    return ranges


def carregar_perfil(caminho: str = PERFIL_PADRAO) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def ranges_do_perfil(perfil: dict) -> dict:
    return {pos: Range(classes) for pos, classes in perfil["ranges_abertura"].items()}
