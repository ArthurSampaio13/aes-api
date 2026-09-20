# OpenRouter

## O que é um roteador de modelos

O OpenRouter é um intermediário entre a aplicação e os provedores de modelos
de linguagem. Em vez de integrar separadamente com OpenAI, Anthropic,
DeepSeek e cada outro fornecedor — cada um com sua credencial, seu formato de
requisição e suas particularidades — a aplicação fala com uma única API e
escolhe o modelo pelo nome na própria requisição.

## Por que não falar direto com um provedor

Três razões, em ordem de importância para este trabalho.

**Trocar de modelo vira configuração, não código.** Um trabalho que precisa
comparar modelos não pode ter o modelo soldado na implementação. Aqui, o
modelo de correção e o de transcrição são variáveis de ambiente, e a rota de
submissão aceita o modelo por parâmetro. Comparar dois modelos sobre o mesmo
conjunto de redações não exige recompilar nada.

**Uma credencial em vez de várias.** Menos segredo para gerenciar, menos
superfície para vazar.

**Um formato de resposta.** O código que interpreta a resposta do modelo não
muda quando o modelo muda.

## O que isso custa

Roteamento tem um preço que só aparece quando se olha os dados.

No lote `3f675701` (2026-09-19), o mesmo modelo foi servido por **dois
backends diferentes** dentro de uma única execução: `DeepInfra` e `Wafer`. O
OpenRouter distribui carga entre provedores que hospedam o mesmo modelo, e
esses provedores podem diferir em quantização e em configuração de inferência.

A consequência é direta: a mesma requisição, com a mesma temperatura e o
mesmo seed, pode produzir saídas diferentes dependendo de quem atendeu.

Isso é visível nos dados. O guardrail de citações disparou 20, 9, 7 e 13 vezes
em quatro execuções do mesmo conjunto de 28 redações (2026-09-19 e 2026-09-20,
deepseek-v4.1-flash) — uma variação por fator de quase três, sem que nada na
entrada tivesse mudado.

### O que o sistema faz a respeito

Toda chamada carrega três configurações relacionadas a isso:

- **`seed`** fixo, para que o provedor que o honrar produza saída estável.
- **`openrouter_provider.order`** com **`allow_fallbacks: false`**, que fixa
  qual backend atende. Isso vem **desligado** por padrão: é uma escolha de
  disponibilidade sobre reprodutibilidade, porque com o pin ligado a queda do
  backend escolhido derruba o job em vez de ser roteada para outro.
- **`data_collection: deny`**, para que nenhum provedor que retenha dados
  receba a folha. A folha digitalizada traz o nome do aluno.

Para uma rodada experimental que precise de resultados comparáveis, ligar o
pin deixa de ser opcional.

## Prompt caching

O template de prompt tem duas partes: um prefixo estável — as instruções da
rubrica, iguais para toda redação do mesmo lote — e um sufixo que muda, que é
a redação do aluno.

O sistema separa os dois e envia o prefixo como instruções, marcadas para
cache. Provedores que suportam cacheamento de prefixo cobram menos pelos
tokens repetidos.

Medido: numa tentativa típica, 768 dos 1.053 tokens de entrada vieram do
cache (lote `3f675701`, 2026-09-19).

Vale registrar como essa configuração chegou aqui. Ela já esteve no código e
foi **removida** no commit `e335cda`, com a justificativa de não funcionar. A
causa nunca foi investigada na época: o campo não existia na versão da
biblioteca então instalada, e por isso era inerte. Só passou a funcionar com a
atualização da biblioteca, e hoje há um teste de regressão que verifica que o
marcador de cache realmente chega ao corpo da requisição.

É o exemplo mais claro do princípio que este conjunto de documentos adota:
afirmação sobre comportamento precisa de medição, não de leitura de
documentação.

## Custo

O OpenRouter informa, em cada resposta, quanto cobrou pela chamada. É esse
valor que o sistema grava.

Existe também uma estimativa calculada por tabela de preços da biblioteca,
usada como reserva — mas ela não precifica todo modelo, e para o
`deepseek-v4.1-flash` devolve nulo. A coluna `cost_source` registra qual dos
dois originou o número, de modo que somar a coluna seja uma operação com
significado.

Medido no lote `f0b97f15` (2026-09-20, deepseek-v4.1-flash), com 28 redações:

| etapa              | custo          |
| ------------------ | -------------- |
| transcrição        | US$ 0,0656     |
| correção           | US$ 0,0383     |
| **total da turma** | **US$ 0,1039** |

O contraintuitivo está aí: **a transcrição custa mais que a correção**,
representando cerca de 63% do total. Processar a imagem de uma folha
manuscrita é mais caro que avaliar o texto extraído dela.

Para dimensionar: corrigir uma turma de 28 redações custou aproximadamente dez
centavos de dólar.
