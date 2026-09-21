# Guardrails

Um guardrail é uma verificação determinística sobre a saída do modelo, que
decide se ela é aceita, se o modelo deve tentar de novo, ou se o trabalho
falha. Três existem neste sistema: um sobre a transcrição, dois sobre a
correção.

Todos são funções puras, sem rede e sem estado externo, o que os torna
testáveis isoladamente — e reutilizáveis como métrica offline.

## Transcrição

### O problema que ele resolve

Antes, o provedor de transcrição aceitava qualquer string que o modelo
devolvesse, inclusive vazia. O texto ia direto para a correção.

Quando o modelo multimodal transcrevia só parte da folha, ninguém percebia. A
correção seguia adiante e avaliava três linhas como se fossem a redação
inteira. O resultado saía bem-formado, plausível e errado — que é a pior
combinação possível, porque nada no sistema sinalizava problema.

### Por que a saída é estruturada

A solução óbvia seria contar palavras e, se forem poucas, mandar o modelo
tentar de novo. Essa solução é uma armadilha.

Um guard que rejeita "poucas palavras" e pede outra tentativa **pressiona o
modelo a inventar texto** para satisfazer o critério. Num sistema de correção
de redação, texto inventado entra no lugar da escrita do aluno e contamina
toda nota, todo feedback e toda métrica a jusante. E o critério tem um falso
positivo legítimo: o aluno do fundamental que de fato escreveu pouco.

Por isso o modelo de visão não devolve texto puro. Devolve uma estrutura com
o texto, uma declaração de ter chegado ao fim da folha, e a contagem de
trechos ilegíveis. O guard cruza um sinal determinístico — a contagem de
palavras — com a autodeclaração do modelo, e só pede nova tentativa quando os
dois discordam.

A instrução do retry pede **verificação, não expansão**: manda conferir se
restou texto na folha, permite explicitamente repetir a mesma transcrição
curta, e proíbe acrescentar o que não está na imagem.

### As regras, na ordem em que rodam

1. O modelo declarou transcrição incompleta → nova tentativa.
1. Texto vazio ou sem nenhuma palavra → nova tentativa, **sempre**.
1. Proporção de trechos ilegíveis acima do limiar → nova tentativa, **sempre**.
1. Menos palavras que o mínimo, com o modelo declarando completude → nova
   tentativa na primeira vez; **aceita** se o modelo reafirmar.
1. Caso contrário, aceita.

### A assimetria é deliberada

Só a regra de contagem de palavras aceita reafirmação. Folha em branco e folha
ilegível não aceitam, e isso não é descuido.

Contagem de palavras tem falso positivo legítimo — o aluno que escreveu pouco
— e o modelo consegue resolver a dúvida olhando de novo. Folha em branco e
folha ilegível não são julgamento que uma segunda leitura desfaça: são
condições que exigem um humano. Essas esgotam as tentativas e falham o job,
com a mensagem de que a folha requer digitação manual.

A ordem das regras importa por uma razão que custou uma correção nesta
implementação: a checagem de ilegibilidade precisa vir **antes** do ramo de
contagem de palavras. Abaixo dele, ela ficava inalcançável para texto curto,
e uma folha 90% ilegível com poucas palavras era aceita e corrigida.

## Citações

Todo trecho entre aspas nas justificativas e no feedback tem de aparecer na
redação do aluno. A comparação ignora acento, caixa e pontuação, porque uma
vírgula a mais não torna a citação inventada.

Isso existe porque o `AGENTS.md` do projeto lista referência alucinada a texto
ausente entre os comportamentos proibidos, e nada verificava isso antes. Um
modelo que atribui ao aluno uma frase que ele não escreveu está fabricando a
evidência sobre a qual a nota se apoia.

A **sugestão acionável** está deliberadamente fora do escopo deste guard. O
trabalho dela é propor linguagem que o aluno ainda não usou — sugerir um
conectivo entre aspas é comportamento correto, e incluí-la faria o guard
punir exatamente a saída pedagogicamente desejável.

### O que foi observado

Em cinco execuções sobre as mesmas 94 redações — mesma transcrição, mesmo
modelo, mesmo backend — o guard disparou 31, 26, 42, 33 e 39 vezes
(2026-09-20, deepseek-v4.1-flash, lotes `e4d508d6`, `7c7c395b`, `f6dd1865` e
`cda91f62`).

Somando: em 120 das 478 tentativas, cerca de uma em quatro, o modelo tentou
citar trecho ausente do texto do aluno. Nenhuma correção entregue contém
citação inventada.

A série é apresentada inteira, e não como média, porque a dispersão é ela
mesma um resultado. A entrada foi idêntica nas cinco execuções e a taxa
variou por um fator de 1,6 — e desta vez **sem** troca de backend, já que as
478 tentativas foram todas servidas pelo mesmo provedor. A variação é da
inferência, não do roteamento. Ver [Confiabilidade](confiabilidade.md).

## Justificativas distintas

Justificativa idêntica repetida entre critérios diferentes indica modelo
preguiçoso, não avaliação. O guard normaliza e compara as cinco
justificativas; havendo repetição, pede nova tentativa.

Nunca disparou nas execuções medidas. Está aqui porque o custo de verificar é
irrelevante e o custo de não verificar é uma avaliação que parece completa
sem ser.

## Quando um guardrail esgota

O orçamento de retries internos é configurável e nasce em dois. Esgotado, a
tentativa é registrada como falha — **com o uso real gravado**, incluindo os
tokens e o custo de todas as chamadas feitas até ali.

Isso importa: uma tentativa que falhou depois de três chamadas ao modelo
custou dinheiro, e uma tabela de auditoria que registrasse zero ali estaria
mentindo sobre o custo justamente nos casos mais caros.

A partir daí, o laço externo do worker decide se tenta de novo, conforme
descrito em [Processo de correção](processo-de-correcao.md).
