# Fase 3 — Estrategias em simulacao offline (6-max, 0,05/0,10, 200 BB)

Gerado por `python -m simulador.analise_estrategias` em 27/11/2026, com rede bloqueada. As regras do robo foram reproduzidas com a funcao de curva original; as equities vem do simulador validado. Nenhuma estrategia foi alterada.

## 1. Pre-flop: o que cada estrategia faz em pote nao aberto

% das 1326 combinacoes. *Tabela do autor* = `preflop.xlsx` (usada so com `preflop_override = 1`).

| Posicao | Tabela do autor (aumenta com freq. > 0) | Trial 2 · mesa 0,01/0,02 | Trial 2 · mesa 0,05/0,10 | Official 1 · mesa 0,01/0,02 | Official 1 · mesa 0,05/0,10 |
|---|---|---|---|---|---|
| UTG | 17.2% | aumenta 13.9% · limp 0.9% | aumenta 4.1% · limp 3.0% | aumenta 16.9% · limp 8.6% | aumenta 3.5% · limp 23.2% |
| HJ | 22.0% | aumenta 19.2% · limp 0.9% | aumenta 5.0% · limp 2.9% | aumenta 19.9% · limp 7.7% | aumenta 3.8% · limp 26.2% |
| CO | 28.8% | aumenta 23.5% · limp 0.9% | aumenta 6.9% · limp 2.0% | aumenta 25.5% · limp 5.4% | aumenta 5.6% · limp 27.8% |
| BTN | 40.3% | aumenta 27.1% · limp 0.9% | aumenta 6.9% · limp 5.4% | aumenta 27.6% · limp 6.0% | aumenta 7.2% · limp 28.5% |
| SB | 62.3% | aumenta 30.2% · limp 0.9% | aumenta 8.9% · limp 13.9% | aumenta 30.9% · limp 5.9% | aumenta 7.5% · limp 41.6% |

- **Trial 2** no BTN (escala calibrada): aumenta QQ, JJ, TT, AKO, AQO, AQS, AKS, AJS…; premium que so pagam (limp): AA, KK.
- **Official 1** no BTN (escala calibrada): aumenta AA, KK, QQ, JJ, TT, 99, AKS, 88…; premium que so pagam (limp): nenhuma.

Leitura: no modo de equity (`preflop_override = 0`) a posicao so entra como uma reducao linear da equity minima (`pre_flop_equity_reduction_by_position` por posicao apos o UTG). O range de aumento cresce menos que na tabela do autor (17.2% a 62.3%): Trial 2: 13.9% (UTG) a 30.2% (SB); Official 1: 16.9% (UTG) a 30.9% (SB). Na mesa 0,05/0,10, sem reescalar `bigBlind`, os custos ficam 5x maiores para a curva e o robo fica muito mais fechado.

## 2. Flop heads-up como agressor (heroi com range de BTN do autor; vilao top 40%)

| Estrategia · mesa | Aposta por valor | Blefe | Check | Paga aposta de meio pote |
|---|---|---|---|---|
| Trial 2 · mesa 0,01/0,02 (calibrada) | 18% | 39% | 43% | 26% |
| Trial 2 · mesa 0,05/0,10 (cenario) | 12% | 39% | 49% | 18% |
| Official 1 · mesa 0,01/0,02 (calibrada) | 26% | 36% | 38% | 34% |
| Official 1 · mesa 0,05/0,10 (cenario) | 20% | 39% | 41% | 30% |

Aposta total = valor + blefe (o blefe usa uma faixa de equity fixa, sem considerar a textura do board). Equities altas acima de `FlopCheckDeceptionMinEquity` (0,85) viram check.

## 3. Quantidade de adversarios (equity real, simulador)

| Mao | 1 adv. | 2 adv. | 3 adv. | 4 adv. | 5 adv. | O robo usa no pre-flop |
|---|---|---|---|---|---|---|
| AS AH | 0.857 | 0.734 | 0.636 | 0.565 | 0.493 | 0.857 (sempre heads-up) |
| AS KS | 0.674 | 0.505 | 0.414 | 0.358 | 0.319 | 0.674 (sempre heads-up) |
| JS TS | 0.579 | 0.424 | 0.345 | 0.288 | 0.255 | 0.579 (sempre heads-up) |
| 7S 7H | 0.664 | 0.472 | 0.340 | 0.272 | 0.212 | 0.664 (sempre heads-up) |

## 4. Rake hipotetico e profundidade de stack (o robo nao considera nenhum dos dois)

| Situacao (valores em R$) | Odds do pote | Equity necessaria sem rake | Com rake 5% teto 3 BB |
|---|---|---|---|
| BB defende contra abertura de 2,5 BB do BTN | 0.300 | 0.300 | 0.316 |
| Paga aposta de meio pote no flop (pote 6 BB) | 0.250 | 0.250 | 0.263 |
| Paga all-in de 100 BB (pote 101,5 BB) | 0.496 | 0.496 | 0.504 |
| Paga all-in de 200 BB (pote 201,5 BB) | 0.498 | 0.498 | 0.502 |

Em potes pequenos o rake pesa mais (o teto so e atingido a partir de 60 BB de pote). O robo usa limites absolutos (`initialFunds` = 23,83, `initialFunds2` = 3,40) sem relacao com o stack efetivo.

## 5. Configuracao do ambiente de estudo (perfil gerado)

- Iteracoes para erro padrao ≤ 0.005: heads-up ≈ 9000, multiway (6 jogadores) ≈ 8000 (medido: erro padrao 0.0073 e 0.0069 com 4.000 iteracoes).
- Ranges de abertura por posicao: tabela do autor (`preflop.xlsx`), por ser posicional, ponderada por combinacoes e proxima dos valores tipicos de TAG 6-max.
- Rake padrao: hipotetico 5% com teto de 3 BB; stacks de 1 a 200 BB.

