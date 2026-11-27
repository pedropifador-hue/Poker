"""Avaliador de maos de 5 a 7 cartas, escrito do zero (independente do motor original).

Retorna uma tupla comparavel: (categoria, desempates...). Tuplas maiores vencem;
tuplas iguais significam empate exato (pote dividido).

Categorias: 8 straight flush, 7 quadra, 6 full house, 5 flush, 4 sequencia,
3 trinca, 2 dois pares, 1 par, 0 carta alta.
"""

from .cartas import rank, naipe

CATEGORIAS = ("Carta alta", "Par", "Dois pares", "Trinca", "Sequencia",
              "Flush", "Full house", "Quadra", "Straight flush")


def _maior_sequencia(ranks_presentes: set):
    """Rank da carta mais alta da maior sequencia; None se nao houver. Inclui A-2-3-4-5."""
    for alto in range(12, 3, -1):
        if all((alto - i) in ranks_presentes for i in range(5)):
            return alto
    if {12, 0, 1, 2, 3} <= ranks_presentes:
        return 3  # roda (wheel): carta alta e o 5
    return None


def avaliar(cs) -> tuple:
    """Avalia a melhor mao de 5 cartas contida em 5, 6 ou 7 cartas."""
    if not 5 <= len(cs) <= 7:
        raise ValueError("avaliar() espera de 5 a 7 cartas")

    contagem = [0] * 13
    por_naipe = ([], [], [], [])
    for c in cs:
        r = rank(c)
        contagem[r] += 1
        por_naipe[naipe(c)].append(r)

    # Flush / straight flush (com 7 cartas so pode existir um naipe com >= 5)
    for lista in por_naipe:
        if len(lista) >= 5:
            alto_sf = _maior_sequencia(set(lista))
            if alto_sf is not None:
                return (8, alto_sf)
            flush = tuple(sorted(lista, reverse=True)[:5])
            break
    else:
        flush = None

    quadras = [r for r in range(12, -1, -1) if contagem[r] == 4]
    trincas = [r for r in range(12, -1, -1) if contagem[r] == 3]
    pares = [r for r in range(12, -1, -1) if contagem[r] == 2]

    if quadras:
        q = quadras[0]
        kicker = max(r for r in range(13) if contagem[r] and r != q)
        return (7, q, kicker)

    if trincas and (len(trincas) >= 2 or pares):
        t = trincas[0]
        par = max(([trincas[1]] if len(trincas) >= 2 else []) + pares[:1])
        return (6, t, par)

    if flush is not None:
        return (5,) + flush

    alto = _maior_sequencia({r for r in range(13) if contagem[r]})
    if alto is not None:
        return (4, alto)

    soltas = [r for r in range(12, -1, -1) if contagem[r] == 1]

    if trincas:
        t = trincas[0]
        return (3, t) + tuple(soltas[:2])

    if len(pares) >= 2:
        p1, p2 = pares[0], pares[1]
        kicker = max([r for r in range(13) if contagem[r] and r not in (p1, p2)])
        return (2, p1, p2, kicker)

    if pares:
        return (1, pares[0]) + tuple(soltas[:3])

    return (0,) + tuple(soltas[:5])


def categoria(valor: tuple) -> str:
    return CATEGORIAS[valor[0]]
