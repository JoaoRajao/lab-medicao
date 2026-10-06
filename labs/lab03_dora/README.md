# Lab03 - Mineracao de metricas DORA

Calcula as metricas DORA (deployment frequency, lead time for changes, change failure rate e tempo de
recuperacao) a partir dos dados publicos de repositorios open-source que usam GitHub Actions.

Todos os comandos rodam a partir da raiz do repositorio, com o ambiente da raiz instalado
(`pip install -r requirements.txt`, ver README raiz).

## Como reproduzir

1. Defina o token do GitHub (nunca commite o token):

   ```bash
   export GITHUB_TOKEN=ghp_...        # ou GITHUB_TOKEN=... no arquivo .env da raiz
   ```

2. Confira a janela de observacao em [`config.yaml`](config.yaml). O padrao sao os 12 meses completos
   antes do inicio do Lab03 (2025-10-01 a 2026-09-30); se o professor fixar outras datas, troque ali.
   Com a janela vazia ou fora de 12 meses, o pipeline se recusa a rodar.

3. Rode o pipeline com um unico comando:

   ```bash
   python -m labs.lab03_dora --config labs/lab03_dora/config.yaml
   ```

   Para rodar so uma etapa: `--etapa selecao` (pode repetir a opcao).

A coleta pode ser interrompida a qualquer momento (rate limit, queda de rede, `Ctrl+C`): rodar o mesmo
comando de novo continua de onde parou, sem repetir chamadas ja feitas.

## Configuracao

| Chave | Significado | Padrao |
| --- | --- | --- |
| `janela.inicio`, `janela.fim` | Janela de observacao de 12 meses (AAAA-MM-DD). Obrigatoria. | - |
| `inclusao.min_releases` | Releases publicadas (`draft = false`) na janela | 5 |
| `inclusao.min_workflow_runs` | Workflow runs validos (`event = push` no default branch) na janela | 50 |
| `amostra.repositorios` | Tamanho alvo da amostra | 100 |
| `saida.dados` | Pasta dos CSVs (metricas e funil) | `data` |
| `saida.cache` | Pasta do cache da API (gitignored) | `data/cache` |
| `api.max_tentativas` | Novas tentativas em erro 5xx ou de rede | 5 |
| `api.timeout_segundos` | Timeout de cada requisicao | 30 |

Caminhos relativos sao resolvidos a partir da pasta do `config.yaml`.

## Etapas do pipeline

O pipeline roda as etapas em ordem. Cada etapa e uma funcao `run(ctx)` registrada em
[`pipeline.py`](pipeline.py) (`STAGES`). Enquanto o modulo de uma etapa nao existir, o pipeline para
nela e indica a issue correspondente.

| Etapa | Modulo | Issue |
| --- | --- | --- |
| `selecao` | `labs/lab03_dora/selecao.py` | #60 (componente A) |
| `releases` | `labs/lab03_dora/releases.py` | #61 (componente B) |
| `workflow_runs` | `labs/lab03_dora/workflow_runs.py` | #62 (componente C) |

Contrato de uma etapa:

```python
from labs.lab03_dora.pipeline import Context

def run(ctx: Context) -> None:
    config = ctx.config          # janela, criterios de inclusao, pastas de saida
    client = ctx.client          # GitHubRestClient, com cache, rate limit e backoff
    ...                          # le e grava CSVs em config.output_dir
```

As funcoes de calculo das metricas ficam em `labs/lab03_dora/metricas/`, separadas da coleta, para
serem testadas com *fixtures* sem acessar a API.

### Cliente da API (`shared/github_rest.py`)

```python
response = client.get("/repos/{owner}/{repo}")                          # Response(status, data, headers)
for release in client.paginate("/repos/{owner}/{repo}/releases"):       # segue Link: rel="next"
    ...
for run in client.paginate(f"/repos/{repo}/actions/runs", {"event": "push"}, item_key="workflow_runs"):
    ...
client.rate_limit()                                                      # nao consome cota, nunca cacheado
```

- **Cache e retomada:** cada resposta e salva em `saida.cache/<repos>/<owner>/<repo>/<endpoint>/`, um JSON
  por requisicao. Uma requisicao ja feita e respondida do disco, sem chamar a API. O token nunca e gravado.
- **Rate limit:** le `X-RateLimit-Remaining`/`X-RateLimit-Reset` e pausa ate a renovacao quando a cota
  acaba; respeita `Retry-After` em rate limit secundario.
- **Erros temporarios:** respostas 5xx e erros de rede sao repetidos com backoff exponencial
  (1 s, 2 s, 4 s, 8 s, 16 s) ate `api.max_tentativas`.
- **404/410** (ex.: `compare` com tag apagada) levantam `GitHubNotFoundError` e tambem ficam no cache, para
  a retomada nao repetir a chamada. Outros erros 4xx levantam `GitHubAPIError` e nao sao cacheados.
- A coleta usa a API REST, implementada com a biblioteca padrao (sem PyGithub ou equivalentes, proibidos
  pelo enunciado). O `shared/github_client.py` continua disponivel para consultas GraphQL.

## Testes e CI

```bash
python -m pytest tests/lab03 --cov=labs/lab03_dora --cov=shared.github_rest --cov-report=term-missing
```

O workflow [`.github/workflows/testes.yml`](../../.github/workflows/testes.yml) roda a suite inteira do
repositorio (`tests/`) a cada push e pull request e falha se:

- algum teste falhar;
- a cobertura do Lab03 e do cliente da API ficar abaixo de 80%; ou
- a cobertura do modulo `labs/lab03_dora/metricas/` ficar abaixo de 80% (exigencia do enunciado).

Toda funcao nova em `metricas/` precisa vir com testes no mesmo PR, ou o CI fica vermelho.
