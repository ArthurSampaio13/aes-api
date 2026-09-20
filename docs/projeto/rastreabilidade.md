# Rastreabilidade

## Por que registrar tanto

Sem histórico por tentativa não há como afirmar nada sobre o sistema. Nem
quanto custa corrigir uma turma, nem com que frequência um guardrail atua, nem
se dois modelos produzem resultados diferentes sobre as mesmas redações.

Um sistema que grava apenas o resultado final permite dizer que ele funcionou.
Um sistema que grava o caminho permite dizer **como** funcionou, e é isso que
uma análise acadêmica precisa citar.

## O que fica gravado em cada tentativa

| campo                                     | o que é                             | por que importa                                            |
| ----------------------------------------- | ----------------------------------- | ---------------------------------------------------------- |
| `attempt_number`                          | posição no laço do worker           | distingue retry externo de interno                         |
| `provider`, `model`                       | quem foi chamado                    | condição do experimento                                    |
| `served_provider`                         | backend que de fato atendeu         | o OpenRouter roteia; sem isso não se sabe quem respondeu   |
| `prompt_version`, `rubric_version`        | versões em uso                      | duas execuções com rubricas diferentes não são comparáveis |
| `code_version`                            | versão da aplicação                 | separa mudança de modelo de mudança de código              |
| `inference_params`                        | temperatura, seed, cache, pin       | as condições exatas da chamada                             |
| `outcome`                                 | `success`, `retry`, `failed`        | desfecho da tentativa                                      |
| `tokens_in`, `tokens_out`                 | tokens de entrada e saída           | volume real                                                |
| `cache_read_tokens`, `cache_write_tokens` | tokens de cache                     | separados de propósito, ver abaixo                         |
| `cost_usd`, `cost_source`                 | custo e sua procedência             | cobrado ou estimado, explicitamente                        |
| `model_retries`                           | chamadas extras dentro da tentativa | mede atuação dos guardrails                                |
| `guardrail_events`                        | veredito de cada guard              | o que cada um decidiu e por quê                            |
| `latency_ms`                              | duração da chamada                  | dimensiona a assincronia                                   |
| `raw_request_ref`, `raw_response_ref`     | ponteiros no object storage         | a conversa crua, se for preciso auditar                    |
| `validation_errors`, `error_message`      | detalhe da falha                    | diagnóstico                                                |

### Por que tokens de cache ficam separados

Somar tokens de cache aos tokens de entrada faria o orçamento do município
cobrar token cacheado a preço cheio, e distorceria qualquer análise de custo.
São três números distintos porque medem três coisas distintas: o que foi
processado do zero, o que foi reaproveitado, e o que foi gravado para reúso.

### Por que a transcrição também deixa rastro

A transcrição não gera uma tentativa de correção, mas gasta chamadas ao modelo
— e, no caso das folhas digitalizadas, é a etapa mais cara. Por isso a
submissão guarda um bloco próprio com modelo, tokens, custo, latência,
contagem de palavras, autodeclaração de completude e os vereditos do guard.

Isso vale inclusive quando a transcrição **falha**: uma folha que estourou o
tempo do provedor depois de três tentativas consumiu chamadas reais, e o
rastro registra o que foi gasto em vez de deixar o campo vazio.

## O manifesto do lote

```
GET /api/v1/aes/batches/{batch_id}/manifest
```

Devolve, por job do lote, as condições completas que produziram cada
correção: a submissão, o rastro da transcrição, **todas** as tentativas e o
resultado aceito.

É o artefato que uma análise cita. A forma resumida:

```json
{
  "batch_id": "f0b97f15-...",
  "essay_prompt_id": "68c280a5-...",
  "jobs": [
    {
      "job_id": "cd4edcdf-...",
      "status": "done",
      "input_type": "image",
      "transcription": {
        "model": "openrouter:deepseek/deepseek-v4.1-flash",
        "palavras": 102,
        "served_provider": "DeepInfra",
        "cost_usd": "0.00234",
        "cost_source": "charged",
        "model_retries": 0
      },
      "attempts": [
        {
          "attempt_number": 1,
          "outcome": "success",
          "model": "deepseek/deepseek-v4.1-flash",
          "served_provider": "DeepInfra",
          "prompt_version": 1,
          "rubric_version": 1,
          "inference_params": { "seed": 42, "temperature": 0.0 },
          "tokens_in": 956,
          "cache_read_tokens": 768,
          "cost_usd": "0.00089",
          "cost_source": "charged",
          "model_retries": 0,
          "guardrail_events": [
            { "guard": "citacoes", "veredito": "allow", "motivo": "..." }
          ]
        }
      ],
      "result": {
        "scores": { "adequacao_tema": { "nota": 7, "justificativa": "..." } },
        "requires_teacher_review": true
      }
    }
  ]
}
```

Repare que `requires_teacher_review` aparece no manifesto. Não é flag interna:
quem analisa os dados vê que nenhum resultado foi tratado como final.

## Isolamento entre municípios

O manifesto respeita a política de linha do banco. Pedir um lote de outro
município responde **404, não 403** — a diferença é deliberada, porque 403
confirmaria que o recurso existe.

O mecanismo está descrito em [Arquitetura](arquitetura.md).
