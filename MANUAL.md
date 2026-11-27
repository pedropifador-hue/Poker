# Manual de uso (para iniciantes)

Este projeto tem **dois programas**, e cada um abre com dois cliques num arquivo da pasta do projeto (a pasta `Poker`, dentro da sua pasta de usuário do Windows):

| Arquivo | O que abre | Precisa de internet? |
|---|---|---|
| **Abrir Simulador.bat** | **Simulador Offline**: estudo de equity, pot odds, stacks e rake com mãos simuladas | **Não** |
| **Abrir Pokerbot.bat** | **PokerBot original** (interface do desenvolvedor) | **Sim**, precisa do servidor do desenvolvedor |
| **Diagnostico.bat** | Verifica se está tudo instalado e funcionando | Só para testar o servidor |
| **Instalar.bat** | Reinstala as bibliotecas (só se algo quebrar) | Sim |

> ⚠️ **Aviso importante.** O PokerBot original foi feito para jogar sozinho em salas reais (PokerStars, PartyPoker, GGPoker). Essas salas proíbem robôs: a conta pode ser banida e o saldo retido. O PokerBot **não tem modo de simulação**. Para estudar e simular, use o **Simulador Offline**.

---

## 1. Simulador Offline (recomendado para estudo)

### Como abrir
Dê dois cliques em **Abrir Simulador.bat**. A janela abre em alguns segundos. Ela não precisa de internet e não mexe no mouse nem em outros programas.

### Aba "Simulacao"
1. **Mãos e mesa**
   - **Sua mão:** duas cartas separadas por espaço. Valor: `2`–`9`, `T` (10), `J`, `Q`, `K`, `A`. Naipe: `S` espadas, `H` copas, `D` ouros, `C` paus. Exemplo: `AS KD` = Ás de espadas e Rei de ouros.
   - **Cartas na mesa:** deixe vazio para o pré-flop, ou informe 3, 4 ou 5 cartas (ex.: `7H 8D 2C`).
   - **Sua posição:** UTG, HJ, CO, BTN, SB ou BB. O resultado mostra se a sua mão está no range de abertura dessa posição.
   - **Adversários na mão:** de 1 a 5 (mesa 6-max).
   - **Range dos adversários:** "Qualquer mão", o range de abertura de uma posição (tabela do desenvolvedor) ou "Top X%".
2. **Pote, stacks e rake** (valores em BB; 1 BB = R$ 0,10)
   - **Pote antes do seu call** e **Valor para pagar**: servem para calcular as odds do pote e o EV.
   - **Seu stack** e **Stack do adversário:** de 1 a 200 BB. O stack efetivo é o menor dos dois.
   - **Rake:** estruturas **hipotéticas** para comparação (sem rake, 5% com teto de 3 BB etc.).
3. **Simulação**
   - **Iterações:** quantas mãos serão simuladas. O padrão (9.000) dá cerca de ±1% de precisão.
   - **Semente:** com o mesmo número, o resultado se repete exatamente.
   - **Iniciar** começa; **Pausar** congela e o mesmo botão vira **Continuar**; **Parar** encerra antes do fim e mantém o resultado parcial.

### Como acompanhar os resultados
O quadro **4. Resultado** é atualizado durante a simulação:
- **Equity:** sua fração média do pote (vitórias + parte dos empates), com a margem de erro;
- **Vitória / Empate:** probabilidades separadas;
- **Odds do pote / Equity necessária com rake:** quanto você precisa vencer para o call valer a pena;
- **EV do call:** ganho ou perda médio em BB e em R$ (verde = lucrativo no longo prazo);
- **All-in heads-up:** stack efetivo, rake e EV de um all-in (só com 1 adversário).

### Aba "Relatorios e manual"
Mostra este manual, a análise das estratégias (Trial 2 e Official 1), a comparação entre o motor original e o simulador, a situação do projeto e o histórico de mudanças.

### Aba "Testes"
O botão **Rodar testes offline** confere tudo automaticamente (cerca de 1 minuto). Ao final aparece "TODOS OS TESTES PASSARAM" ou a lista do que falhou.

### Como encerrar
Feche a janela no **X**.

---

## 2. PokerBot original (interface do desenvolvedor)

### Como abrir
Dê dois cliques em **Abrir Pokerbot.bat**. Uma janela preta (console) abre primeiro e, depois de uns 30 segundos, a janela **Pokerbot**. **Não feche a janela preta:** ela é parte do programa.
- Se o servidor do desenvolvedor não responder, aparece a mensagem **"PokerBot - servidor indisponivel"**. Tente mais tarde, ou use o Simulador.

### Como selecionar uma estratégia
Na janela principal, use a caixa de seleção de estratégia (lista com "Official 1", "Trial 1", "Trial 2", "Trial 3"). A escolha é salva em `poker/config.ini` e vale para a próxima vez.

### Como acessar as configurações
- **Settings:** controle do mouse (mouse direto ou máquina virtual VirtualBox), tempo limite e login. O login padrão é `guest`; **não informe senhas de outros serviços aqui**.
- **Strategy Editor:** mostra todos os parâmetros da estratégia (os significados estão em `PROJECT_STATUS.md`, seção 3). Você pode **ver** e mexer nos controles, mas **salvar exige assinatura paga**; nenhuma compra foi ou será feita por mim.
- **Table Setup:** ensina o robô a reconhecer uma mesa nova (trabalho manual, com capturas de tela do cliente de poker).
- **Strategy Analyser:** gráficos de desempenho das estratégias (dados vêm do servidor do desenvolvedor).
- **Documentation:** ajuda original (em inglês).

### Iniciar, pausar e encerrar
- **Start:** o robô começa a ler a tela, procurando a mesa de poker configurada. Se a opção **"Act automatically"** estiver marcada, ele **clica sozinho**. Desmarcada (padrão), ele calcula a decisão e espera você apertar Enter na janela preta.
- **Stop:** pausa o robô.
- **Encerrar:** feche a janela Pokerbot e a janela preta.

> Neste computador, o controle está configurado para uma máquina virtual chamada `w1064` (herdada da configuração do desenvolvedor), e o VirtualBox **não está instalado**. Por isso, ao apertar Start, o robô só registra erros e **não controla nada**. O Diagnóstico avisa sobre isso.

### Como acompanhar
O painel mostra a última decisão, a equity calculada, os limites de call e bet, as cartas reconhecidas, etc. Os registros ficam em `poker/log/` (o arquivo `deepmind_pokerbot_errors.log` guarda só os erros).

---

## 3. Como identificar e resolver erros

1. Dê dois cliques em **Diagnostico.bat**. Cada item aparece como `[OK ]` ou `[ERRO]`, e o resultado fica salvo em `diagnostico.txt`.
2. Problemas comuns:

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| "PokerBot - servidor indisponivel" | Sem internet, firewall ou servidor do desenvolvedor fora do ar | Tentar mais tarde; usar o Simulador |
| Janela preta mostra "Ambiente nao encontrado" | Pasta `.venv` apagada | Dois cliques em `Instalar.bat` |
| `[ERRO] Biblioteca ...` no diagnóstico | Instalação incompleta | Dois cliques em `Instalar.bat` |
| `[ERRO] Controle do mouse` | Máquina virtual configurada sem VirtualBox | Normal neste computador; só importa se você quiser usar o robô |
| "Strategy not available" / estratégia volta para "Default" | Estratégia não liberada para o login `guest` | Escolher Official 1 ou Trial 1–3 |
| "To save strategies you need to purchase a subscription" | Salvar estratégias é pago | Não salvar; usar o Simulador para estudos |
| Simulador: "Entrada invalida" | Carta digitada errada ou repetida | Usar o formato `AS KD` |
| Aba Testes: "HA FALHAS" | Algum teste falhou | Copiar o texto da aba e me enviar |

---

## 4. O que exige o servidor do desenvolvedor

Precisam de conexão com `dickreuter.com:7778`: abrir o PokerBot original, a lista e o conteúdo das estratégias, salvar estratégias (pago), mapas de mesas (Table Setup), a rede neural de cartas, o Strategy Analyser, a verificação de atualização e o registro das mãos jogadas (enviado ao servidor).

**Funcionam sem o servidor:** o Simulador Offline inteiro, os testes offline e o Diagnóstico (exceto a verificação do servidor).

## 5. O que exige intervenção manual

- **Login no GitHub** no navegador, quando o Windows pedir, para enviar alterações.
- **Instalar VirtualBox, criar a máquina virtual e escolher o controle em Settings**, se um dia quiser que o robô controle algo (não recomendado em salas reais).
- **Table Setup:** mapear mesas novas exige capturas de tela e cliques seus.
- **Assinatura paga** para salvar estratégias: decisão sua; não foi feita.
- **Firewall/antivírus:** pode pedir autorização na primeira vez que o PokerBot acessar a internet.
- **Apertar Start e Stop** no PokerBot é sempre uma ação sua.
