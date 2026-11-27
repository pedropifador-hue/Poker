"""Ranges de maos iniciais (169 classes / 1326 combinacoes).

Diferenca em relacao ao motor original:
- modo 'combos' (padrao, correto): o "top X%" e medido em COMBINACOES (1326),
  ponderando pares (6), suited (4) e offsuit (12);
- modo 'classes' (reproduz o original): o "top X%" e medido em CLASSES (169),
  sem ponderar combinacoes.

A ordem das classes usa a tabela local poker/decisionmaker/preflop_equity.json
(apenas leitura, nenhum acesso a rede). Tambem e possivel informar as classes manualmente.
"""

import json
import os
from itertools import combinations

from .cartas import RANKS, classe_da_mao

ARQUIVO_EQUITY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "poker", "decisionmaker", "preflop_equity.json")

TODAS_COMBOS = tuple(combinations(range(52), 2))  # 1326


def normalizar_classe(classe: str) -> str:
    """'KAS' -> 'AKS', 'aa' -> 'AA', '72o' -> '72O'."""
    c = classe.strip().upper()
    if len(c) == 2:
        a, b = c
        sufixo = ""
    elif len(c) == 3:
        a, b, sufixo = c
    else:
        raise ValueError(f"Classe invalida: {classe!r}")
    if RANKS.find(a) < RANKS.find(b):
        a, b = b, a
    if a == b:
        if sufixo not in ("", "O"):
            raise ValueError(f"Par nao pode ser suited: {classe!r}")
        return a + b
    if sufixo not in ("S", "O"):
        raise ValueError(f"Informe S ou O: {classe!r}")
    return a + b + sufixo


COMBOS_POR_CLASSE = {}
for _c1, _c2 in TODAS_COMBOS:
    COMBOS_POR_CLASSE.setdefault(classe_da_mao(_c1, _c2), []).append((_c1, _c2))


def ordem_das_classes(arquivo: str = ARQUIVO_EQUITY) -> list:
    """Classes da mais forte para a mais fraca, segundo a tabela de equity local."""
    with open(arquivo, encoding="utf-8") as f:
        tabela = json.load(f)
    normalizada = {normalizar_classe(k): v for k, v in tabela.items()}
    return sorted(normalizada, key=lambda k: -normalizada[k])


class Range:
    """Conjunto de combinacoes de duas cartas que um adversario pode ter."""

    def __init__(self, classes):
        self.classes = frozenset(normalizar_classe(c) for c in classes)
        self.combos = tuple(cb for c in sorted(self.classes) for cb in COMBOS_POR_CLASSE[c])
        if not self.combos:
            raise ValueError("Range vazio")

    @classmethod
    def top(cls, fracao: float, modo: str = "combos", ordem=None):
        """Top `fracao` (0 a 1) das maos. modo='combos' (correto) ou 'classes' (como o original)."""
        if not 0 < fracao <= 1:
            raise ValueError("fracao deve estar em (0, 1]")
        ordem = ordem or ordem_das_classes()
        escolhidas = []
        if modo == "classes":
            escolhidas = ordem[:int(len(ordem) * fracao)]  # mesma regra do original
        elif modo == "combos":
            alvo = fracao * len(TODAS_COMBOS)
            total = 0
            for c in ordem:
                if total >= alvo:
                    break
                escolhidas.append(c)
                total += len(COMBOS_POR_CLASSE[c])
        else:
            raise ValueError("modo deve ser 'combos' ou 'classes'")
        return cls(escolhidas or ordem[:1])

    @classmethod
    def qualquer(cls):
        return cls(COMBOS_POR_CLASSE.keys())

    @property
    def fracao_combos(self) -> float:
        return len(self.combos) / len(TODAS_COMBOS)

    def contem(self, c1: int, c2: int) -> bool:
        return classe_da_mao(c1, c2) in self.classes

    def __repr__(self):
        return f"Range({len(self.classes)} classes, {len(self.combos)} combos, {self.fracao_combos:.1%})"
