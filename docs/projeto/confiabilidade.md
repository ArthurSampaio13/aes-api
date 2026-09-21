# Confiabilidade

## A pergunta que dá para responder sem nota humana

A rota padrão para avaliar um corretor automático é comparar a nota da
máquina com a de professores e reportar concordância. Este trabalho não tem
nota humana de referência, nem terá: não há painel de corretores, nem
subconjunto rotulado. Toda estatística que exija rótulo está fora, e isso
inclui a maior parte do arcabouço consagrado de avaliação de escoramento
automático.

O que sobra é de outra natureza, e é real: **o sistema concorda consigo
mesmo?** Corrigir a mesma redação cinco vezes, sob condições fixas, e medir
quanto a nota se move não diz se a nota está certa — diz se ela é
reprodutível. Um corretor que devolve notas diferentes para o mesmo texto não
pode estar certo de forma estável, então a confiabilidade é um teto para
qualquer validade futura, e mede-se sem rótulo nenhum.

Esta página registra o que foi medido, como, e o que cada número autoriza
dizer.

## O desenho

**Corpus.** 94 redações manuscritas de quatro turmas de 9º ano da mesma
escola, todas respondendo à mesma proposta (artigo de opinião sobre a criação
de um abrigo para animais na cidade). Mediana de 73 palavras por redação,
variando de 21 a 148.

| turma | redações | lote       |
| ----- | -------- | ---------- |
| 9ºA   | 28       | `e4d508d6` |
| 9ºB   | 29       | `7c7c395b` |
| 9ºC   | 20       | `f6dd1865` |
| 9ºD   | 17       | `cda91f62` |

**Procedimento.** Cada folha foi transcrita **uma vez** e corrigida **cinco
vezes** sobre a mesma transcrição, via `POST /batches/{id}/corrections`. Essa
separação é o centro do desenho: se cada repetição passasse pelo OCR de novo,
a variação observada misturaria transcrição e correção, e nenhuma das duas
ficaria isolável. O que se mede aqui é a variação do **corretor**.

**Condições**, exatamente como gravadas em `inference_params` de cada
tentativa:

```json
{ "temperature": 0.0, "seed": 42,
  "openrouter_cache_instructions": "5m",
  "openrouter_provider": { "data_collection": "deny" } }
```

Modelo `deepseek/deepseek-v4.1-flash`, rubrica versão 1, template de prompt
versão 1, 470 correções aceitas em 478 tentativas, nenhuma falha. Data:
2026-09-20.

**O pin de provedor estava desligado** (`AES_OPENROUTER_PROVIDER_ORDER`
vazio), o que importa para ler o resultado — ver
[O backend não foi controlado](#o-backend-nao-foi-controlado-ele-so-nao-variou).

## Confiabilidade teste-reteste

ICC(2,1): duas vias, efeitos aleatórios, concordância absoluta, medida única —
o coeficiente indicado quando as execuções são amostra de uma população de
execuções possíveis e interessa o valor absoluto da nota, não só a ordenação.
O intervalo é de **bootstrap percentil** sobre as redações, não a fórmula
analítica com F: a analítica pressupõe normalidade, e nota de rubrica 0–10 é
ordinal e truncada.

| critério            | ICC(2,1) | IC 95%         | SEM  | idênticas nas 5 | amplitude média |
| ------------------- | -------- | -------------- | ---- | --------------- | --------------- |
| `coesao_coerencia`  | 0,874    | \[0,83; 0,91\] | 0,59 | 18%             | 1,07            |
| `vocabulario`       | 0,866    | \[0,81; 0,90\] | 0,59 | 14%             | 1,14            |
| `adequacao_ling`    | 0,863    | \[0,81; 0,90\] | 0,53 | 20%             | 0,99            |
| `adequacao_tema`    | 0,854    | \[0,79; 0,90\] | 0,80 | 7%              | 1,53            |
| `estrutura_textual` | 0,819    | \[0,76; 0,86\] | 0,63 | 10%             | 1,28            |

Desenho completo: nenhuma redação ficou fora por falta de nota em alguma
execução.

O **SEM é a forma comunicável do resultado**: o sistema reproduz a própria
nota dentro de cerca de meio ponto numa escala de 0 a 10. `adequacao_tema` é
o critério de maior erro absoluto; `estrutura_textual`, o menos estável.

Uma medição anterior, com 28 redações de outro corpus, deu ICC entre 0,898 e
0,926. Os valores aqui são menores, e são estes que valem: com n=94 a
amostra passa das 30 que a literatura de ICC recomenda, e os intervalos são
bem mais estreitos. Estimativa de confiabilidade com n pequeno tende ao
otimismo.

### O teto que isso estabelece

Pela correção para atenuação, nenhuma concordância com corretores humanos
acima de √ICC seria alcançável neste sistema — algo entre **0,91 e 0,93**,
conforme o critério. É uma afirmação forte obtida sem rótulo nenhum, e é
útil de antemão: define o que seria um resultado impossível num estudo de
validação futuro.

## Como as notas se distribuem

Cada redação entra pela média das suas cinco execuções, o que reduz o ruído
de execução antes de olhar a distribuição.

| critério            | média | dp   | mín | q1  | mediana | q3  | máx |
| ------------------- | ----- | ---- | --- | --- | ------- | --- | --- |
| `adequacao_tema`    | 4,54  | 1,97 | 0,0 | 3,3 | 4,7     | 6,2 | 8,4 |
| `vocabulario`       | 3,01  | 1,52 | 0,2 | 2,0 | 2,7     | 4,0 | 7,4 |
| `coesao_coerencia`  | 2,83  | 1,59 | 0,0 | 1,8 | 2,4     | 4,2 | 6,2 |
| `estrutura_textual` | 2,66  | 1,38 | 0,0 | 1,8 | 2,4     | 3,6 | 6,2 |
| `adequacao_ling`    | 2,40  | 1,37 | 0,0 | 1,4 | 2,1     | 3,4 | 6,8 |
| média dos critérios | 3,09  | 1,51 | 0,1 | 2,1 | 2,9     | 4,3 | 5,9 |

**As notas são baixas e comprimidas na base.** Mediana geral 2,9 de 10, três
quartos das redações abaixo de 4,3, nenhuma média passando de 5,9. Há notas
zero.

Isso admite duas explicações — as redações são de fato fracas, ou o sistema é
severo por construção — e **sem referência externa elas são
indistinguíveis**. Essa é a limitação mais séria do trabalho, e é o que
impede tratar a nota como número, mesmo indicativo. Calibração de nível
absoluto exige referência que este projeto não tem.

As turmas se ordenam de forma consistente, sem uma única inversão entre os
cinco critérios:

| turma | n   | `tema` | `estrutura` | `coesão` | `ling` | `vocab` | geral |
| ----- | --- | ------ | ----------- | -------- | ------ | ------- | ----- |
| 9ºB   | 29  | 5,38   | 3,31        | 3,52     | 2,89   | 3,59    | 3,74  |
| 9ºA   | 28  | 4,88   | 2,77        | 3,04     | 2,72   | 3,36    | 3,35  |
| 9ºC   | 20  | 3,81   | 2,17        | 2,35     | 1,90   | 2,48    | 2,54  |
| 9ºD   | 17  | 3,41   | 1,94        | 1,88     | 1,64   | 2,07    | 2,19  |

Que o sistema discrimine grupos é encorajador. Que os ordene **corretamente**
é outra afirmação, e essa não se sustenta sem validação.

## A rubrica entrega um sinal, não cinco

Correlação de Spearman entre os critérios, sobre a média das execuções por
redação — posto, e não Pearson, porque nota de rubrica é ordinal.

|                     | `tema` | `estrutura` | `coesão` | `ling` | `vocab` |
| ------------------- | ------ | ----------- | -------- | ------ | ------- |
| `adequacao_tema`    | 1,00   | 0,96        | 0,97     | 0,91   | 0,93    |
| `estrutura_textual` | 0,96   | 1,00        | 0,95     | 0,88   | 0,91    |
| `coesao_coerencia`  | 0,97   | 0,95        | 1,00     | 0,94   | 0,95    |
| `adequacao_ling`    | 0,91   | 0,88        | 0,94     | 1,00   | 0,97    |
| `vocabulario`       | 0,93   | 0,91        | 0,95     | 0,97   | 1,00    |

Correlação média entre pares: **0,94**, nenhum par abaixo de 0,88. O mesmo
padrão apareceu num corpus independente de 28 redações, com média idêntica.

Os cinco critérios declarados produzem, nas saídas deste sistema,
aproximadamente **uma dimensão**. As médias por critério diferem — o sistema
desloca o nível — mas a ordenação das redações é quase a mesma em todos eles.

Isso replica um achado documentado em corretores humanos: escores analíticos
humanos de redação raramente distinguem mais de duas dimensões. Replicar um
limite conhecido da correção analítica não é o mesmo que estar livre dele, e
a consequência para o produto é concreta: o feedback separado por critério
pode sugerir ao professor um diagnóstico diferenciado que os números não
sustentam.

O que isso **não** prova: que os cinco construtos sejam indistinguíveis nos
alunos, nem que a rubrica seja pedagogicamente inadequada. Prova que, como
aplicada aqui, ela é estatisticamente redundante.

## Ancoragem das justificativas

Em **120 das 478 tentativas** — cerca de uma em quatro — o modelo tentou
citar trecho que não aparecia no texto do aluno, e o guard de citações
rejeitou a tentativa antes da entrega. Nenhuma correção aceita contém citação
inventada.

Este é o resultado mais sólido do conjunto, porque o oráculo é
determinístico: a verificação é de presença literal do trecho no texto-fonte,
não julgamento. O número não é contestável.

O que ele mede é a taxa em que o sistema atribui ao aluno texto que ele não
escreveu. O que ele **não** mede é se as justificativas ancoradas são
pedagogicamente corretas ou úteis — uma justificativa pode citar corretamente
e ainda assim não ajudar ninguém.

## O backend não foi controlado; ele só não variou

Com o pin desligado, o OpenRouter escolheu livremente quem atenderia cada
chamada. O que ficou gravado em `served_provider`:

| etapa       | backends                      |
| ----------- | ----------------------------- |
| correção    | DeepInfra nas 478 tentativas  |
| transcrição | Alibaba em 90, DeepInfra em 4 |

Duas leituras, ambas necessárias:

**O roteador varia de fato.** Na transcrição ele alternou entre dois
provedores sem que nada na entrada mudasse. Não é risco teórico.

**Na correção, ele não variou** — e é isso que dá força ao resultado
principal. Com o mesmo modelo, a mesma seed, temperatura zero e **o mesmo
backend** atendendo todas as 478 tentativas, a nota ainda oscila: de 80% a
93% das redações receberam ao menos duas notas diferentes entre as cinco
execuções, conforme o critério. A instabilidade não vem do roteamento; vem da
inferência. "Mesmo modelo, mesma seed" não é condição experimental
determinística.

A ressalva honesta: o backend único foi **observado, não imposto**. Repetir
este experimento pode não reproduzir a mesma condição. Para uma rodada em que
a comparabilidade precise ser garantida, e não constatada depois, o pin
existe e deve ser ligado — ver [OpenRouter](openrouter.md).

## Custo e tempo

Medido nos quatro lotes, 2026-09-20:

| etapa                     | custo          |
| ------------------------- | -------------- |
| transcrição (94 folhas)   | US$ 0,2548     |
| correção (478 tentativas) | US$ 0,5373     |
| **total do experimento**  | **US$ 0,7922** |

Por unidade: US$ 0,0027 por transcrição, US$ 0,0011 por correção. Corrigir
uma turma de 28 redações uma vez custa cerca de **US$ 0,11** — e a
transcrição responde por 71% disso. Processar a imagem de uma folha
manuscrita continua mais caro que avaliar o texto extraído dela.

Latência: correção com mediana de 37,8 s, p95 de 90,7 s e cauda até 154 s;
transcrição com mediana de 11,7 s e máximo de 26 s. É por isso que a correção
é assíncrona.

## Como reproduzir

```bash
# envio único: transcreve uma vez, corrige a primeira vez
PROVIDER=openrouter MODEL=deepseek/deepseek-v4.1-flash \
  RUN_LABEL=run-1 LABEL_PREFIX=9A- \
  scripts/enviar-redacoes.sh <essay_prompt_uuid> 'pasta/*.pdf'

# execuções 2..5 sobre as mesmas transcrições, e exporta o manifesto
PROVIDER=openrouter MODEL=deepseek/deepseek-v4.1-flash \
  scripts/experimento.sh <batch_id> 5

# análise
scripts/analise-teste-reteste.py .local/manifests/<batch>.json ...
scripts/analise-distribuicao.py  .local/manifests/<batch>.json ...
```

Os dois scripts de análise rodam em stdlib puro, sem dependência externa, e
trazem `--autoteste`: o de confiabilidade confere o ICC contra o conjunto
publicado de Shrout e Fleiss (1979), cujo ICC(2,1) conhecido é 0,290; o de
distribuição confere o Spearman contra o exemplo de QI × horas de televisão
da Wikipédia, ρ = −0,1758. Rodar o autoteste antes de confiar num número é
barato.

Um **pacote de evidência** do experimento é mantido fora do repositório, com
os quatro manifestos, as trocas cruas de cada tentativa, as saídas das
análises, o estado exato do código que produziu os dados e somas SHA-256 de
tudo. Ele contém texto de aluno e por isso não é versionado nem publicado; os
números agregados desta página são o que dele se cita.

O corpus **não está versionado**: são redações manuscritas de alunos
identificáveis. Os manifestos exportados ficam em `.local/`, fora do git, e
os rótulos das redações são numerados (`9A-01`) em vez de derivados do nome
do arquivo, porque nome de folha digitalizada costuma carregar nome de aluno.

## O que este conjunto de medidas não estabelece

Vale repetir, porque é o limite do trabalho e não uma nota de rodapé:

- **Acerto.** ICC alto significa repetível. Um sistema pode repetir a mesma
  nota errada com precisão admirável.
- **Calibração.** Nada aqui diz se o nível absoluto das notas está certo, e a
  distribuição concentrada na base é exatamente onde isso pesa.
- **Ordenação correta** de redações reais entre si.
- **Eficácia pedagógica.** Nenhuma medida aqui envolveu professor ou aluno
  usando o sistema.
- **Os cortes usuais de ICC** (0,75 e 0,9 como "bom" e "excelente") vêm de
  medição clínica e não foram validados para escorador baseado em modelo de
  linguagem. Aplicá-los é transferir um corte de outro domínio, e a
  transferência precisa ser declarada como tal.

A posição que os dados sustentam é **confiável mas não validado**. É uma
posição científica respeitável. "Confiável, logo bom" não é, e a distância
entre as duas frases é o que esta página existe para preservar.
