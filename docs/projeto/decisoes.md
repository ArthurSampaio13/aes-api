# Decisões de projeto

Cada decisão aqui registra **o que foi decidido**, **por quê**, e **o que
custa se estiver errada**. A terceira parte é a que importa: uma escolha sem
consequência declarada é uma preferência disfarçada de argumento.

## A saída da transcrição é estruturada, não texto puro

O modelo multimodal devolve o texto, uma declaração de ter chegado ao fim da
folha e a contagem de trechos ilegíveis, em vez de devolver só a transcrição.

**Por quê.** A alternativa — contar palavras e pedir nova tentativa quando são
poucas — pressiona o modelo a inventar texto do aluno. Num sistema de
correção, texto inventado contamina toda nota a jusante, e nada no resultado
denuncia isso.

**Custo se errada.** Uma redação legitimamente curta gasta uma chamada extra
de verificação. Do outro lado, uma transcrição truncada passaria caso o modelo
declarasse completude erradamente duas vezes seguidas.

## Folha em branco e folha ilegível não aceitam reafirmação

Só a regra de contagem de palavras aceita que o modelo reafirme e siga
adiante. As outras duas esgotam as tentativas e falham o job.

**Por quê.** Contagem de palavras tem falso positivo legítimo e o modelo pode
resolver a dúvida relendo. Folha em branco e folha ilegível não são julgamento
que uma segunda leitura desfaça — exigem um humano.

**Custo se errada.** Uma folha recuperável falha em vez de ser corrigida, e o
professor digita à mão algo que o sistema poderia ter lido.

## Retry em dois níveis

Falha de conteúdo é tratada dentro da execução pelo guardrail, com histórico e
instrução. Falha de infraestrutura é tratada pelo laço do worker, e cada volta
vira uma linha nova de tentativa.

**Por quê.** O retry informado é barato e eficaz: o modelo vê o que errou. O
retry externo é caro, porque refaz tudo sem contexto — mas é o único que
resolve queda de rede, onde não há conversa para continuar.

**Custo se errada.** Mover tudo para dentro faria cada tentativa deixar de ser
uma linha no banco, e a rastreabilidade por tentativa é exigência do projeto.
Mover tudo para fora transformaria cada correção rejeitada num novo sorteio
cego, pagando o prompt inteiro de novo.

## O pin de provedor vem desligado

`openrouter_provider.order` com `allow_fallbacks: false` existe, está
implementado e testado, mas não é o padrão.

**Por quê.** Com o pin ligado, a indisponibilidade do backend escolhido
derruba o job em vez de ser roteada para outro. Para uso corrente,
disponibilidade vale mais; para rodada experimental, reprodutibilidade vale
mais, e aí liga-se.

**Custo se errada.** Resultados não comparáveis entre execuções. O efeito é
mensurável: o guardrail de citações disparou 20, 9, 7 e 13 vezes sobre o mesmo
conjunto de 28 redações em quatro execuções (2026-09-19 e 2026-09-20,
deepseek-v4.1-flash).

## O custo gravado é o cobrado, com a procedência explícita

O sistema prefere o valor que o OpenRouter informa ter cobrado; a estimativa
por tabela de preços fica como reserva. `cost_source` registra qual dos dois
originou cada número.

**Por quê.** A estimativa não cobre todo modelo — para o `deepseek-v4.1-flash`
ela é nula — e a coluna de custo existe para análise. Misturar cobrado e
estimado sem dizer qual tornaria a soma da coluna sem significado.

**Custo se errada.** Nenhum relevante: a coluna diz qual é qual, e quem
analisa pode filtrar antes de somar.

## O tempo de visibilidade da fila é definido no código

O `VisibilityTimeout` do SQS é aplicado por recebimento, a partir da
configuração da aplicação, e não apenas pelos atributos da fila.

**Por quê.** A configuração de infraestrutura definia 900 segundos, mas a fila
foi recriada sem os atributos e a configuração não se aplicou — a fila operou
com o padrão de 30 segundos. Como uma correção leva mediana de 65 segundos
ponta a ponta, toda mensagem voltava a ficar visível no meio da execução e era
entregue de novo.

**Custo se errada.** Volta a duplicar execução. Antes da correção, o sistema
rodava 2,86 execuções por job e pagava por todas; depois, 1,00 (lotes
`3f675701` de 2026-09-19 e `f0b97f15` de 2026-09-20, deepseek-v4.1-flash).

## A documentação separa o projeto da plataforma herdada

`/docs` apresenta primeiro os documentos deste trabalho; a documentação do
boilerplate FastAPI de origem fica agrupada em "Referência da plataforma", em
inglês, sem tradução.

**Por quê.** Dos 48 documentos originais, 46 descreviam o boilerplate e a
capa do site anunciava o template. Ao mesmo tempo, esses documentos descrevem
infraestrutura que o sistema de fato usa, e apagá-los perderia informação
útil.

**Custo se errada.** Nenhum relevante: os documentos herdados continuam
acessíveis e linkáveis.

## Todo número medido carrega a rodada de onde veio

Valores nesta documentação aparecem com lote, data e modelo.

**Por quê.** Os números variam entre execuções, e alguns variam muito. Publicar
um valor como atemporal inventaria uma precisão que os dados não sustentam.
Este repositório já publicou uma configuração inerte por escrever contra
documentação em vez de medir — o commit `e335cda` é o registro disso.

**Custo se errada.** O texto fica mais pesado de ler. É o preço de não afirmar
mais do que se mediu.
