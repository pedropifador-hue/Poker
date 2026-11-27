# CHANGELOG

Registro das mudanças feitas neste fork (`pedropifador-hue/Poker`). O código original do PokerBot (`poker/`) não foi modificado, exceto onde indicado.

## [Fase 2] 27/11/2026 — Validação matemática e simulador offline

### Adicionado
- `simulador/`: ambiente de simulação **offline e isolado** (sem rede, sem conluio, sem controle de tela, sem importar o PokerBot):
  - `avaliador.py`: avaliador de mãos de 5 a 7 cartas, independente do original;
  - `equity.py`: Monte Carlo reprodutível (semente), empates divididos 1/k, 2 a 10 jogadores, enumeração exata;
  - `ranges.py`: ranges por combinações (padrão) e por classes (modo do original);
  - `cenario.py`: mesa 6-max 0,05/0,10, stack máximo de 200 BB, stack efetivo, odds do pote, equity necessária, EV de call/all-in e rake hipotético;
  - `seguranca.py`: bloqueio de rede para os testes;
  - `comparacao.py`: relatório antes/depois em `auditoria/fase2_comparacao.md`;
  - `testes.py`: executor de testes por categoria (offline, rede, treino, desativados, proibidos);
  - `tests/`: 88 testes de validação matemática, cenário, isolamento e comparação.
- `auditoria/fase2_comparacao.md`: evidências comparativas motor original x simulador.
- Tag `v6.76-auditoria-fase1` apontando para o estado auditado (`0163ef2`).

### Corrigido (somente no simulador isolado; o motor original foi preservado)
- Empates contados como vitória → agora divididos proporcionalmente.
- Straight flush desempatado por carta extra → corrigido.
- Desempate errado com quadra no board → corrigido.
- Mãos sorteadas fora do range (~17%) → 100% dentro do range.
- Range medido em classes → medido em combinações (modo antigo disponível).
- Número de adversários limitado/forçado a heads-up → informado explicitamente (2 a 6 em 6-max).
- Resultados não reprodutíveis → semente explícita.

### Documentado
- `PROJECT_STATUS.md`, seção 12: validações, problemas confirmados, hipóteses descartadas, classificação dos testes, comandos e limitações.

### Não alterado
- Parâmetros da Trial 2 e de qualquer estratégia.
- Mecanismos de assinatura/licenciamento.
- Qualquer arquivo em `poker/`.

## [Fase 1] 27/11/2026 — Instalação e auditoria

### Alterado
- `requirements_win.txt`: removido `fastapi_auth` (inexistente no PyPI e não usado); adicionado `pywin32` (controle do mouse no Windows).
- `.gitignore`: ignora `.venv/`.

### Adicionado
- `Instalar.bat` e `Abrir Pokerbot.bat`: instalação e abertura com dois cliques (Python 3.11 em `.venv`).
- `PROJECT_STATUS.md`: auditoria técnica e estratégica (seções 1 a 11).
- `auditoria/`: snapshot das estratégias Trial 2 / Official 1 e scripts de verificação offline.

Commits: `6ad6b46` (instalação), `0163ef2` (auditoria).
