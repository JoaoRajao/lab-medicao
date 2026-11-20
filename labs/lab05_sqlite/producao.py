"""Segundo caminho do Lab05: quais configuracoes o SQLite usa em producao (pesquisa documental).

So documentacao oficial ou rastreador oficial do fornecedor, nunca analise de codigo-fonte (secao 2a do enunciado).
Acesso a todas as fontes: 19/11/2026. A linha "Python sqlite3" e verificada no proprio ambiente do grupo.
"""

from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

ACESSO = "19/11/2026"


@dataclass(frozen=True)
class Configuracao:
    software: str
    alcance: str
    journal: str
    synchronous: str
    evidencia: str
    fonte: str
    url: str


CONFIGURACOES = (
    Configuracao("SQLite (padrão da biblioteca)", "toda aplicação que não muda a configuração", "DELETE", "FULL",
                 "\"The DELETE journaling mode is the default\"; \"FULL is the default synchronous mode for a rollback "
                 "journal\". Para o WAL, \"synchronous=NORMAL provides the best balance between performance and safety "
                 "for most applications\".", "SQLite — PRAGMA statements", "https://www.sqlite.org/pragma.html"),
    Configuracao("Python sqlite3", "scripts e aplicações Python (biblioteca padrão)", "DELETE", "FULL",
                 "Verificado no ambiente do grupo: uma conexão nova retorna journal_mode = delete e synchronous = 2 "
                 "(FULL), ou seja, herda o padrão da biblioteca.", "Verificação local (Python 3.14.7, SQLite 3.50.4)",
                 ""),
    Configuracao("Android SQLiteDatabase (Android 9+)", "apps Android que usam a API nativa", "WAL", "não informado",
                 "\"Compatibility WAL\" é ativado por padrão no banco de cada app, a menos que o app escolha o modo. "
                 "A página afirma que o WAL pode dar ganho de 4× na velocidade de escrita no ext4.",
                 "Android Open Source Project — Compatibility WAL",
                 "https://source.android.com/docs/core/perf/compatibility-wal"),
    Configuracao("Android Room (Jetpack)", "apps Android que usam a biblioteca recomendada pelo Google", "WAL",
                 "não informado", "O padrão AUTOMATIC usa WRITE_AHEAD_LOGGING, exceto em API < 16 ou em aparelhos com "
                 "pouca RAM, que usam TRUNCATE.", "Android Developers — RoomDatabase.JournalMode",
                 "https://developer.android.com/reference/androidx/room/RoomDatabase.JournalMode"),
    Configuracao("Apple Core Data (iOS 7+ e OS X 10.9+)", "apps iOS e macOS que usam Core Data", "WAL", "não informado",
                 "\"the default journaling mode for Core Data SQLite stores was changed to Write-Ahead Logging (WAL) in "
                 "iOS 7 and OS X Mavericks\".", "Apple Technical Q&A QA1809",
                 "https://developer.apple.com/library/archive/qa/qa1809/_index.html"),
    Configuracao("Firefox (Places: histórico e favoritos)", "navegador Firefox", "WAL", "FULL",
                 "\"Currently, Places uses JOURNAL_MODE=WAL and SYNCHRONOUS=FULL. These are acceptable defaults because "
                 "they will lead to the least amount of data loss in the wild.\" (2016)",
                 "Mozilla Bugzilla — Bug 1272025", "https://bugzilla.mozilla.org/show_bug.cgi?id=1272025"),
)

NAO_DOCUMENTADOS = (
    ("Google Chrome", "A configuração só aparece no código-fonte do Chromium, que está fora do escopo do lab "
                      "(seção 2a do enunciado); não há documentação oficial pública."),
)


def configuracao_local() -> tuple[str, int]:
    """journal_mode e synchronous de uma conexao nova do sqlite3 do Python, sem nenhum PRAGMA."""
    with tempfile.TemporaryDirectory() as pasta:
        con = sqlite3.connect(Path(pasta) / "padrao.db")
        try:
            return con.execute("PRAGMA journal_mode").fetchone()[0], con.execute("PRAGMA synchronous").fetchone()[0]
        finally:
            con.close()


def tratamento(c: Configuracao) -> tuple[str, str] | None:
    """Tratamento do experimento que corresponde a configuracao (None se o synchronous nao e informado)."""
    return (c.journal, c.synchronous) if c.synchronous in ("FULL", "NORMAL") else None
