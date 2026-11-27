# PROJECT_STATUS — Auditoria técnica e estratégica do DeeperMind PokerBot

- **Data:** 27/11/2026
- **Repositório:** https://github.com/pedropifador-hue/Poker (fork de `dickreuter/Poker`)
- **Versão do programa:** 6.76 (`poker/main.py:43`)
- **Escopo:** apenas leitura e documentação. **Nenhuma estratégia, regra de licenciamento ou arquitetura foi alterada.**

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
| Branch de desenvolvimento | Na confirmação desta etapa foi escolhido **manter o trabalho no `master`**; nenhuma branch nova foi criada |
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
