"""Comando unico do Lab04: dados -> simulacoes -> roteiro -> validacao -> dashboard (issue #104).

    python -m labs.lab04_ci.executar                  # gera tudo, valida e abre o dashboard
    python -m labs.lab04_ci.executar --sem-dashboard  # so gera e valida (ambiente limpo, CI)
    python -m labs.lab04_ci.executar --checar-links   # tambem confere os links do topo (precisa de rede)

Semente fixa: `estatistica.SEED` (42), repassada as simulacoes. Contrato das simulacoes (#99/#100): o modulo
`labs.lab04_ci.experimentos` expoe `gerar_resultados(seed: int) -> pandas.DataFrame` com as colunas de
`resultados.COLUNAS`; o resultado e gravado em `data/simulacao/resultados.csv`, que o dashboard le.
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from labs.lab04_ci import estatistica as est  # noqa: E402
from labs.lab04_ci import graficos, ingest, roteiro  # noqa: E402
from labs.lab04_ci import resultados as res  # noqa: E402

APP = Path(__file__).resolve().parent / "app.py"
SECOES = ["1. Cenário", "2. Os dados", "3. Como os testes funcionam", "4. Erro tipo I", "5. Poder",
          "6. Dados reais", "7. Conclusão"]
LINKS = {"repositório": "https://github.com/JoaoRajao/lab-medicao",
         "GitHub Projects": "https://github.com/users/JoaoRajao/projects/4",
         "dashboard publicado": roteiro.DASHBOARD}


def passo(titulo: str) -> None:
    print(f"\n== {titulo}", flush=True)


def simular() -> bool:
    """Roda as simulacoes de Q1-Q3 se o modulo da #99/#100 existir; True se ha resultados para o dashboard."""
    try:
        experimentos = importlib.import_module("labs.lab04_ci.experimentos")
    except ModuleNotFoundError as erro:
        if erro.name != "labs.lab04_ci.experimentos":
            raise
        existente = res.carregar()
        print("   labs/lab04_ci/experimentos.py ainda não existe (#99/#100): "
              + ("mantendo os resultados versionados." if existente is not None else
                 "o dashboard mostra os valores exatos no lugar das simulações."))
        return existente is not None
    caminho = res.salvar(experimentos.gerar_resultados(seed=est.SEED))
    print(f"   resultados gravados em {caminho.relative_to(ROOT).as_posix()}")
    return True


def validar() -> list[str]:
    """Confere a entrega: amostra real, resultados, quatro graficos e secoes do dashboard. Devolve os problemas."""
    from streamlit.testing.v1 import AppTest

    problemas = []
    amostra = est.carregar_amostra()
    print(f"   amostra real: {amostra.n} execuções, {amostra.falhas} falhas ({amostra.repositorio})")
    if amostra.n != ingest.SAMPLE_SIZE:
        problemas.append(f"amostra real com {amostra.n} execuções, esperado {ingest.SAMPLE_SIZE}")

    simulados = res.carregar()
    exatos = res.exatos(simulados)
    if simulados is None:
        problemas.append("sem resultados de Q1-Q3 (data/simulacao/resultados.csv): G3 e G4 mostram só os valores exatos")
    else:
        print(f"   resultados: {len(simulados)} linhas, situações {list(dict.fromkeys(simulados['situacao']))}")
        if (simulados["repeticoes"] < 10_000).any():
            problemas.append("há pontos com menos de 10.000 repetições")
        if simulados["seed"].nunique() != 1:
            problemas.append("resultados com mais de uma semente")
        conferidos = simulados.merge(exatos, on=["situacao", "teste", "p_verdadeiro"], suffixes=("", "_ex"))
        # 3,29 erros padrao = 99,9%: com dezenas de pontos, uma diferenca maior indica erro de codigo, nao acaso.
        fora = conferidos[(conferidos["taxa_rejeicao"] - conferidos["taxa_exata"]).abs()
                          > res.margem(conferidos["taxa_exata"], conferidos["repeticoes"]) * 3.29 / 1.96]
        print(f"   simulação × valor exato: {len(conferidos)} pontos Bernoulli conferidos, {len(fora)} fora de 99,9%")
        problemas += [f"{l.situacao} · {l.teste} · p = {l.p_verdadeiro}: simulado {l.taxa_rejeicao:.4f}, "
                      f"exato {l.taxa_exata:.4f}" for l in fora.itertuples()]

    figuras = [graficos.g1_dados(amostra), graficos.g2_testes(amostra), graficos.g3_erro_tipo_i(simulados, exatos),
               graficos.g4_poder(simulados, exatos, amostra.proporcao - est.P0)]
    for i, fig in enumerate(figuras, start=1):
        if not (fig.layout.title.text or "").startswith(f"G{i}") or not fig.layout.xaxis.title.text \
                or not fig.layout.yaxis.title.text or len(fig.data) < 2:
            problemas.append(f"G{i} sem título, eixos ou legenda")
    print("   gráficos G1–G4: título, eixos e legenda conferidos")

    app = AppTest.from_file(str(APP), default_timeout=120).run()
    if app.exception:
        problemas.append(f"dashboard com exceção: {app.exception[0].message}")
    secoes = [h.value for h in app.header]
    print(f"   seções do dashboard: {secoes}")
    if secoes != SECOES[:len(secoes)]:
        problemas.append(f"seções fora da ordem do enunciado: {secoes}")
    faltando = SECOES[len(secoes):]
    if faltando:
        problemas.append(f"seções ainda ausentes: {faltando}")
    return problemas


class _SemRedirecionar(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # o Streamlit Cloud redireciona para gravar um cookie de acesso
        return None


def checar_links() -> list[str]:
    problemas, abrir = [], build_opener(_SemRedirecionar).open
    for nome, url in LINKS.items():
        try:
            with abrir(Request(url, headers={"User-Agent": "lab-medicao-validacao"}), timeout=30) as resposta:
                status = resposta.status
        except HTTPError as erro:
            status = erro.code
        except OSError as erro:
            problemas.append(f"link do {nome} não abriu: {erro}")
            continue
        print(f"   {nome}: HTTP {status}")
        if status >= 400:
            problemas.append(f"link do {nome} respondeu HTTP {status}")
    return problemas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera, valida e abre o dashboard do Lab04")
    parser.add_argument("--sem-dashboard", action="store_true", help="Não abre o Streamlit ao final")
    parser.add_argument("--checar-links", action="store_true", help="Confere os links do topo (precisa de rede)")
    args = parser.parse_args(argv)

    passo("1/5 Dados reais: CSV → DuckDB → Parquet → dbt")
    ingest.main([])
    passo(f"2/5 Simulações de Q1–Q3 (semente {est.SEED})")
    simular()
    passo("3/5 Roteiro das 15 perguntas")
    print(f"   {roteiro.gerar().relative_to(ROOT).as_posix()}")
    passo("4/5 Validação da entrega")
    problemas = validar() + (checar_links() if args.checar_links else [])
    for problema in problemas:
        print(f"   PENDENTE: {problema}")
    print("   OK: nada pendente" if not problemas else f"   {len(problemas)} pendência(s)")
    if not args.sem_dashboard:
        passo("5/5 Dashboard (Ctrl+C para encerrar)")
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(APP)], cwd=ROOT, check=False)
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
