from __future__ import annotations

import pytest

from labs.lab05_sqlite import painel, robustez


@pytest.fixture(scope="module")
def d():
    return painel.carregar()


def test_graficos_tem_titulo_eixo_e_dados(d):
    figuras = [painel.efeitos(d["testes"]), painel.durabilidade(d["durabilidade"]),
               painel.concorrencia(d["concorrencia"]), painel.replicacao(d["replicacao"])]
    for fig in figuras:
        assert fig.layout.title.text and fig.layout.xaxis.title.text
        assert fig.data and all(len(t.x) for t in fig.data if t.x is not None)


def test_cada_configuracao_e_cada_ambiente_tem_cor_propria(d):
    from labs.lab05_sqlite import cores

    fig = painel.durabilidade(d["durabilidade"])
    cores_configs = list(fig.data[0].marker.color)
    assert len(set(cores_configs)) == len(cores_configs) and set(cores_configs) <= set(cores.CONFIG.values())
    rep = painel.replicacao(d["replicacao"])
    pontos = [t for t in rep.data if t.mode == "markers"]
    assert len({t.marker.color for t in pontos}) == len(pontos) == d["replicacao"]["ambiente"].nunique()
    assert rep.layout.showlegend and painel.concorrencia(d["concorrencia"]).layout.showlegend


def test_numeros_das_manchetes_saem_dos_dados(d):
    n = painel.numeros(d)
    t = d["testes"].set_index("codigo")
    assert n["h1"] == pytest.approx(t.loc["H-1", "razao_medianas"])
    assert n["ambientes"] == d["comparacao"]["ambientes"].max()
    texto = painel.veredito(n)
    assert robustez._vezes(n["h1"]) in texto and f"{n['direcao']} de {n['pares']}" in texto
    assert len(painel.resposta(n)["pontos"]) == 3


def test_textos_de_limites_usam_os_dados(d):
    h3 = d["comparacao"].set_index("codigo").loc["H-3"]
    assert robustez._vezes(h3["razao_max"]) in painel.nao_afirma(d)[1]
    md = painel.tabela_md(painel.CATEGORIAS)
    assert md.count("\n") == len(painel.CATEGORIAS) + 1 and "Nível de evidência" in md
