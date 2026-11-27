"""Cenario de estudo: NLHE cash 6-max, stacks efetivos e rake hipotetico.

Tudo aqui e calculo teorico sobre maos simuladas. Nao ha conexao com salas,
nao ha leitura de tela e nada e enviado para fora do computador.

Convencoes:
- valores em unidades monetarias (ex.: 0,10 = 1 BB);
- "equity" = fracao esperada do pote (vitorias + parte dos empates);
- EV de um call e medido em relacao a desistir (fold = 0), com o que ja foi
  investido considerado custo afundado.
"""

from dataclasses import dataclass
from typing import Optional

from .equity import simular


@dataclass(frozen=True)
class ConfigMesa:
    small_blind: float = 0.05
    big_blind: float = 0.10
    max_jogadores: int = 6
    stack_max_bb: float = 200

    @property
    def stack_max(self) -> float:
        return self.stack_max_bb * self.big_blind

    def em_bb(self, valor: float) -> float:
        return valor / self.big_blind

    def validar_stack(self, stack: float) -> float:
        if stack <= 0:
            raise ValueError("Stack deve ser positivo")
        if stack > self.stack_max + 1e-9:
            raise ValueError(f"Stack {stack:.2f} acima do maximo de {self.stack_max_bb:g} BB ({self.stack_max:.2f})")
        return stack

    def validar_jogadores(self, n: int) -> int:
        if not 2 <= n <= self.max_jogadores:
            raise ValueError(f"Mesa {self.max_jogadores}-max aceita de 2 a {self.max_jogadores} jogadores na mao")
        return n


MESA_REFERENCIA = ConfigMesa()  # 0,05/0,10 · 6-max · 200 BB


@dataclass(frozen=True)
class Rake:
    """Estrutura de rake HIPOTETICA para estudo (nao representa nenhuma sala real)."""
    percentual: float = 0.0
    teto: Optional[float] = None          # em unidades monetarias; None = sem teto
    sem_flop_sem_rake: bool = True        # "no flop, no drop"
    nome: str = "sem rake"

    def calcular(self, pote: float, viu_flop: bool = True) -> float:
        if pote <= 0 or self.percentual <= 0:
            return 0.0
        if self.sem_flop_sem_rake and not viu_flop:
            return 0.0
        valor = pote * self.percentual
        return min(valor, self.teto) if self.teto is not None else valor


ESTRUTURAS_RAKE_HIPOTETICAS = {
    "sem_rake": Rake(nome="sem rake"),
    "5%_teto_3bb": Rake(0.05, 0.30, nome="5% com teto de 3 BB"),
    "5%_teto_1bb": Rake(0.05, 0.10, nome="5% com teto de 1 BB"),
    "4,5%_sem_teto": Rake(0.045, None, nome="4,5% sem teto"),
    "10%_teto_5bb": Rake(0.10, 0.50, nome="10% com teto de 5 BB (estresse)"),
}


# ------------------------------------------------------------------ stacks

def stack_efetivo(heroi: float, *viloes: float) -> float:
    """Quanto o heroi pode efetivamente ganhar/perder: min(heroi, maior stack entre os viloes)."""
    if not viloes:
        raise ValueError("Informe ao menos um vilao")
    return min(heroi, max(viloes))


# ------------------------------------------------------------------ odds e EV

def odds_do_pote(pote: float, call: float) -> float:
    """Fracao do pote final que o call representa: call / (pote + call)."""
    return call / (pote + call)


def equity_necessaria(pote: float, call: float, rake: Rake = Rake(), viu_flop: bool = True) -> float:
    """Equity minima para o call ter EV >= 0, considerando o rake retirado do pote final."""
    final = pote + call
    return call / (final - rake.calcular(final, viu_flop))


def ev_call(equity: float, pote: float, call: float, rake: Rake = Rake(), viu_flop: bool = True) -> float:
    """EV (unidades monetarias) de pagar `call` para disputar `pote` (que ja inclui a aposta do vilao)."""
    final = pote + call
    return equity * (final - rake.calcular(final, viu_flop)) - call


@dataclass
class AllIn:
    stack_efetivo: float
    pote_final: float
    custo_call: float
    rake: float
    equity: float
    equity_necessaria: float
    ev: float
    ev_bb: float


def ev_call_allin(equity: float, stack_heroi: float, stack_vilao: float,
                  investido_heroi: float = 0.0, dinheiro_morto: float = 0.0,
                  rake: Rake = Rake(), viu_flop: bool = True,
                  mesa: ConfigMesa = MESA_REFERENCIA) -> AllIn:
    """Heroi decide pagar um all-in heads-up.

    stack_heroi/stack_vilao: stacks no inicio da mao (incluem o que ja foi investido).
    investido_heroi: quanto o heroi ja colocou no pote nesta mao (ex.: big blind).
    dinheiro_morto: fichas de jogadores que ja desistiram (ex.: small blind).
    O excedente do stack maior e devolvido, por isso so o stack efetivo esta em jogo.
    Um all-in pre-flop pago vai ate o showdown, logo o flop e visto (viu_flop=True).
    """
    mesa.validar_stack(stack_heroi)
    mesa.validar_stack(stack_vilao)
    efetivo = stack_efetivo(stack_heroi, stack_vilao)
    pote_final = 2 * efetivo + dinheiro_morto
    custo = efetivo - investido_heroi
    r = rake.calcular(pote_final, viu_flop)
    ev = equity * (pote_final - r) - custo
    return AllIn(stack_efetivo=efetivo, pote_final=pote_final, custo_call=custo, rake=r, equity=equity,
                 equity_necessaria=custo / (pote_final - r), ev=ev, ev_bb=mesa.em_bb(ev))


def estudar_allin(mao_heroi, vilao, stack_heroi: float, stack_vilao: float,
                  investido_heroi: float = 0.0, dinheiro_morto: float = 0.0,
                  rake: Rake = Rake(), board=None, iteracoes: int = 20000, semente: int = 0,
                  mesa: ConfigMesa = MESA_REFERENCIA):
    """Simula a equity (mao_heroi x vilao: mao, Range ou None) e calcula o EV do call all-in."""
    res = simular([mao_heroi, vilao], board=board, iteracoes=iteracoes, semente=semente)
    return ev_call_allin(res.equity(), stack_heroi, stack_vilao, investido_heroi, dinheiro_morto,
                         rake, True, mesa), res
