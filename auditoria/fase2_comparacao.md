# Fase 2 — Comparacao motor original x simulador offline

Gerado por `python -m simulador.comparacao` (rede bloqueada). Iteracoes Monte Carlo: 20000.

## 1. Empates e potes divididos

| Cenario | Esperado | Original (antes) | Simulador (depois) |
|---|---|---|---|
| 2c3d vs aleatoria, board AsKsQsJsTs (empate garantido) | 0,500 | 0.672 | 0.500 (empate 100%) |
| 72o vs 1 aleatoria | ~0,346 | 0.380 | 0.350 (vitoria 0.321 + empate 0.059) |

Verificacao da hipotese: no original, 72o = 0.380 ~ vitoria + empate do simulador = 0.380 → **os empates contam como vitoria inteira**.
No board de royal flush o original nao da 1,0 porque um 2o defeito faz o vilao com qualquer espada "vencer" (ranks extras nao sao cortados no straight flush): P(vilao tem espada) = 1 − C(39,2)/C(47,2) = 0,315 → original ≈ 0,685 (medido 0.672).

## 2. Avaliador de maos (teste diferencial)

200000 confrontos aleatorios heroi x vilao com board completo. Divergencias: **9** (0.005%).

| Resultado correto → resultado do original | Ocorrencias |
|---|---|
| empata -> original diz vence | 5 |
| empata -> original diz perde | 4 |

Causa: todas as divergencias ocorrem com **quadra no board**. No original (`calc_score`, linhas 79-82) a mao e representada pelos dois maiores ranks distintos das 7 cartas (ex.: board 2222K + 84 vira (K, 8)), o que pode descartar o rank da quadra e usar uma carta que nao entra na melhor mao; o empate correto vira vitoria/derrota.

Exemplos:

- heroi KC 4D x vilao 8D 5H, board 2S 2D 2H 2C KH: empata -> original diz perde
- heroi AS KD x vilao AC TS, board 8H 5C 8S 8D 8C: empata -> original diz vence
- heroi 3D 6H x vilao QC 4S, board TS TH TD AD TC: empata -> original diz perde
- heroi 2C 4D x vilao AS 9S, board 8H 8D 8S AD 8C: empata -> original diz perde
- heroi KD QS x vilao 8D KC, board 2D 2C 5D 2H 2S: empata -> original diz vence

## 3. Respeito aos ranges

| Medida | Original (antes) | Simulador (depois) |
|---|---|---|
| Maos do oponente dentro do range top 10% | 83.5% | 100% (teste `test_todas_as_maos_sorteadas_estao_no_range`) |
| Definicao de top 10% | 16 classes = 7.8% das combinacoes | 21 classes = 10.1% das combinacoes |

Causa (original, `distribute_cards_to_players`, linhas 224-225): `deck.pop(random_card1)` desloca os indices antes de `deck.pop(random_card2)`; quando o 2o indice e maior que o 1o, sai uma carta diferente da validada.

Uniformidade das cartas do oponente (original, range total, 40000 distribuicoes): qui-quadrado p = 0.099 → nao ha evidencia de vies (p > 0,01). Extremos: 7D = 94% da media, JS = 106% da media.

## 4. Numero de adversarios (6-max, 5 adversarios na mao)

| Situacao | Jogadores simulados | Equity de AA |
|---|---|---|
| Original, pre-flop (sempre heads-up) | 2 | 0.855 |
| Original, pos-flop (limite `total_players − 2`) | 4 | 0.643 |
| Simulador (correto) | 6 | 0.491 (referencia 0,492) |

## 5. Hipoteses verificadas e descartadas

- *O Monte Carlo original esta errado em geral*: **descartada**. AA vs 1 aleatoria: original 0.855, simulador 0.853, referencia 0,852. A diferenca so aparece onde ha empates.
- *A equity de AA vs top 10% (0,849) era anomala*: **descartada**. Simulador com o mesmo range de 16 classes: 0.840; original 0.851. AA domina quase todas as classes do top 10%.

