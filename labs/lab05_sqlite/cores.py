"""Cores e marcadores do dashboard do Lab05, num lugar so, para cada coisa ter sempre a mesma cor.

Configuracoes: paleta de Okabe e Ito, feita para quem tem daltonismo. DELETE em tons quentes e WAL em azuis, para a
familia ser reconhecida de longe e cada configuracao ainda ter cor propria.

Ambientes: paleta "muted" de Paul Tol (tambem segura para daltonismo), mais um formato de marcador por familia
(notebook, GitHub Actions, celular), para a identidade nunca depender so da cor.
"""

CONFIG = {
    "DELETE/FULL": "#D55E00",    # vermelhao: o padrao do SQLite e do Python
    "DELETE/NORMAL": "#E69F00",  # laranja
    "DELETE/EXTRA": "#CC79A7",   # rosa
    "WAL/FULL": "#0072B2",       # azul
    "WAL/NORMAL": "#56B4E9",     # azul-ceu
}

AMBIENTE = {
    "Notebook · Windows": "#332288",
    "Notebook · Linux (WSL2)": "#88CCEE",
    "Actions · Ubuntu": "#44AA99",
    "Actions · Windows": "#117733",
    "Actions · macOS": "#999933",
    "iPhone 11 · iOS": "#CC6677",
    "Android": "#882255",
}


def simbolo_ambiente(ambiente: str) -> str:
    if ambiente.startswith("Notebook"):
        return "diamond"
    if ambiente.startswith("Actions"):
        return "square"
    return "circle"


def config(journal: str, synchronous: str) -> str:
    return CONFIG[f"{journal}/{synchronous}"]


SIGNIFICATIVO = "#0072B2"
NAO_SIGNIFICATIVO = "#9E9C96"
TEXTO = "#2F2E2B"
TEXTO_SECUNDARIO = "#6B6A65"
GRADE = "#E8E6E1"
REFERENCIA = "#9E9C96"
FONTE = "Source Sans Pro, Arial, sans-serif"
