"""Representacao de cartas e baralho.

Cada carta e um inteiro de 0 a 51: rank = carta // 4 (0 = 2 ... 12 = As),
naipe = carta % 4. A notacao texto segue o padrao do projeto original:
rank em '23456789TJQKA' + naipe em 'CDHS' (ex.: 'AS' = As de espadas).
"""

RANKS = "23456789TJQKA"
NAIPES = "CDHS"
BARALHO = tuple(range(52))


def carta(texto: str) -> int:
    """Converte 'AS' / 'Th' / '2c' em inteiro."""
    texto = texto.strip()
    if len(texto) != 2:
        raise ValueError(f"Carta invalida: {texto!r}")
    r = RANKS.find(texto[0].upper())
    s = NAIPES.find(texto[1].upper())
    if r < 0 or s < 0:
        raise ValueError(f"Carta invalida: {texto!r}")
    return r * 4 + s


def cartas(textos) -> list:
    """Converte 'AS KD' ou ['AS', 'KD'] em lista de inteiros (sem repeticao)."""
    if isinstance(textos, str):
        textos = textos.replace(",", " ").split()
    lista = [carta(t) for t in textos]
    if len(set(lista)) != len(lista):
        raise ValueError(f"Cartas repetidas: {textos}")
    return lista


def texto(c: int) -> str:
    return RANKS[c // 4] + NAIPES[c % 4]


def textos(cs) -> list:
    return [texto(c) for c in cs]


def rank(c: int) -> int:
    return c // 4


def naipe(c: int) -> int:
    return c % 4


def classe_da_mao(c1: int, c2: int) -> str:
    """Classe de mao inicial no formato do projeto: 'AA', 'AKS', 'AKO'."""
    r1, r2 = rank(c1), rank(c2)
    if r1 < r2:
        r1, r2 = r2, r1
    if r1 == r2:
        return RANKS[r1] * 2
    return RANKS[r1] + RANKS[r2] + ("S" if naipe(c1) == naipe(c2) else "O")
