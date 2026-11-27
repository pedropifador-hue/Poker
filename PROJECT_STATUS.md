# PROJECT_STATUS — Auditoria técnica e estratégica do DeeperMind PokerBot

- **Data:** 27/11/2026
- **Repositório:** https://github.com/pedropifador-hue/Poker (fork de `dickreuter/Poker`)
- **Versão do programa:** 6.76 (`poker/main.py:43`)
- **Escopo:** apenas leitura e documentação. **Nenhuma estratégia, regra de licenciamento ou arquitetura foi alterada.**
- **Fases:** Fase 1, auditoria (seções 1 a 11, tag `v6.76-auditoria-fase1`); Fase 2, validação matemática e simulador offline (seção 12); **Fase 3, estabilidade, análise de estratégias, janela do simulador e manual (seção 13)**. Manual de uso: [MANUAL.md](MANUAL.md). Histórico de mudanças em [CHANGELOG.md](CHANGELOG.md).

## Cenário de referência usado na avaliação

| Item | Valor |
|---|---|
| Jogo | Texas Hold'em No-Limit, cash game 6-max |
| Blinds | SB 0,05 / BB 0,10 |
| Buy-in máximo | 20,00 (= 200 BB) |
| Estilo de referência | Tight Aggressive (TAG) |
| Ambiente | estudos e simulações **offline**, sem conexão a salas de apostas |

---

## 1. Documentação original lida

- `readme.rst`: setup de PokerStars/PartyPoker/GGPoker, VirtualBox, Strategy Analyzer, Strategy Editor, versão paga ("Full version"), mapeamento de mesas e execução via Python/Docker.
- Tooltips de todos os campos do Strategy Editor (`poker/gui/ui/strategy_manager_form.ui`, 301 widgets extraídos).
- `.github/workflows/python-tests.yml`: o CI oficial usa Python 3.11 + `pytest` + `pylint`.

Pontos da documentação que importam para este cenário:
- O próprio autor diz: *"Most of the strategies are based on zoom or Fast Forward tables"* e recomenda **2.000 a 5.000 mãos** antes de concluir algo sobre uma estratégia.
- O readme alerta: não testar com contas reais antes de verificar o funcionamento (risco de perder conta e capital).
- Editar/criar estratégias exige a versão paga (senha enviada após compra).

---

## 2. Arquitetura (como uma decisão é tomada)

```
Captura de tela ──► scraper/table_screen_based.py  (cartas, botões, pote, stacks, dealer, jogadores ativos — via OCR/templates)
                         │
                         ▼
decisionmaker/montecarlo_python.py  ──►  equity (probabilidade de vencer) por simulação
                         │
                         ▼
decisionmaker/decisionmaker.py  ──►  curvas de limite de call/bet (curvefitting.py) + regras
                         │                 (blefe, check deception, pot bet no river, etc.)
                         ▼
tools/mouse_mover.py  ──►  clique no botão (Fold/Check/Call/Bet/BetPlus/Bet half pot/Bet pot)
```

A **estratégia** é um dicionário de ~90 parâmetros **baixado do servidor do autor** (`tools/strategy_handler.py:115-135`). Não há arquivo local de estratégia no projeto.

### Como funciona a "curva" (núcleo da estratégia)

Para cada street, o robô calcula **o valor máximo (em dinheiro) que aceita pagar** e **o valor máximo que aceita apostar**, em função da equity:

```
limite(equity) = a · (equity + b) ^ Power
```
A curva passa por dois pontos (`decisionmaker/curvefitting.py:42-70`, `decisionmaker.py:189-196` e `269-272`):
- `(MinEquity, 2 × bigBlind)`: abaixo dessa equity o limite é 0 (fold/check);
- `(1,0 ou 0,95 no pré-flop, initialFunds / initialFunds2)`: limite máximo com 100% de equity.

`Power` controla a curvatura: quanto maior, mais o limite fica perto de zero até equities altas (jogo mais tight).

Decisão (`decisionmaker.py:353-432`): **Call** se `limite_call ≥ valor do call`; **Bet** se `limite_bet ≥ valor do bet mínimo`; **Bet half pot** se `limite_bet ≥ pote/2`; **Bet pot** no river só com `equity ≥ betPotRiverEquity`.

---

## 3. Parâmetros do Strategy Editor

Legenda da coluna **Efeito no código**: ✅ usado nas decisões · ⚙️ usado fora da decisão (log, OCR, algoritmo genético) · ⚠️ sem efeito ou quebrado na versão atual.
Valores lidos do servidor em 27/11/2026 (cópia em `auditoria/estrategias_snapshot.json`).

### 3.1 Limites básicos e escala monetária

| Parâmetro | Trial 2 | Official 1 | Função | Efeito no código |
|---|---|---|---|---|
| `bigBlind` | 0,02 | 0,02 | Big blind **assumido pela estratégia** (não é lido da mesa). Base de `2×BB` (ponto inicial da curva), do ajuste por pote e do limite de pot bet no river. | ✅ `decisionmaker.py:33,144-152,159` |
| `smallBlind` | 0,01 | 0,01 | Small blind assumido. | ⚙️ só exibido no gráfico de curvas |
| `initialFunds` | 23,83 | 23,83 | Valor máximo de **call** com 100% de equity (canto superior direito da curva de call). | ✅ `decisionmaker.py:189` |
| `initialFunds2` | 3,40 | 3,40 | Valor máximo de **bet** com 100% de equity. | ✅ `decisionmaker.py:269` |
| `use_pot_multiples` | 0 | 0 | Usa múltiplos do pote em vez de valores absolutos nas curvas. | ✅ `decisionmaker.py:54-58` |
| `pokerSite` | PP | PP | Sala para a qual a estratégia foi feita (PartyPoker). Não aparece no editor. | ⚙️ scraper |

### 3.2 Curvas por street (pré-flop, flop, turn, river)

| Parâmetro (× 4 streets) | Trial 2 (PF / F / T / R) | Official 1 (PF / F / T / R) | Função | Efeito |
|---|---|---|---|---|
| `{Street}MinCallEquity` | 0,62 / 0,66 / 0,73 / 0,74 | 0,59 / 0,59 / 0,59 / 0,73 | Equity mínima para pagar 2×BB (início da curva de call). | ✅ `decisionmaker.py:154-187` |
| `{Street}CallPower` | 10 / 10 / 10 / 10 | 3 / 3 / 4 / 4 | Curvatura da curva de call. | ✅ |
| `{Street}MinBetEquity` | 0,56 / 0,68 / 0,76 / 0,82 | 0,61 / 0,60 / 0,65 / 0,76 | Equity mínima para apostar 2×BB (início da curva de bet). | ✅ `decisionmaker.py:214-245` |
| `{Street}BetPower` | 5 / 2 / 1 / 1 | 5 / 2 / 1 / 1 | Curvatura da curva de bet. | ✅ |
| `PreFlopMaxBetEquity` | **0,78** | 1,00 | Acima dessa equity o limite de bet pré-flop vira 0 (só paga, *slowplay*). | ✅ `decisionmaker.py:220`, `curvefitting.py:57` |

### 3.3 Ajustes de equity mínima

| Parâmetro | Trial 2 | Official 1 | Função | Efeito |
|---|---|---|---|---|
| `pre_flop_equity_reduction_by_position` | 0,02 | 0,01 | Reduz a equity mínima pré-flop em X por posição após UTG (`X × UTG+n`). | ✅ `decisionmaker.py:106-108` |
| `pre_flop_equity_increase_if_bet` | 0,05 | 0,05 | Soma X à equity mínima pré-flop se alguém aumentou antes. | ✅ `decisionmaker.py:110-112` |
| `pre_flop_equity_increase_if_call` | 0,02 | 0,02 | Soma X se alguém pagou antes. | ✅ `decisionmaker.py:116-118` |
| `secondRoundAdjustmentPreFlop` | 0,10 | 0,10 | Soma X à equity mínima quando o robô age pela 2ª vez na mesma street pré-flop (houve reraise). | ✅ `decisionmaker.py:123-135` |
| `secondRoundAdjustment` | 0,05 | 0,05 | Idem, pós-flop. | ✅ |
| `secondRoundAdjustmentPowerIncrease` | 2 | 2 | Soma X ao `Power` na 2ª rodada (curva mais tight). | ✅ |
| `potAdjustmentPreFlop` / `potAdjustment` | 1 / 1 | 1 / 1 | Reduz a equity mínima conforme o pote cresce: `pote / BB / 250 × X`. | ✅ `decisionmaker.py:144-152` |
| `maxPotAdjustmentPreFlop` / `maxPotAdjustment` | 0,03 / 0,02 | 0,03 / 0,02 | Teto desse ajuste (no máximo 3% e 2%). | ✅ |
| `out_multiplier` | 2 | 2 | Reduz a equity mínima no flop/turn em `outs × X %`. (O tooltip na interface está errado: repete o texto do `BetPlusInc`.) | ✅ `decisionmaker.py:88-104` |
| `opponent_raised_without_initiative_{flop,turn,river}` | 1 / 1 / 1 | 1 / 1 / 1 | Soma 10% à equity mínima de **bet** se o oponente aumentou sem ter a iniciativa. | ✅ `decisionmaker.py:199-212` |

### 3.4 Ranges dos adversários (simulação Monte Carlo)

| Parâmetro | Trial 2 | Official 1 | Função | Efeito |
|---|---|---|---|---|
| `range_preflop` | 0,50 | 1,00 | No pré-flop, os adversários recebem só os X% melhores tipos de mão. | ✅ `montecarlo_python.py:316` |
| `range_utg0` … `range_utg5` | 0,40 (todos) | 0,40 – 0,50 | Range pós-flop do **único** adversário (heads-up), conforme a posição dele. | ✅ `montecarlo_python.py:320-326` |
| `range_utg6` … `range_utg8` | 0,20 | 0,20 | Para mesas com mais de 6 lugares. | ⚠️ irrelevante em 6-max |
| `range_multiple_players` | 0,40 | 0,10 | Range de cada adversário quando há 2 ou mais na mão pós-flop. | ✅ |
| `range_of_range` | **1** | 0 | Usa a tabela `preflop_equity-50.json` (equities calculadas contra um range de 50%) para ordenar as mãos. | ✅ `montecarlo_python.py:37-50` |
| `differentiate_reverse_sheet` | 0 | 0 | Na "reverse table" (inferir o range pela ação pré-flop), distingue call de raise. | ✅ `current_hand_memory.py` |
| `CoveredPlayersCallLikelihoodFlop` | 0,10 | 0,10 | Segundo o tooltip, ajustaria o número de jogadores simulados no flop. | ⚠️ **não é lido em nenhum lugar** fora da GUI |

### 3.5 Apostas, tamanhos e river

| Parâmetro | Trial 2 | Official 1 | Função | Efeito |
|---|---|---|---|---|
| `minimum_bet_size` | 3 | 3 | Tamanho mínimo pós-flop: 2 = BetPlus, 3 = meio pote, 4 = pote. | ✅ `decisionmaker.py:530-543` |
| `BetPlusInc` | 2 | 2 | Cliques no slider para o "BetPlus" (bet maior que o mínimo). | ✅ `decisionmaker.py:405,565` |
| `increased_preflop_betting` | 1 | 1 | Se = 2, permite "Bet half pot" pré-flop. | ✅ `decisionmaker.py:372-375` |
| `betPotRiverEquity` | 0,95 | 0,95 | Equity mínima para apostar o pote no river. | ✅ `decisionmaker.py:425` |
| `betPotRiverEquityMaxBBM` | 50 | 50 | Pot bet no river só se o pote < X × BB. | ✅ |
| `secondRiverBetPotMinEquity` | 0,98 | 0,98 | Pot bet ao agir pela 2ª vez no river. | ✅ `decisionmaker.py:606-610` |
| `alwaysCallEquity` | 0,90 | 0,90 | Acima dessa equity nunca dá fold (limite de call infinito). | ✅ `decisionmaker.py:584-586` |
| `always_call_low_stack_multiplier` | 12 | 12 | Paga tudo se `stack próprio × X < pote`. | ✅ `decisionmaker.py:588-592` |

### 3.6 Blefe, check deception e bully

| Parâmetro | Trial 2 | Official 1 | Função | Efeito |
|---|---|---|---|---|
| `FlopBluffMinEquity` / `FlopBluffMaxEquity` | 0,40 / 0,65 | 0,40 / 0,65 | Faixa de equity para blefar no flop (só heads-up, 1ª ação da street, quando a decisão seria check). | ✅ `decisionmaker.py:434-471` |
| `TurnBluffMinEquity` / `TurnBluffMaxEquity` | 0,70 / 0,85 | 0,70 / 0,85 | Idem, turn. | ✅ |
| `RiverBluffMinEquity` / `RiverBluffMaxEquity` | 1,00 / 1,00 | 1,00 / 1,00 | Idem, river. Com min = max = 1,0, o blefe no river fica **desligado**. | ✅ |
| `{flop,turn,river}_bluffing_condidion_1` | 0 / 0 / 0 | 0 / 0 / 0 | Só blefa se nenhum jogador age antes nesta rodada. | ✅ |
| `{turn,river}_bluffing_condidion_2` | 1 / 1 | 1 / 1 | Não blefa se o oponente tem a iniciativa. | ✅ |
| `{flop,turn,river}_betting_condidion_1` | 0 / 1 / 1 | 0 / 1 / 1 | Não aposta se o oponente tem a iniciativa (exceto sem botão de check). | ✅ `decisionmaker.py:384-432` |
| `FlopCheckDeceptionMinEquity` | 0,85 | 0,85 | Com equity acima disso, dá check em vez de bet no flop (armadilha). | ✅ `decisionmaker.py:473-504` |
| `TurnCheckDeceptionMinEquity` / `RiverCheckDeceptionMinEquity` | 0,95 / 1,00 | 0,95 / 1,00 | Idem, turn/river (só se o robô pagou na street anterior). | ✅ |
| `minBullyEquity`, `maxBullyEquity`, `bullyDivider` | 1,0 / 0,0 / 1 | 1,0 / 0,0 / 1 | "Modo bully" contra oponente com stack curto. | ⚠️ a função `bully()` **não é chamada** (`decisionmaker.py:611`, comentada) |
| `antibluff_percentage` | 0 | 0 | Sem widget no editor. | ⚠️ não usado |

### 3.7 Opções gerais e algoritmo genético

| Parâmetro | Trial 2 | Official 1 | Função | Efeito |
|---|---|---|---|---|
| `preflop_override` | 0 | 0 | Usa a tabela de especialista (`preflop.xlsx`) no pré-flop em vez das curvas. | ✅ `decisionmaker.py:594-596` |
| `use_relative_equity` | 0 | 0 | Usaria "equity relativa" ao range do próprio robô. | ⚠️ **quebrado**: ativar gera `RuntimeError("Relative equity not implemented correctly")` (`montecarlo_python.py:409-410`) |
| `gather_player_names` | 0 | 0 | Lê o nome dos jogadores por OCR (perfil de frequência no heads-up). | ⚙️ `table_screen_based.py:281` |
| `collusion` | **0** | 0 | "Participar de conluio": envia suas cartas ao servidor e recebe as de outro robô na mesma mesa. | ✅ `game_logger.py:124-141`. **Ver alerta na seção 7.** |
| `max_abs_fundchange` | 50 | 3,08 | Só registra no log mãos cuja variação de stack ≤ X (filtra erros de OCR). | ⚙️ `game_logger.py:113` |
| `considerLastGames` | 2011 | 100 | Algoritmo genético automático: quantas mãos recentes considerar. | ⚙️ `scraper/table.py:64` |
| `strategyIterationGames` | 10000 | 10000 | A cada X mãos, verifica se deve iterar a estratégia. | ⚙️ `scraper/table.py:77` |
| `minimumLossForIteration` | -100 | -100 | Perda mínima que dispara a iteração. | ⚙️ |

---

## 4. Estratégia Trial 2: características e limitações

Valores calculados **offline** pela própria função de curva do projeto (`auditoria/curvas_trial2.py`). Limite em unidades monetárias para cada equity:

| Street | Tipo | Eq 0,55 | 0,65 | 0,75 | 0,85 | 0,95 |
|---|---|---|---|---|---|---|
| Pré-flop | call | 0 | 0,09 | 0,82 | 5,09 | 23,83 |
| Pré-flop | bet | 0 | 0,17 | 0,56 | **0** | **0** |
| Flop | call | 0 | 0 | 0,33 | 2,31 | 11,60 |
| Flop | bet | 0 | 0 | 0,31 | 1,15 | 2,52 |
| Turn | call | 0 | 0 | 0,08 | 1,14 | 9,54 |
| Turn | bet | 0 | 0 | 0 | 1,30 | 2,70 |
| River | call | 0 | 0 | 0,06 | 0,99 | 9,20 |
| River | bet | 0 | 0 | 0 | 0,60 | 2,47 |

Perfil: equity mínima alta e `CallPower = 10` em todas as streets formam um perfil **muito tight e passivo nos calls**. As apostas são pequenas em relação aos calls (`initialFunds2` = 3,40 contra `initialFunds` = 23,83).

**Limitações para o cenário 0,05/0,10, 6-max, TAG:**

1. **Escala de blinds errada.** A Trial 2 foi calibrada para **0,01/0,02 no PartyPoker** (`bigBlind = 0,02`, `pokerSite = PP`). O robô **não lê o blind da mesa**: usa o da estratégia (`decisionmaker.py:33-34`). Numa mesa 0,05/0,10:
   - o ponto inicial das curvas (`2 × BB`) seria 0,04 (0,4 BB reais) em vez de 0,20;
   - o ajuste por pote (`pote / BB / 250`) ficaria 5× mais forte que o planejado;
   - `initialFunds2` = 3,40 equivale a apenas **34 BB** reais (era 170 BB na escala original);
   - `betPotRiverEquityMaxBBM` = 50 × 0,02 = 1,00, ou seja, só 10 BB reais.
2. **Não aumenta com mãos premium pré-flop.** `PreFlopMaxBetEquity = 0,78` zera o limite de bet acima de 78% de equity, e `preflop_override = 0` (não usa a tabela de especialista). Com AA, KK etc., o robô **só paga**. Isso contraria um estilo TAG, que aumenta por valor.
3. **Pós-flop passivo:** `CallPower = 10` exige equity ≥ 0,85 para pagar mais que ~2 de pote no flop, e `minimum_bet_size = 3` força apostas de meio pote.
4. **Blefe no river desligado** (min = max = 1,0); blefes só no flop/turn e só heads-up.
5. **Ranges fixos e iguais** (`range_utg0..5 = 0,40`): a posição do adversário não muda o range dele.
6. **Edição bloqueada para o usuário guest:** salvar exige assinatura (seção 6).
7. Não considera stack efetivo nem rake (seção 5).

---

## 5. Como o projeto calcula os conceitos-chave

### 5.1 Equity
- Monte Carlo em Python puro (`montecarlo_python.py:238-300`): 3.000 (pré-flop), 5.000 (flop), 4.000 (turn) ou 3.000 (river) simulações, com corte por tempo (`montecarlo_timeout = 8` s em `config.ini`).
- **Empates contam como vitória do robô.** `eval_best_hand` ordena com `sorted(..., reverse=True)`; como a ordenação é estável, em caso de empate vence o índice 0, que é sempre o robô (`montecarlo_python.py:52-55`; o próprio código comenta *"considering draws as wins"*, linha 486). Evidência offline: com um royal flush na mesa (empate garantido), a equity retornada foi **0,68**, quando deveria ser 0,50 (pote dividido). Isso **superestima a equity** em boards com empate provável.
- Verificação offline contra valores conhecidos: AA vs 1 aleatório = 0,854 (referência ~0,85); AA vs 5 aleatórios = 0,495 (~0,49); 72o vs 1 aleatório = 0,376 (~0,35, inflado pelos empates).

### 5.2 Pot odds
- **Não há regra explícita de pot odds na decisão.** `calc_EV_call_limit` (`base.py:18-25`) calcula o call de EV zero (`E·P − (1−E)·S = 0`), mas o resultado `maxCallEV` **só vai para o log**: a decisão usa apenas a curva (`decisionmaker.py:137-140` e `274-276`, com o `min(...)` comentado). Esse cálculo também tem teto de 10 unidades (`MaxCall = 10`).
- O tamanho do pote só entra pelo `potAdjustment`, que reduz a equity mínima em no máximo 2–3% na Trial 2.

### 5.3 Ranges
- O range é uma fração das **169 classes de mão** (AA, AKs, AKo…), ordenadas pela equity em `preflop_equity.json` (`montecarlo_python.py:37-50`). As classes **não são ponderadas pelo número de combinações** (par = 6, suited = 4, offsuit = 12).
- **Falha no sorteio:** em `distribute_cards_to_players` (linhas 224-225), a 1ª carta é removida do baralho antes da 2ª, o que desloca os índices; a carta entregue pode não ser a que foi validada. Evidência offline (`auditoria/verificacao_range.py`): com range de 10%, só **82,9%** das mãos sorteadas para o oponente estavam dentro do range.
- Pós-flop, com 1 adversário, o range pode vir da "reverse table" (ação pré-flop observada); com vários, usa `range_multiple_players`.

### 5.4 Posição
- O botão do dealer é detectado por imagem; `position_utg_plus = (total_players + 3 − dealer_position) % total_players` (`table_screen_based.py:392-410`).
- Efeitos: (a) pré-flop, reduz a equity mínima linearmente por posição; (b) pós-flop, escolhe `range_utgN` do adversário (só heads-up); (c) condições de blefe e aposta via `playersAhead` (jogadores que agem antes).
- Há valor fixo de 6 lugares em `big_blind_position_abs_all = (dealer_position + 2) % 6` (linha 407).

### 5.5 Número de adversários
- `other_active_players` vem da detecção de cartas cobertas na tela (`table_screen_based.py:327-352`).
- Jogadores na simulação (`montecarlo_python.py:314-347`):
  - **Pré-flop: sempre 2 (heads-up)**, mesmo com vários jogadores na mão; a correção fica a cargo dos ajustes `pre_flop_equity_increase_if_*`;
  - Flop: `ativos − round(playersAhead × (1 − range)) + 1`;
  - Turn/River: `ativos + 1`;
  - Limitado ao intervalo `[2, total_players − 2]`: em 6-max, **no máximo 3 adversários** simulados, mesmo com 5 na mão.

### 5.6 Stack efetivo e rake

| Conceito | Considerado? | Evidência |
|---|---|---|
| Stack efetivo | **Não** | A decisão só usa o stack do próprio robô em `always_call_low_stack_multiplier` (`decisionmaker.py:588`). Os limites são valores absolutos fixos (`initialFunds`/`initialFunds2`). O arquivo `decisionmaker/implied_odds.py` tem uma função de stack efetivo, mas **não é importado por nenhum módulo** (código morto). |
| Stack do adversário | Só no modo bully | E o modo bully está desativado (seção 3.6). |
| Rake | **Não** | Nenhuma ocorrência de "rake" em todo o código Python. |
| Stack máximo de 200 BB | Indiretamente | Só via `initialFunds`; nenhum parâmetro em BB. |

---

## 6. Dependências de servidores externos, licenças e assinaturas

Servidor do autor: **`https://dickreuter.com:7778/`** (chave `db` em `poker/config.ini`). Login padrão: `guest`/`guest` (público, não é credencial pessoal).

| Funcionalidade | Endpoint(s) | Offline? | Observação |
|---|---|---|---|
| Carregar estratégia ao abrir | `get_strategy`, `get_playable_strategy_list` | ❌ | Obrigatório: a interface chama `read_strategy()` ao iniciar (`action_and_signals.py:69-70`). |
| Salvar/editar estratégia | `save_strategy`, `update_strategy` | ❌ | **Exige assinatura paga.** O servidor recusa para guest e a GUI abre o link de compra (`action_and_signals.py:643-645`). O botão "salvar sobre" só é habilitado para estratégias criadas no mesmo computador ou nos computadores do autor (nomes fixos no código, linhas 494-496). **Não foi contornado.** |
| Mapas de mesa (coordenadas e imagens) | `get_table`, `get_available_tables`, `create_new_table*`, `save_coordinates`, `update_table_image` | ❌ | Necessários para o scraper ler a mesa. |
| Rede neural de cartas | `get_tensorflow_weights`, `update_tensorflow_model` | ❌ | Opcional por mesa. |
| Versão e tabela pré-flop | `get_internal` | ❌ | Informa a última versão e a URL do `preflop.xlsx` (existe uma cópia local em `decisionmaker/preflop.xlsx`). |
| Atualização automática | `UpdateChecker.downloader` | ❌ | Baixa um executável do site do autor se houver versão nova. |
| **Registro de cada mão jogada** | `insert_round`, `insert_games` | ❌ | **Telemetria:** cada decisão é enviada ao servidor com o nome do computador (`game_logger.py:40-122`). |
| Strategy Analyzer / gráficos | `get_stacked_bar_data*`, `get_histrogram_data`, `get_game_count`, `get_strategy_return`, `get_fundschange_chart`, `get_worst_games`, `get_top_strategies` | ❌ | Os dados vêm do banco do autor, não do seu computador. |
| Conluio (`collusion`) | `insert_collusion`, `get_collusion_cards` | ❌ | Ver seção 7. |
| API local | `127.0.0.1:8005` (`restapi_local.py`) | ✅ | Só local, para capturas de tela. |
| Chat / compra | Discord, `deepermind-pokerbot.com/purchase` | — | Só abrem links; nenhuma compra foi feita. |

---

## 7. Alertas de ética e segurança

- **Conluio:** o parâmetro `collusion` compartilha as cartas fechadas entre robôs na mesma mesa. Isso é **trapaça contra os outros jogadores** e viola as regras de qualquer sala. Está **desligado** (0) na Trial 2 e na Official 1 e deve continuar assim.
- **Uso em salas reais:** PokerStars, PartyPoker e GGPoker proíbem robôs. Usar o bot pode levar a banimento e confisco de saldo, e prejudica outros jogadores. Nesta etapa, **nenhuma conexão com salas de apostas foi feita**, e o ambiente de testes não tem cliente de pôquer.
- **Privacidade:** ao abrir, o programa envia ao servidor do autor o nome do computador e, durante o jogo, cada mão. É o comportamento original e não foi alterado.

---

## 8. Testes e simulações 100% offline

> **Atualizado na Fase 2:** o ambiente offline recomendado agora é o pacote `simulador/` com o executor `python -m simulador.testes` (seção 12). Os scripts de `auditoria/` da Fase 1 continuam válidos como evidência.

### O que funciona sem internet
- Monte Carlo (`decisionmaker/montecarlo_python.py`), cálculo de outs (`outs_calculator.py`), curvas (`curvefitting.py`) e a tabela pré-flop local.
- Testes `test_montecarlo.py` e `test_outs.py` (não chamam o servidor).
- Scripts desta auditoria em `auditoria/` (bloqueiam a rede de propósito e falham se algo tentar se conectar).

### O que **não** funciona offline
- A interface gráfica (`main.py`): exige o servidor para carregar a estratégia e o mapa da mesa.
- `test_decision.py` e `test_reverseTables.py` (baixam a estratégia), `test_table_and_ocr.py` e `test_tensorflow.py` (baixam mapas/pesos das mesas).

### Comandos (PowerShell, na pasta do projeto)

Preparar o ambiente (uma vez por janela):
```powershell
$env:PYTHONPATH = (Get-Location).Path   # execute dentro da pasta do projeto
```

Testes offline:
```powershell
.\.venv\Scripts\python.exe -m pytest poker/tests/test_montecarlo.py poker/tests/test_outs.py -v
```

Simulações de equity com a rede bloqueada:
```powershell
.\.venv\Scripts\python.exe -I auditoria\simulacao_offline_montecarlo.py .
```

Conferir o filtro de range:
```powershell
.\.venv\Scripts\python.exe -I auditoria\verificacao_range.py .
```

Curvas da Trial 2 (lê `auditoria/estrategias_snapshot.json`, sem rede):
```powershell
.\.venv\Scripts\python.exe -I auditoria\curvas_trial2.py .
```

---

## 9. Integridade do ambiente e testes existentes

| Item | Resultado |
|---|---|
| Python | 3.11.9 em `.venv` (o mesmo do CI oficial) |
| `pip check` | "No broken requirements found." |
| Bibliotecas principais | TensorFlow 2.12.0 · OpenCV 4.11.0 · PyQt6 6.12.1 · pandas 2.0.3 · numpy 1.23.5 · Tesseract 5.5.4 |
| OCR | `tesserocr` carrega os dados de `tessdata/` sem erro |
| Interface | Abre, carrega a estratégia e não registra erros em `log/deepmind_pokerbot_errors.log` (teste anterior) |

### Bateria completa de testes (`pytest poker/tests`, 45 testes coletados, limite de 25 min)

| Arquivo | Resultado | Usa servidor? | Observação |
|---|---|---|---|
| `test_outs.py` | ✅ 15/15 passaram | Não | Cálculo de outs íntegro. |
| `test_montecarlo.py` | ✅ 3 passaram · ❌ 1 falhou | Não | `test_monteCarlo` falha com `TypeError: run_montecarlo() got an unexpected keyword argument 'maxRuns'`: o teste usa um nome de parâmetro antigo (o código usa `max_runs`). **Defeito do teste original, não do ambiente.** |
| `test_table_and_ocr.py` | ✅ 9/9 passaram | Sim (`get_table`) | OCR do Tesseract e recorte de imagens funcionando. |
| `test_tensorflow.py` | ✅ 1 passou · ❌ 1 falhou · ⏱️ 1 interrompido | Sim | `test_save_model` tenta **enviar** um modelo ao servidor do autor e foi recusado; **não deve ser executado**. `test_train_card_neural_network_and_predict` treina uma rede neural na CPU e passou do limite de 25 min (interrompido, sem erro). |
| `test_decision.py` | ⏭️ 14 ignorados | Sim | Marcados pelo autor com `@pytest.mark.skip(reason="Fix access issues")`. |
| `test_reverseTables.py` | ⏭️ ignorado | Sim | Marcado com `@pytest.mark.skip()` pelo autor. |
| `test_tableScreenBased.py` | — | — | Não contém testes. |

**Conclusão:** nenhuma falha vem da instalação. As duas falhas são de testes desatualizados ou que dependem de permissão de escrita no servidor do autor.

---

## 10. Git e sincronização com o GitHub

| Item | Situação |
|---|---|
| Branch atual | `master` (rastreia `origin/master`); é a única branch do fork |
| Remoto | `origin` → https://github.com/pedropifador-hue/Poker.git |
| Sincronização antes desta auditoria | Local e GitHub idênticos em `6ad6b46` (verificado com `git fetch` + `git rev-parse`) |
| Branch de desenvolvimento | Por decisão do usuário, **todo o trabalho segue no `master`**; nenhuma branch nova foi criada |
| Tag do estado auditado | `v6.76-auditoria-fase1` → commit `0163ef2` (enviada ao GitHub) |
| Alteração local não commitada | `poker/config.ini`: `last_strategy` mudou de "Official 1" para "Trial 2" ao selecionar a estratégia na interface. É preferência local e **não** foi incluída no commit. |

### Arquivos adicionados nesta auditoria (sem alterar o código original)
- `PROJECT_STATUS.md`: este relatório.
- `auditoria/estrategias_snapshot.json`: cópia dos parâmetros da Trial 2 e da Official 1, sem `_id` e nome de computador.
- `auditoria/simulacao_offline_montecarlo.py`, `auditoria/verificacao_range.py`, `auditoria/curvas_trial2.py`: scripts de evidência offline.

---

## 11. Resumo dos principais achados

1. A Trial 2 está calibrada para 0,01/0,02 (PartyPoker), não para 0,05/0,10; o blind vem da estratégia, não da mesa.
2. A Trial 2 não aumenta com mãos premium pré-flop (`PreFlopMaxBetEquity = 0,78`). Ela é tight, mas passiva, e não TAG.
3. Empates contam como vitória na simulação (equity superestimada).
4. O filtro de range deixa ~17% das mãos fora do range e não pondera por combinações.
5. O pré-flop é sempre simulado como heads-up; o pós-flop tem no máximo 3 adversários simulados em 6-max.
6. Pot odds são calculadas, mas não usadas na decisão.
7. Stack efetivo e rake não são considerados.
8. Seis parâmetros não têm efeito (`CoveredPlayersCallLikelihoodFlop`, `antibluff_percentage`, bully ×3, `range_utg6-8` em 6-max) e um quebra o programa se ativado (`use_relative_equity`).
9. A interface e o salvamento de estratégias dependem do servidor do autor; salvar exige assinatura.
10. A função de conluio existe e deve permanecer desligada.

---

## 12. Fase 2: validação matemática e simulador offline

### 12.1 O que foi construído

Um pacote **novo e isolado**, `simulador/`, separado da execução do PokerBot. O motor original (`poker/decisionmaker/montecarlo_python.py`) **não foi alterado** e serve só de referência de comparação.

| Arquivo | Função |
|---|---|
| `simulador/cartas.py` | Cartas 0–51, conversão de texto (`'AS'`), classes de mão (`AKS`, `AKO`, `AA`) |
| `simulador/avaliador.py` | Avaliador de 5 a 7 cartas escrito do zero (não reutiliza o código original) |
| `simulador/ranges.py` | Ranges por **combinações** (correto) ou por **classes** (modo do original, para comparação) |
| `simulador/equity.py` | Monte Carlo com semente, empates divididos 1/k, 2 a 10 jogadores, enumeração exata |
| `simulador/cenario.py` | Mesa 6-max 0,05/0,10, stack máximo de 200 BB, stack efetivo, odds do pote, equity necessária, EV de call/all-in e estruturas **hipotéticas** de rake |
| `simulador/seguranca.py` | Bloqueio de rede (socket/DNS) usado em todos os testes do simulador |
| `simulador/comparacao.py` | Gera `auditoria/fase2_comparacao.md` (antes x depois) com a rede bloqueada |
| `simulador/testes.py` | Executor de testes por categoria |
| `simulador/tests/` | 88 testes (avaliador, equity, cenário, isolamento, comparação) |

**Garantias de isolamento**, verificadas por `test_isolamento.py`:
- nenhum módulo do simulador usa `requests`, `urllib`, `socket` (exceto o bloqueador), mouse, captura de tela, VirtualBox, banco do autor ou conluio;
- importar o simulador não carrega nenhum módulo `poker.*` nem `requests`;
- qualquer conexão de rede durante os testes gera `RedeBloqueada`.

### 12.2 Validação matemática: resultados esperados x obtidos

| Item validado | Referência | Esperado | Obtido (simulador) | Situação |
|---|---|---|---|---|
| Contagem das 2.598.960 mãos de 5 cartas | Combinatória clássica | SF 40 · quadra 624 · full 3.744 · flush 5.108 · sequência 10.200 · trinca 54.912 · 2 pares 123.552 · par 1.098.240 · carta alta 1.302.540 | idêntico | ✅ exato |
| Vitória por outs no turn (AhKh x QsQd, 2h7hQc3s) | Fórmula fechada | 7/44 = 0,1591 | 0,1591 (enumeração) | ✅ exato |
| Vitória no flop (AA x KK, 2c7d9h) | Fórmula fechada | 907/990 = 0,9162 | 0,9162 | ✅ exato |
| AA x KK pré-flop | Tabelas clássicas | ≈ 0,82 | enumeração exata dos 1.712.304 boards dentro de ±0,01; Monte Carlo dentro de 4 erros-padrão | ✅ |
| Empate total (board royal flush) | Regra | vitória 0, empate 100%, equity 0,5 | 0, 100%, 0,500 | ✅ |
| Pote dividido em 3 | Regra | 1/3 cada | 1/3 cada | ✅ |
| Simetria AsAh x AdAc | Simetria | 0,5; empate ≈ 95% | 0,5 ± 0,01; empate entre 93% e 97% | ✅ |
| AA x 1…5 aleatórias (2 a 6 jogadores) | Tabelas clássicas | 0,852 / 0,735 / 0,639 / 0,559 / 0,492 | 0,850 / 0,731 / 0,639 / 0,558 / 0,489 | ✅ (tol. ±0,012) |
| 72o x 1 aleatória | Tabelas clássicas | ≈ 0,346 | 0,346–0,350 (vitória 0,32 + metade de empates de 0,06) | ✅ |
| Soma das equities (6 jogadores) | Conservação | 1,0 | 1,0 | ✅ |
| Unicidade das cartas (6 jogadores + board, 3.000 mãos) | Regra | 17 cartas distintas | sempre distintas | ✅ |
| Uniformidade das cartas do board | Qui-quadrado | p > 0,001 | aprovado | ✅ |
| Mãos dentro do range (5%, 10%, 25%, 50%) | Definição | 100% | 100% | ✅ |
| Frequência AA : AKs : AKo no range | Combinações 6 : 4 : 12 | proporcional | qui-quadrado aprovado | ✅ |
| Reprodutibilidade | Mesma semente | resultados idênticos | idênticos | ✅ |
| Convergência | Erro ∝ 1/√n | erro cai ~2× ao quadruplicar n; erro real < 4 erros-padrão | razão entre 1,7 e 2,3; aprovado em n = 1k, 4k, 16k | ✅ |
| Comparação com implementação independente | Teste diferencial com o avaliador original (200.000 confrontos) | — | 9 divergências, todas com quadra no board (defeito do original) | ✅ explicado |

### 12.3 Problemas confirmados no motor original (com evidência)

Fonte: `auditoria/fase2_comparacao.md` e `simulador/tests/test_comparacao_motor_original.py`.

| # | Problema | Evidência (antes) | Depois (simulador) |
|---|---|---|---|
| P1 | **Empate conta como vitória inteira** do robô | 72o = 0,380 no original, que é igual a vitória + empate (0,321 + 0,059) | 0,350 (empate dividido) |
| P2 | **Straight flush usa uma carta extra** como desempate: com board AsKsQsJsTs, um vilão com qualquer espada "vence" | Original 0,672 (teoria: 741/1081 = 0,685) | 0,500 |
| P3 | **Desempate errado com quadra no board** (`calc_score`, linhas 79-82) | 9 em 200.000 confrontos; ex.: board 2222K, KC4D x 8D5H: original diz "perde" | empate |
| P4 | **Vazamento de range:** cartas sorteadas diferentes das validadas (`pop` desloca índices, linhas 224-225) | 83,5% das mãos dentro do top 10% | 100% |
| P5 | **Range medido em classes, não em combinações** | "top 10%" = 16 classes = 7,8% das combinações | top 10% = 21 classes = 10,1% (modo `classes` disponível para comparar) |
| P6 | **Número de adversários reduzido** (pré-flop sempre heads-up; pós-flop no máximo `total_players − 2` = 4 jogadores) | AA com 5 adversários: original 0,855 (pré-flop) / 0,643 (pós-flop) | 0,491 (referência 0,492) |
| P7 | **Não reprodutível:** usa `np.random` global sem semente | — | semente explícita (`semente=`) |
| P8 | Teste original `test_monteCarlo` desatualizado (`maxRuns` x `max_runs`) | `TypeError` | registrado como falha conhecida; o teste original não foi alterado |

### 12.4 Hipóteses descartadas

| Hipótese | Resultado | Evidência |
|---|---|---|
| "O Monte Carlo original está errado em geral" | **Descartada** | AA x 1 aleatória: original 0,855, simulador 0,853, referência 0,852. O desvio só aparece onde há empate. |
| "A equity de AA x top 10% (0,849) era anômala" | **Descartada** | Com as mesmas 16 classes, o simulador dá 0,840 e o original 0,851. AA domina quase todo o top 10%. |
| "A distribuição de cartas do oponente no original é enviesada" (pelo `randint(0, len−1)`) | **Não confirmada** | Qui-quadrado p = 0,099 em 40.000 distribuições (sem evidência de viés a 1%) |

### 12.5 Alterações realizadas

- **Nenhuma** alteração em `poker/` (motor, estratégia, scraper, GUI, licenciamento). Parâmetros da Trial 2 **inalterados**.
- Correções feitas **somente** no componente isolado `simulador/`: P1 a P7 estão corrigidos lá; P8 ficou só documentado.
- Arquivos novos: `simulador/**`, `auditoria/fase2_comparacao.md`, `CHANGELOG.md`. Arquivo atualizado: `PROJECT_STATUS.md`.

### 12.6 Classificação dos testes

| Categoria | Arquivos | Como rodar | Situação |
|---|---|---|---|
| **Unitários offline** | `simulador/tests/*` (88), `poker/tests/test_outs.py` (15), `poker/tests/test_montecarlo.py` (3 + 1 falha conhecida) | `python -m simulador.testes offline` (rápido) ou `offline-completo` | ✅ `offline-completo`: **106 aprovados**, 0 falhas, 1 falha conhecida excluída (3 min 50 s). `offline`: 104 aprovados, mais 1 falha conhecida quando incluída (`--incluir-falhas-conhecidas`). |
| **Dependentes de rede (só leitura)** | `test_table_and_ocr.py` (9), `test_tensorflow.py::test_load_nn_model` | `python -m simulador.testes rede --confirmar` | Não executados na Fase 2 (resultado da Fase 1: 10 aprovados) |
| **Desativados pelo autor** | `test_decision.py` (14), `test_reverseTables.py` (1) | — (skip no código) | Não executados |
| **Treinamento de rede neural** | `test_tensorflow.py::test_train_card_neural_network_and_predict` | `python -m simulador.testes treino --confirmar` | Não executado na Fase 2 (> 25 min na Fase 1) |
| **Proibido (envia dados)** | `test_tensorflow.py::test_save_model` | **nunca** (o executor sempre o exclui) | Não executado |

Na Fase 2 só foram executados testes offline; nenhum teste que envia dados ao servidor foi rodado.

### 12.7 Como reproduzir

Na pasta do projeto, no PowerShell:

```powershell
.\.venv\Scripts\python.exe -m simulador.testes listar
```
```powershell
.\.venv\Scripts\python.exe -m simulador.testes offline
```
```powershell
.\.venv\Scripts\python.exe -m simulador.testes offline-completo
```
```powershell
.\.venv\Scripts\python.exe -m simulador.comparacao
```

Exemplo de estudo no cenário de referência, salvo em um arquivo `.py` na pasta do projeto:

```python
from simulador.cenario import estudar_allin, ESTRUTURAS_RAKE_HIPOTETICAS
from simulador.ranges import Range

# Heroi no BB (investiu 0,10) com AKs, 150 BB; vilao no SB empurra 200 BB com top 15%
resultado, equity = estudar_allin("AS KS", Range.top(0.15), stack_heroi=15.0, stack_vilao=20.0,
                                  investido_heroi=0.10, rake=ESTRUTURAS_RAKE_HIPOTETICAS["5%_teto_3bb"],
                                  iteracoes=20000, semente=1)
print(equity.resumo(), resultado.ev_bb)
```

### 12.8 Limitações remanescentes

1. **O PokerBot continua usando o motor original** com os defeitos P1 a P7. O simulador é um ambiente de estudo à parte e não muda as decisões do robô.
2. O simulador calcula **equity e EV de decisões isoladas** (call, all-in). Ele não simula a árvore completa de apostas (várias streets, tamanhos de aposta, fold equity) nem as estratégias do Strategy Editor.
3. O rake é **hipotético** e simplificado: percentual + teto + "no flop, no drop", sem arredondamento de centavos e sem regras específicas de sala.
4. Desempenho: Python puro, cerca de 20 mil simulações por segundo heads-up; a enumeração exata pré-flop leva cerca de 1,5 min.
5. A ordenação de ranges usa a tabela `preflop_equity.json` do próprio projeto, que foi gerada pelo motor original (com empates contados como vitória). A ordem relativa das mãos é razoável, mas não é uma referência independente.
6. Os testes originais `test_decision.py` e `test_reverseTables.py` continuam desativados pelo autor e dependem do servidor.

### 12.9 Commits e pushes da Fase 2 (branch `master`)

| Commit | Conteúdo |
|---|---|
| tag `v6.76-auditoria-fase1` | Marca o estado auditado (`0163ef2`) |
| `23a13cf` | Avaliador de mãos independente + testes |
| `ccd4808` | Motor de equity, ranges e validação matemática |
| `ad45fe8` | Comparação motor original x simulador |
| `8fa067f` | Cenário 6-max, stacks efetivos, rake hipotético, isolamento |
| `5f76ac1` | Executor de testes por categoria |
| `47037f8` | Documentação: `PROJECT_STATUS.md` e `CHANGELOG.md` |

---

## 13. Fase 3: estabilidade, estratégias em simulação, janela do simulador e manual

### 13.1 Correções (erros comprovados)

| Problema comprovado | Evidência | Correção | Arquivo |
|---|---|---|---|
| Sem o servidor do autor, o PokerBot fechava com `requests.exceptions.ConnectionError` (texto técnico em inglês) | Execução com a rede bloqueada: traceback em `UpdateChecker.check_update` → `get_internal` | O atalho verifica o servidor antes de abrir e mostra uma mensagem em português, sugerindo o Simulador | `Abrir Pokerbot.bat`, `ferramentas/diagnostico.py` |
| Sem ferramenta de diagnóstico para leigos | — | `Diagnostico.bat`: Python, bibliotecas, OCR, `config.ini`, servidor (só conexão TCP, nada é enviado), controle do mouse e últimas linhas do log de erros | `Diagnostico.bat`, `ferramentas/diagnostico.py` |
| `config.ini` aponta o controle para a VM `w1064` (herdada do autor); sem VirtualBox, o Start gera erros em ciclo | `deepmind_pokerbot_errors.log`: `Library not registered` / `No virtual machine found` | **Não alterado** (mudar para mouse direto faria o robô mover o mouse real). O diagnóstico agora explica a situação. | — |
| `np.random.random_integers` está obsoleto (aviso; removido no NumPy 2) | `DeprecationWarning` nos testes | Trocado por `np.random.randint(0, len(Deck))`, que é equivalente e gera a mesma sequência aleatória | `poker/decisionmaker/montecarlo_python.py:234` |
| Teste original `test_monteCarlo` quebrado (`maxRuns`) | `TypeError` | Argumento renomeado para `max_runs`; o teste **passa** (4/4) | `poker/tests/test_montecarlo.py:160` |
| `.bat` com quebra de linha Unix | — | `.gitattributes` com `*.bat eol=crlf` | `.gitattributes` |

Os defeitos matemáticos do motor original (seção 12.3) **continuam no robô**, como decidido na Fase 2: o motor original é preservado como referência. As versões corrigidas estão no simulador.

### 13.2 O que a implementação realmente considera (confirmado no código)

| Aspecto | Existe no robô? | Como (evidência) |
|---|---|---|
| Posição UTG/HJ/CO/BTN/SB/BB | **Parcial** | Só como número `position_utg_plus` (0 = UTG … 5 = BB, `table_screen_based.py:396`); não há nomes de posição. No modo de equity, a posição reduz a equity mínima pré-flop de forma linear (`decisionmaker.py:106`). |
| Ranges por posição (próprios) | **Só com `preflop_override = 1`** | `preflop.xlsx` tem planilhas por posição e ação (`table.py:169-191`). Na Trial 2 e na Official 1 está **desligado**. A tabela tem 2 entradas mal formatadas (`A3`, `K7` na planilha `5C2`), que o robô nunca encontra. |
| Ranges por posição (adversários) | **Só heads-up pós-flop** | `range_utg0..5` (`montecarlo_python.py:320-326`); em multiway usa um único `range_multiple_players`. |
| Quantidade de adversários | **Parcial** | Pré-flop simulado sempre como heads-up; pós-flop com limite de 4 jogadores (seção 5.5). |
| Profundidade de stack | **Não** | Só `always_call_low_stack_multiplier`; limites absolutos (`initialFunds`). |
| Equity | **Sim, com defeitos** | Monte Carlo com empates contados como vitória (seção 12.3). |
| Pot odds | **Calculadas, não usadas** | `maxCallEV` só vai para o log (seção 5.2). |
| Agressividade pré-flop | **Sim** | Curvas `PreFlopBetPower`/`MinBetEquity`, `PreFlopMaxBetEquity` (slowplay), `increased_preflop_betting`. |
| Agressividade pós-flop | **Sim** | Curvas por street, `minimum_bet_size`, faixas de blefe, check deception, pot bet no river. |
| Rake | **Não** | Nenhuma referência no código. |
| Heads-up x multiway | **Sim, regras diferentes** | Blefe e ajuste por perfil do jogador só em heads-up (`decisionmaker.py:248,437`); range do adversário por posição só em heads-up. |

### 13.3 Estratégias em simulação offline (`auditoria/fase3_estrategias.md`)

Reprodução das regras do robô com a **função de curva original** e as equities do simulador validado. Pote não aberto, % das 1326 combinações que **aumentam**:

| Posição | Tabela do autor | Trial 2 (0,01/0,02) | Trial 2 (0,05/0,10) | Official 1 (0,01/0,02) | Official 1 (0,05/0,10) |
|---|---|---|---|---|---|
| UTG | 17,2% | 13,9% | 4,1% | 16,9% | 3,5% |
| HJ | 22,0% | 19,2% | 5,0% | 19,9% | 3,8% |
| CO | 28,8% | 23,5% | 6,9% | 25,5% | 5,6% |
| BTN | 40,3% | 27,1% | 6,9% | 27,6% | 7,2% |
| SB | 62,3% | 30,2% | 8,9% | 30,9% | 7,5% |

Conclusões:
1. A **tabela do autor** (`preflop.xlsx`) é a única configuração realmente posicional e tem perfil TAG (UTG ≈ 17%, BTN ≈ 40%). Ela fica desativada nas estratégias disponíveis.
2. A **Trial 2** em escala calibrada é tight, mas **não aumenta com AA e KK** (só paga, por causa de `PreFlopMaxBetEquity = 0,78`).
3. Na mesa **0,05/0,10** sem reescalar `bigBlind`, as duas estratégias ficam muito fechadas (≤ 9% de aumentos) e a Official 1 passa a dar muito limp (23–42%).
4. No flop, como agressor heads-up, a Trial 2 aposta por valor em 12–18% das vezes e blefa em ~39% (faixa fixa de equity), com check em 43–49%. O blefe ignora a textura do board.
5. Rake e stack não entram nas decisões. Com rake hipotético de 5% (teto 3 BB), a equity necessária para defender o BB contra 2,5 BB sobe de 30,0% para 31,6%.

**Parâmetros das estratégias do robô: não alterados** (salvar exige assinatura, e não foi pedido).

### 13.4 Configuração do ambiente de estudo (definida a partir dos resultados)

Arquivo `simulador/perfis/tag_6max_nl10.json`, gerado por `python -m simulador.analise_estrategias`:

| Parâmetro | Valor | Justificativa |
|---|---|---|
| Mesa | 0,05/0,10 · 6-max · até 200 BB | cenário pedido |
| Ranges de abertura | tabela do autor por posição (UTG 17,2% … SB 62,3%) | única fonte posicional do projeto, com perfil TAG |
| Ranges dos adversários | os mesmos ranges por posição, "qualquer mão" ou top X% | escolha na janela |
| Iterações | 9.000 heads-up / 8.000 multiway | erro padrão ≤ 0,005 medido (0,0073 e 0,0069 com 4.000) |
| Rake padrão | hipotético 5% com teto de 3 BB | estrutura comum de estudo; outras opções na janela |
| Stack padrão | 100 BB | — |
| Semente | 2026 | resultados reprodutíveis |

### 13.5 Janela do Simulador (sem terminal)

`Abrir Simulador.bat` abre `simulador/janela.py` (PyQt6, o mesmo kit gráfico do PokerBot):
- **Simulação:** mão, mesa, posição, de 1 a 5 adversários, range, pote, call, stacks, rake; botões **Iniciar / Pausar-Continuar / Parar**; barra de progresso; equity, vitória/empate, margem de erro, odds do pote, equity necessária com rake, EV do call, EV do all-in e se a mão está no range da posição;
- **Relatórios e manual:** exibe `MANUAL.md`, as análises das Fases 2 e 3, `PROJECT_STATUS.md` e `CHANGELOG.md`;
- **Testes:** roda os testes offline com um clique.

A interface original do PokerBot **não foi alterada**.

### 13.6 Testes

| Categoria | Resultado |
|---|---|
| Offline completo (`python -m simulador.testes offline-completo`, também pela aba Testes) | ✅ **124 aprovados, 0 falhas, nenhum teste excluído** (2 min 51 s), incluindo o `test_monteCarlo` original, agora corrigido |
| Dependentes de rede / treino de rede neural | Não executados nesta fase |
| `test_save_model` (envia dados) | Nunca executado |

### 13.7 Limitações remanescentes

1. O robô continua usando o motor original (defeitos P1 a P7 da seção 12.3) e as estratégias sem considerar rake e stack.
2. O simulador avalia decisões isoladas (call e all-in), não a mão inteira com todas as streets.
3. A análise pós-flop é aproximada: ignora outs e ajustes de segunda rodada, e o tamanho do pote é fixo.
4. O rake é hipotético; os ranges dos adversários vêm da tabela do autor, não de dados reais de jogadores.
5. Abrir o PokerBot, o Strategy Analyser, as mesas e as estratégias continuam dependendo do servidor do desenvolvedor.
6. O controle `w1064` continua no `config.ini`; o Start não controla nada sem VirtualBox.

### 13.8 Commits da Fase 3 (branch `master`)

| Commit | Conteúdo |
|---|---|
| `3f1ff0b` | Estabilidade: abertura sem servidor, diagnóstico, compatibilidade NumPy, teste original |
| `1bc92a2` | Análise offline das estratégias e perfil de estudo |
| `9c1f60d` | Janela do Simulador e `Abrir Simulador.bat` |
| (commit desta documentação) | Manual, documentação e relatório da Fase 3 regenerado |
