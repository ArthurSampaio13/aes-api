# Correção assistida de redações do Ensino Fundamental

Este é o artefato de software de um Trabalho de Conclusão de Curso sobre
correção de redações assistida por modelos de linguagem.

O problema é concreto. Corrigir redação é lento, repetitivo e difícil de
manter consistente, o que limita a frequência com que um aluno recebe
retorno detalhado sobre a própria escrita. Este sistema dá ao professor um
ponto de partida: transcreve a folha digitalizada, avalia segundo uma rubrica
configurável e devolve feedback por critério, com o caminho inteiro
registrado para auditoria.

**O sistema não corrige sozinho.** Todo resultado nasce marcado para revisão
do professor, e nenhuma decisão de alto impacto é tomada sem ele. O que o
sistema entrega é um rascunho rastreável, não uma nota final.

## Por onde começar

A [visão geral do projeto](projeto/index.md) conta a história inteira: o
problema, a arquitetura e o caminho de uma folha digitalizada até um
resultado revisável. Dali se chega a todas as demais páginas.

Para rodar o sistema, veja [Rodando o AES](getting-started/running-aes.md).

A seção **Referência da plataforma** documenta o boilerplate FastAPI do qual
este repositório partiu. É documentação de terceiros, mantida em inglês,
sobre infraestrutura que o projeto de fato usa — caching, autenticação,
migrações — mas não é sobre este trabalho.
