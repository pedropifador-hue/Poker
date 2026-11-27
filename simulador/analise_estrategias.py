"""Comparacao offline das estrategias Trial 2 e Official 1 no cenario 6-max 0,05/0,10.

Reproduz as regras do robo (decisionmaker.py) usando a MESMA funcao de curva do projeto
(poker/decisionmaker/curvefitting.py, importada so como referencia) e o simulador
validado para as equities. A rede fica bloqueada. Nenhuma estrategia e alterada:
os parametros vem de auditoria/estrategias_snapshot.json.

Executar:  .venv\\Scripts\\python.exe -m simulador.analise_estrategias
Gera:      auditoria/fase3_estrategias.md e simulador/perfis/tag_6max_nl10.json
"""

import datetime
import json
import logging
import math
import os
import random
import sys
import warnings

import numpy as np

from .cartas import classe_da_mao
from .cenario import ESTRUTURAS_RAKE_HIPOTETICAS, MESA_REFERENCIA, equity_necessaria, odds_do_pote
from .equity import simular, distribuir, _normalizar
from .estrategias import POSICOES, PERFIL_PADRAO, ranges_de_abertura_do_autor
from .ranges import COMBOS_POR_CLASSE, Range
from .seguranca import rede_bloqueada

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(RAIZ, "auditoria", "estrategias_snapshot.json")
CACHE = os.path.join(RAIZ, "auditoria", "cache_equity_preflop.json")
SAIDA = os.path.join(RAIZ, "auditoria", "fase3_estrategias.md")
CLASSES = sorted(COMBOS_POR_CLASSE)
CENARIOS = {"mesa 0,01/0,02 (calibrada)": 0.02, "mesa 0,05/0,10 (cenario)": 0.10}
logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")


def _curva(eqs, min_eq, max_eq, topo, power, bb_estrategia, max_x):
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    from poker.decisionmaker.curvefitting import Curvefitting  # pylint: disable=import-outside-toplevel
    return Curvefitting(np.array(eqs), 0, 2 * bb_estrategia, topo, min_eq, max_eq, max_x, int(power)).y


def _pct(classes):
    return 100 * sum(len(COMBOS_POR_CLASSE[c]) for c in classes) / 1326


# ------------------------------------------------------------------ equities pre-flop (como o robo enxerga)

def equity_preflop_por_classe(faixa_vilao, iteracoes=1500, semente=1):
    """{classe: {'robo': vitoria+empate, 'real': equity com empates divididos}} heads-up contra faixa_vilao."""
    tabela = {}
    for i, c in enumerate(CLASSES):
        mao = list(COMBOS_POR_CLASSE[c][0])
        r = simular([mao, faixa_vilao], iteracoes=iteracoes, semente=semente + i)
        tabela[c] = {"robo": r.prob_vitoria() + r.prob_empate(), "real": r.equity()}
    return tabela


def _cache_equities(fracoes):
    dados = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            dados = json.load(f)
    mudou = False
    for fr in fracoes:
        chave = f"top{fr:.2f}_classes"
        if chave not in dados:
            dados[chave] = equity_preflop_por_classe(Range.top(fr, modo="classes"))
            mudou = True
    if mudou:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=1)
    return dados


# ------------------------------------------------------------------ regras pre-flop do robo (pote nao aberto)

def acoes_preflop(s, eq_por_classe, bb_mesa):
    """Para cada posicao: classes que o robo aumenta / paga (limp) com a estrategia s."""
    bb = float(s["bigBlind"])
    eqs = [eq_por_classe[c]["robo"] for c in CLASSES]
    pote = 1.5 * bb_mesa
    adj_call = min(pote / bb / 250 * s["potAdjustmentPreFlop"], s["maxPotAdjustmentPreFlop"])
    adj_bet = min(pote / bb / 250 * s["potAdjustment"], s["maxPotAdjustment"])  # o codigo usa potAdjustment aqui
    resultado = {}
    for p, pos in enumerate(POSICOES[:5]):
        red = s["pre_flop_equity_reduction_by_position"] * p
        lim_call = _curva(eqs, s["PreFlopMinCallEquity"] - adj_call - red, 1, s["initialFunds"],
                          s["PreFlopCallPower"], bb, 0.95)
        lim_bet = _curva(eqs, s["PreFlopMinBetEquity"] - adj_bet - red, s["PreFlopMaxBetEquity"], s["initialFunds2"],
                         s["PreFlopBetPower"], bb, 0.95)
        min_call = (0.5 if pos == "SB" else 1.0) * bb_mesa
        min_bet = 2 * bb_mesa
        aumenta, paga = [], []
        for c, e, lc, lb in zip(CLASSES, eqs, lim_call, lim_bet):
            if lb > min_bet:
                aumenta.append(c)
            elif lc >= min_call or e >= s["alwaysCallEquity"]:
                paga.append(c)
        resultado[pos] = (aumenta, paga)
    return resultado


# ------------------------------------------------------------------ flop (heads-up, robo foi o agressor)

def amostras_flop(range_heroi, range_vilao, amostras=500, iteracoes=300, semente=7):
    rng = random.Random(semente)
    specs, board, conhecidas = _normalizar([range_heroi, range_vilao], [])
    saida = []
    for k in range(amostras):
        maos, b = distribuir(specs, board, conhecidas, rng)
        r = simular([maos[0], range_vilao], board=b[:3], iteracoes=iteracoes, semente=semente * 1000 + k)
        saida.append(r.prob_vitoria() + r.prob_empate())  # equity como o robo calcula
    return saida


def acoes_flop(s, eqs, bb_mesa):
    bb = float(s["bigBlind"])
    lim_bet = _curva(eqs, s["FlopMinBetEquity"], 1, s["initialFunds2"], s["FlopBetPower"], bb, 1)
    lim_call = _curva(eqs, s["FlopMinCallEquity"], 1, s["initialFunds"], s["FlopCallPower"], bb, 1)
    aposta_valor = blefe = check = 0
    paga = 0
    pote, aposta = 5.0 * bb_mesa, 2.5 * bb_mesa  # pote apos raise/call; aposta de meio pote do vilao
    for e, lb, lc in zip(eqs, lim_bet, lim_call):
        aposta = lb >= 2 * bb_mesa
        if aposta and e > s["FlopCheckDeceptionMinEquity"]:
            aposta = False  # check deception
        if aposta:
            aposta_valor += 1
        elif s["FlopBluffMaxEquity"] > e > s["FlopBluffMinEquity"]:
            blefe += 1      # heads-up, 1a acao, flop_bluffing_condidion_1 = 0
        else:
            check += 1
        paga += (lc >= 2.5 * bb_mesa or e >= s["alwaysCallEquity"])
    n = len(eqs)
    return {"aposta_valor": aposta_valor / n, "blefe": blefe / n, "check": check / n, "paga_meio_pote": paga / n}


# ------------------------------------------------------------------ relatorio

def gerar(rapido=False):
    with open(SNAPSHOT, encoding="utf-8") as f:
        snap = json.load(f)
    estrategias = {"Trial 2": snap["Trial 2"], "Official 1": snap["Official 1"]}
    autor = ranges_de_abertura_do_autor()
    eqs = _cache_equities(sorted({float(s["range_preflop"]) for s in estrategias.values()}))
    L = ["# Fase 3 — Estrategias em simulacao offline (6-max, 0,05/0,10, 200 BB)", "",
         f"Gerado por `python -m simulador.analise_estrategias` em {datetime.date.today():%d/%m/%Y}, com rede bloqueada. "
         "As regras do robo foram reproduzidas com a funcao de curva original; as equities vem do simulador validado. "
         "Nenhuma estrategia foi alterada.", ""]

    # 1. pre-flop
    L += ["## 1. Pre-flop: o que cada estrategia faz em pote nao aberto", "",
          "% das 1326 combinacoes. *Tabela do autor* = `preflop.xlsx` (usada so com `preflop_override = 1`).", "",
          "| Posicao | Tabela do autor (aumenta com freq. > 0) | " + " | ".join(
              f"{n} · {c.split(' (')[0]}" for n in estrategias for c in CENARIOS) + " |",
          "|---|---|" + "---|" * (len(estrategias) * len(CENARIOS))]
    acoes = {}
    for n, s in estrategias.items():
        tab = eqs[f"top{float(s['range_preflop']):.2f}_classes"]
        for c, bbm in CENARIOS.items():
            acoes[(n, c)] = acoes_preflop(s, tab, bbm)
    for pos in POSICOES[:5]:
        celulas = [f"{_pct(autor[pos].classes):.1f}%"]
        for n in estrategias:
            for c in CENARIOS:
                a, p = acoes[(n, c)][pos]
                celulas.append(f"aumenta {_pct(a):.1f}% · limp {_pct(p):.1f}%")
        L.append(f"| {pos} | " + " | ".join(celulas) + " |")
    L.append("")
    for n, s in estrategias.items():
        tab = eqs["top%.2f_classes" % float(s["range_preflop"])]
        a, p = acoes[(n, list(CENARIOS)[0])]["BTN"]
        premium = [c for c in ("AA", "KK", "QQ", "AKS", "AKO") if c in p]
        melhores = ", ".join(sorted(a, key=lambda c: -tab[c]["robo"])[:8]) or "nenhuma"
        L.append(f"- **{n}** no BTN (escala calibrada): aumenta {melhores}…; "
                 f"premium que so pagam (limp): {', '.join(premium) or 'nenhuma'}.")
    cal = list(CENARIOS)[0]
    faixas = "; ".join(
        f"{n}: {_pct(acoes[(n, cal)]['UTG'][0]):.1f}% (UTG) a {_pct(acoes[(n, cal)]['SB'][0]):.1f}% (SB)"
        for n in estrategias)
    L += ["", "Leitura: no modo de equity (`preflop_override = 0`) a posicao so entra como uma reducao linear da "
          "equity minima (`pre_flop_equity_reduction_by_position` por posicao apos o UTG). O range de aumento cresce "
          f"menos que na tabela do autor ({_pct(autor['UTG'].classes):.1f}% a {_pct(autor['SB'].classes):.1f}%): "
          f"{faixas}. Na mesa 0,05/0,10, sem reescalar `bigBlind`, os custos ficam 5x maiores para a curva "
          "e o robo fica muito mais fechado.", ""]

    # 2. flop
    heroi = autor["BTN"]
    amostras = amostras_flop(heroi, Range.top(0.4, modo="classes"), amostras=150 if rapido else 500)
    L += ["## 2. Flop heads-up como agressor (heroi com range de BTN do autor; vilao top 40%)", "",
          "| Estrategia · mesa | Aposta por valor | Blefe | Check | Paga aposta de meio pote |", "|---|---|---|---|---|"]
    for n, s in estrategias.items():
        for c, bbm in CENARIOS.items():
            f = acoes_flop(s, amostras, bbm)
            L.append(f"| {n} · {c} | {f['aposta_valor']:.0%} | {f['blefe']:.0%} | {f['check']:.0%} | {f['paga_meio_pote']:.0%} |")
    L += ["", "Aposta total = valor + blefe (o blefe usa uma faixa de equity fixa, sem considerar a textura do board). "
          "Equities altas acima de `FlopCheckDeceptionMinEquity` (0,85) viram check.", ""]

    # 3. adversarios e multiway
    L += ["## 3. Quantidade de adversarios (equity real, simulador)", "",
          "| Mao | 1 adv. | 2 adv. | 3 adv. | 4 adv. | 5 adv. | O robo usa no pre-flop |", "|---|---|---|---|---|---|---|"]
    for mao in ("AS AH", "AS KS", "JS TS", "7S 7H"):
        vals = [simular([mao] + [None] * k, iteracoes=3000 if rapido else 8000, semente=50 + k).equity() for k in range(1, 6)]
        L.append(f"| {mao} | " + " | ".join(f"{v:.3f}" for v in vals) + f" | {vals[0]:.3f} (sempre heads-up) |")
    L.append("")

    # 4. rake e stacks
    rake = ESTRUTURAS_RAKE_HIPOTETICAS["5%_teto_3bb"]
    bb = MESA_REFERENCIA.big_blind
    L += ["## 4. Rake hipotetico e profundidade de stack (o robo nao considera nenhum dos dois)", "",
          "| Situacao (valores em R$) | Odds do pote | Equity necessaria sem rake | Com rake 5% teto 3 BB |", "|---|---|---|---|"]
    for desc, pote, call in [("BB defende contra abertura de 2,5 BB do BTN", 3.5 * bb, 1.5 * bb),
                             ("Paga aposta de meio pote no flop (pote 6 BB)", 9 * bb, 3 * bb),
                             ("Paga all-in de 100 BB (pote 101,5 BB)", 101.5 * bb, 100 * bb),
                             ("Paga all-in de 200 BB (pote 201,5 BB)", 201.5 * bb, 200 * bb)]:
        L.append(f"| {desc} | {odds_do_pote(pote, call):.3f} | {equity_necessaria(pote, call):.3f} | "
                 f"{equity_necessaria(pote, call, rake):.3f} |")
    L += ["", "Em potes pequenos o rake pesa mais (o teto so e atingido a partir de 60 BB de pote). "
          "O robo usa limites absolutos (`initialFunds` = 23,83, `initialFunds2` = 3,40) sem relacao com o stack efetivo.", ""]

    # 5. iteracoes (convergencia) para o perfil
    alvo = 0.005
    se_hu = simular(["AS KD", Range.top(0.2)], iteracoes=4000, semente=3).erro_padrao()
    se_mw = simular(["AS KD", None, None, None, None, None], iteracoes=4000, semente=4).erro_padrao()
    n_hu = int(math.ceil(4000 * (se_hu / alvo) ** 2 / 1000) * 1000)
    n_mw = int(math.ceil(4000 * (se_mw / alvo) ** 2 / 1000) * 1000)
    L += ["## 5. Configuracao do ambiente de estudo (perfil gerado)", "",
          f"- Iteracoes para erro padrao ≤ {alvo}: heads-up ≈ {n_hu}, multiway (6 jogadores) ≈ {n_mw} "
          f"(medido: erro padrao {se_hu:.4f} e {se_mw:.4f} com 4.000 iteracoes).",
          "- Ranges de abertura por posicao: tabela do autor (`preflop.xlsx`), por ser posicional, ponderada por "
          "combinacoes e proxima dos valores tipicos de TAG 6-max.",
          "- Rake padrao: hipotetico 5% com teto de 3 BB; stacks de 1 a 200 BB.", ""]

    perfil = {
        "nome": "TAG 6-max NL10 (estudo offline)",
        "gerado_em": f"{datetime.date.today():%Y-%m-%d}",
        "origem": "simulador.analise_estrategias (dados locais, rede bloqueada)",
        "mesa": {"small_blind": 0.05, "big_blind": 0.10, "max_jogadores": 6, "stack_max_bb": 200},
        "rake_padrao": "5%_teto_3bb",
        "stack_padrao_bb": 100,
        "iteracoes": {"heads_up": max(n_hu, 5000), "multiway": max(n_mw, 5000)},
        "semente": 2026,
        "ranges_abertura": {pos: sorted(r.classes) for pos, r in autor.items()},
        "ranges_abertura_pct": {pos: round(_pct(r.classes), 1) for pos, r in autor.items()},
        "observacao": "Perfil do ambiente de estudo. Nao altera nenhuma estrategia do robo.",
    }
    os.makedirs(os.path.dirname(PERFIL_PADRAO), exist_ok=True)
    with open(PERFIL_PADRAO, "w", encoding="utf-8") as f:
        json.dump(perfil, f, indent=2, ensure_ascii=False)
    return "\n".join(L)


def main():
    with rede_bloqueada():
        texto = gerar(rapido="--rapido" in sys.argv)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    print(texto)
    print(f"\nRelatorio: {SAIDA}\nPerfil: {PERFIL_PADRAO}")


if __name__ == "__main__":
    main()
