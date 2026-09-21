# Visão geral

## O problema

No Ensino Fundamental, corrigir redação é lento, repetitivo e difícil de
manter consistente. A correção depende de leitura manual folha por folha, o
que limita a frequência com que cada aluno recebe retorno detalhado sobre a
própria escrita — e dificulta enxergar que dificuldades se repetem numa turma
inteira.

Este sistema existe para dar ao professor um ponto de partida: transcrever a
folha digitalizada, avaliar segundo uma rubrica configurável e devolver
feedback por critério, com o caminho inteiro registrado.

## O que o sistema recusa fazer

O sistema **não corrige sozinho**. Todo resultado nasce com
`requires_teacher_review` verdadeiro, e esse campo é exposto no manifesto de
auditoria — não é uma flag interna que se possa ignorar sem deixar rastro.

Também não é um corretor de ENEM, não é um chatbot, e não produz nota final.
O que ele entrega é um rascunho rastreável que um professor revisa, aceita ou
descarta.

Essa fronteira não é retórica: ela determina decisões concretas de desenho
descritas em [Guardrails](guardrails.md) e em
[Decisões de projeto](decisoes.md). Quando um guardrail não consegue
garantir a qualidade de uma transcrição, o sistema **falha o job** em vez de
corrigir o que conseguiu ler.

## O caminho de uma redação

O professor envia um lote de folhas digitalizadas — até 50 arquivos por
requisição, em JPG, PNG ou PDF de até 10 MB cada. Cada folha vira uma
submissão, e cada submissão vira um job de correção assíncrono.

O worker pega o job da fila. Se a submissão é imagem, um modelo multimodal
transcreve o manuscrito. A transcrição passa por um guardrail que cruza a
contagem de palavras com o que o próprio modelo declara sobre ter chegado ao
fim da folha; se os dois discordam, o modelo é chamado de novo para
verificar.

Com o texto em mãos, um segundo modelo avalia a redação contra a rubrica,
produzindo saída estruturada e validada: nota e justificativa para cada um
dos cinco critérios, mais feedback e uma sugestão acionável. Dois guardrails
examinam essa saída — um recusa citação que não aparece na redação do aluno,
outro recusa justificativa repetida entre critérios.

Cada tentativa é gravada com as condições completas que a produziram. O
resultado aceito fica disponível para o professor revisar, e o lote inteiro
pode ser exportado como manifesto de auditoria.

A correção é assíncrona porque é lenta: mediana de 37,8 segundos, p95 de 90,7
e cauda de 154 segundos só na etapa de correção (478 correções, 2026-09-20).
Prender uma requisição HTTP nisso não é viável, e um lote pode ter 50 folhas.

## Por onde seguir

[**Arquitetura**](arquitetura.md) — que peças existem, por que essas, e por
que o isolamento entre municípios é política no banco em vez de filtro na
aplicação.

[**Processo de correção**](processo-de-correcao.md) — o caminho completo em
diagrama, as quatro entidades do domínio e a topologia de retry em dois
níveis, que é a decisão menos óbvia do sistema.

[**Guardrails**](guardrails.md) — o que cada guard verifica, por que existe, e
por que a saída da transcrição é estruturada em vez de texto puro.

[**OpenRouter**](openrouter.md) — o que é um roteador de modelos, o que ele
resolve, o que custa em reprodutibilidade, e quanto custa em dinheiro.

[**Rastreabilidade**](rastreabilidade.md) — o que fica gravado em cada
tentativa e como ler o manifesto de um lote.

[**Confiabilidade**](confiabilidade.md) — o experimento de teste-reteste, o
que as notas fazem quando a mesma redação é corrigida cinco vezes, e o que
esses números autorizam afirmar.

[**Decisões de projeto**](decisoes.md) — as escolhas de desenho e o que cada
uma custa se estiver errada.
