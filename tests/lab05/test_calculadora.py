from __future__ import annotations

import pytest

from labs.lab05_sqlite import calculadora, robustez
from labs.lab05_sqlite.calculadora import Perfil


@pytest.fixture(scope="module")
def dados():
    return calculadora.carregar()


def test_perda_inaceitavel_sempre_wal_full(dados):
    for escritas in (1, 60, 12_000):
        r = calculadora.recomendar(Perfil(escritas, True, "inaceitavel"), dados)
        assert r["escolha"] == ("WAL", "FULL")
        assert any("Não perdeu nenhuma transação" in m for m in r["motivos"])


def test_perda_indiferente_wal_normal_com_o_custo_explicito(dados):
    r = calculadora.recomendar(Perfil(60, False, "indiferente"), dados)
    assert r["escolha"] == ("WAL", "NORMAL")
    assert any("O custo:" in m for m in r["motivos"])


def test_perda_toleravel_depende_de_quanto_o_full_pesa(dados):
    pouco = calculadora.recomendar(Perfil(10, False, "toleravel", robustez.REFERENCIA), dados)
    muito = calculadora.recomendar(Perfil(12_000, False, "toleravel", robustez.REFERENCIA), dados)
    assert pouco["escolha"] == ("WAL", "FULL") and muito["escolha"] == ("WAL", "NORMAL")


def test_tabela_usa_os_valores_medidos_do_ambiente(dados):
    t = calculadora.tabela(Perfil(60, True, "inaceitavel", robustez.REFERENCIA), dados).set_index("Configuração")
    esperado = float(dados["latencia_ms"].loc[(robustez.REFERENCIA, "WAL", "FULL")])
    assert t.loc["WAL/FULL", "ms por gravação"] == pytest.approx(esperado)
    assert t.loc["WAL/FULL", "fração do tempo gravando"] == pytest.approx(60 * esperado / 60_000)
    assert t.loc["DELETE/FULL (padrão)", "bloqueia leitura"] and not t.loc["WAL/FULL", "bloqueia leitura"]


def test_alerta_do_padrao_e_concorrencia_quando_le_enquanto_grava(dados):
    com = calculadora.recomendar(Perfil(60, True, "inaceitavel"), dados)
    sem = calculadora.recomendar(Perfil(60, False, "inaceitavel"), dados)
    assert com["alertas"] and "DELETE/FULL" in com["alertas"][0]
    assert any("lê enquanto grava" in m for m in com["motivos"])
    assert not any("lê enquanto grava" in m for m in sem["motivos"])


def test_concorrencia_do_celular_quando_o_ambiente_e_celular(dados):
    if "iPhone 11 · iOS" not in dados["ambientes"]:
        pytest.skip("sem coleta do iPhone")
    r = calculadora.recomendar(Perfil(60, True, "inaceitavel", "iPhone 11 · iOS"), dados)
    assert any("iPhone" in m and "lê enquanto grava" in m for m in r["motivos"])
