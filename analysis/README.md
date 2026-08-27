# Analise e visualizacao de dados

Gera graficos de distribuicao por faixa para as RQs do laboratorio, a partir do
`repositories.parquet` ja coletado (nao bate na API do GitHub).

As faixas usadas em cada grafico sao identicas as ja publicadas nos documentos
de validacao (`docs/rq01_rq02_validacao.md`, `docs/rq03_rq04_validacao.md`), para
manter tabela e grafico consistentes.

## Instalar

```bash
cd analysis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Rodar

Gera todos os graficos configurados, salvando em `docs/assets/`:

```bash
python visualize_rq.py
```

Para gerar so algumas RQs:

```bash
python visualize_rq.py --rq rq01_age rq02_pull_requests
```
