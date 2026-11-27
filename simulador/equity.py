"""Calculo de equity por Monte Carlo (reprodutivel) e por enumeracao exata.

Correcoes em relacao ao motor original (que permanece intacto como referencia):
1. Empates: cada jogador empatado recebe a fracao 1/k do pote (k = empatados),
   em vez de o robo "vencer" todos os empates.
2. Ranges: a mao de cada adversario e sorteada uniformemente entre as combinacoes
   do range compativeis com as cartas ja conhecidas (amostragem conjunta por
   rejeicao). Nenhuma mao fora do range e entregue.
3. Numero de jogadores: o chamador informa exatamente quantos adversarios ha
   (1 a 5 em 6-max); nao ha limite artificial nem "heads-up forcado" no pre-flop.
4. Reprodutibilidade: gerador aleatorio proprio com semente.

Cada jogador pode ser:
- lista de 2 cartas (mao conhecida);
- um Range (mao sorteada dentro do range);
- None (mao totalmente aleatoria).
"""

import math
import random
from dataclasses import dataclass, field
from itertools import combinations

from .avaliador import avaliar
from .cartas import cartas as _parse
from .ranges import Range

MAX_REJEICOES = 100_000


@dataclass
class ResultadoJogador:
    vitorias: int = 0          # venceu sozinho
    empates: int = 0           # dividiu o pote
    participacao: float = 0.0  # soma das fracoes de pote ganhas
    soma_quadrados: float = 0.0


@dataclass
class Resultado:
    iteracoes: int
    jogadores: list = field(default_factory=list)
    exato: bool = False

    def equity(self, i=0) -> float:
        """Fracao esperada do pote (vitorias + parte dos empates)."""
        return self.jogadores[i].participacao / self.iteracoes

    def prob_vitoria(self, i=0) -> float:
        return self.jogadores[i].vitorias / self.iteracoes

    def prob_empate(self, i=0) -> float:
        return self.jogadores[i].empates / self.iteracoes

    def erro_padrao(self, i=0) -> float:
        """Erro padrao da estimativa de equity (0 se exato)."""
        if self.exato or self.iteracoes < 2:
            return 0.0
        n = self.iteracoes
        media = self.jogadores[i].participacao / n
        var = max(self.jogadores[i].soma_quadrados / n - media ** 2, 0.0) * n / (n - 1)
        return math.sqrt(var / n)

    def resumo(self, i=0) -> str:
        return (f"equity={self.equity(i):.4f} vitoria={self.prob_vitoria(i):.4f} "
                f"empate={self.prob_empate(i):.4f} erro_padrao={self.erro_padrao(i):.4f} "
                f"n={self.iteracoes}{' (exato)' if self.exato else ''}")


def _normalizar(jogadores, board):
    fixos, specs = [], []
    for j in jogadores:
        if j is None or isinstance(j, Range):
            specs.append(j)
        else:
            mao = _parse(j) if isinstance(j, str) else list(j)
            if len(mao) != 2:
                raise ValueError("Mao conhecida deve ter 2 cartas")
            specs.append(mao)
            fixos.extend(mao)
    board = _parse(board) if isinstance(board, str) else list(board or [])
    conhecidas = fixos + board
    if len(set(conhecidas)) != len(conhecidas):
        raise ValueError("Cartas repetidas entre maos e board")
    if len(board) > 5:
        raise ValueError("Board com mais de 5 cartas")
    if not 2 <= len(specs) <= 10:
        raise ValueError("Use de 2 a 10 jogadores")
    return specs, board, set(conhecidas)


def _registrar(res, valores):
    melhor = max(valores)
    vencedores = [i for i, v in enumerate(valores) if v == melhor]
    parte = 1.0 / len(vencedores)
    for i in range(len(valores)):
        r = res.jogadores[i]
        if i in vencedores:
            if len(vencedores) == 1:
                r.vitorias += 1
            else:
                r.empates += 1
            r.participacao += parte
            r.soma_quadrados += parte * parte


def distribuir(specs, board, conhecidas, rng):
    """Uma distribuicao valida: (maos, board_completo). Exposta para testes de unicidade."""
    usadas = set(conhecidas)
    maos = [None] * len(specs)
    # 1) jogadores com range: amostragem conjunta por rejeicao (uniforme entre combinacoes validas)
    com_range = [i for i, s in enumerate(specs) if isinstance(s, Range)]
    if com_range:
        for _ in range(MAX_REJEICOES):
            escolha = [rng.choice(specs[i].combos) for i in com_range]
            cartas_escolhidas = [c for cb in escolha for c in cb]
            if len(set(cartas_escolhidas)) == len(cartas_escolhidas) and not usadas.intersection(cartas_escolhidas):
                break
        else:
            raise RuntimeError("Ranges incompativeis com as cartas conhecidas")
        for i, cb in zip(com_range, escolha):
            maos[i] = list(cb)
            usadas.update(cb)
    # 2) maos conhecidas
    for i, s in enumerate(specs):
        if isinstance(s, list):
            maos[i] = s
    # 3) maos aleatorias e board, tirados do baralho restante
    restante = [c for c in range(52) if c not in usadas]
    faltam_aleatorios = sum(1 for s in specs if s is None)
    faltam_board = 5 - len(board)
    sorteio = rng.sample(restante, 2 * faltam_aleatorios + faltam_board)
    k = 0
    for i, s in enumerate(specs):
        if s is None:
            maos[i] = sorteio[k:k + 2]
            k += 2
    return maos, list(board) + sorteio[k:]


def simular(jogadores, board=None, iteracoes=20000, semente=None) -> Resultado:
    """Equity por Monte Carlo. Jogador 0 costuma ser o heroi."""
    specs, board, conhecidas = _normalizar(jogadores, board)
    rng = random.Random(semente)
    res = Resultado(iteracoes=iteracoes, jogadores=[ResultadoJogador() for _ in specs])
    for _ in range(iteracoes):
        maos, board_final = distribuir(specs, board, conhecidas, rng)
        _registrar(res, [avaliar(m + board_final) for m in maos])
    return res


def enumerar(jogadores, board=None) -> Resultado:
    """Equity exata, enumerando todos os boards possiveis (apenas maos conhecidas)."""
    specs, board, conhecidas = _normalizar(jogadores, board)
    if any(not isinstance(s, list) for s in specs):
        raise ValueError("Enumeracao exata exige todas as maos conhecidas")
    restante = [c for c in range(52) if c not in conhecidas]
    res = Resultado(iteracoes=0, jogadores=[ResultadoJogador() for _ in specs], exato=True)
    for complemento in combinations(restante, 5 - len(board)):
        b = board + list(complemento)
        _registrar(res, [avaliar(m + b) for m in specs])
        res.iteracoes += 1
    return res
