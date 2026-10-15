"""Rascunho automatico para revisao de Joao; nunca altera a planilha final."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Sequence

from openpyxl import load_workbook

from labs.lab03_dora.records import write_csv

VERSION = "regras-codex-v1"
FIELDS = (
    "escopo", "repositorio", "tag", "dimensao", "sugestao", "confianca",
    "evidencia", "metodo", "origem", "rotulo_final", "revisor", "revisado_em",
)
CORRECTIVE = re.compile(r"\b(bug\s*fix(?:es)?|hotfix|regression|revert|fix(?:es|ed)?|patch release|security fix)\b", re.I)
FEATURE = re.compile(r"\b(new feature|features?|added|introduc(?:ed|es)|support for|new in|enhancement)\b", re.I)
CLI = re.compile(r"\b(cli|command.line|terminal|shell|developer tool|command line)\b", re.I)
LIBRARY = re.compile(r"\b(library|framework|sdk|package|api client|toolkit|module)\b", re.I)
APP = re.compile(r"\b(app|application|service|server|platform|website|web app|self.hosted)\b", re.I)


def _rows(path: Path, sheet: str) -> list[dict]:
    book = load_workbook(path, read_only=True, data_only=True)
    rows = book[sheet].values
    headers = next(rows)
    result = [dict(zip(headers, row)) for row in rows]
    book.close()
    return result


def project_type(description: str, topics: str) -> tuple[str, str, str]:
    text = f"{description} {topics}"
    matches = [
        ("ferramenta CLI", CLI.search(text)),
        ("biblioteca/framework", LIBRARY.search(text)),
        ("aplicacao/servico", APP.search(text)),
    ]
    available = [(label, match.group(0)) for label, match in matches if match]
    if not available:
        return "outro", "baixa", "sem indicador explicito; verificar README"
    label, evidence = available[0]
    return label, "media" if len(available) > 1 else "alta", f"descricao/topicos: {evidence}"


def real_delivery(description: str, topics: str) -> tuple[str, str, str]:
    text = f"{description} {topics}".lower()
    if re.search(r"\b(awesome|collection of|curated list|examples?|tutorials?|template)\b", text):
        return "incerto", "baixa", "parece catalogo/exemplo; verificar releases"
    return "sim", "baixa", "projeto de software; verificar se as releases entregam ao usuario"


def corrective(notes: str, commits: str) -> tuple[str, str, str]:
    summary = (notes or "")[:1000]
    first_lines = "\n".join((commits or "").splitlines()[:12])
    fix = CORRECTIVE.search(summary)
    feature = FEATURE.search(summary)
    if fix and not feature:
        return "sim", "media", f"notas: {fix.group(0)}"
    if feature and not fix:
        return "nao", "media", f"notas: {feature.group(0)}"
    if fix and feature:
        return "incerto", "baixa", "notas misturam correcoes e novidades; revisar objetivo principal"
    commit_fix = CORRECTIVE.search(first_lines)
    if commit_fix:
        return "incerto", "baixa", f"commit: {commit_fix.group(0)}; notas sem objetivo claro"
    return "incerto", "baixa", "sem evidencia suficiente no resumo; abrir links"


def build(path: Path, output: Path) -> list[dict]:
    suggestions = []
    for item in _rows(path, "Repositorios"):
        repo = item["repositorio"]
        for dimension, classifier in (("tipo_projeto", project_type), ("entregas_reais", real_delivery)):
            suggestion, confidence, evidence = classifier(item.get("descricao") or "", item.get("topicos") or "")
            suggestions.append(dict(escopo="repositorios", repositorio=repo, tag="", dimensao=dimension,
                                    sugestao=suggestion, confianca=confidence, evidencia=evidence,
                                    metodo=VERSION, origem="automatica_sem_revisao",
                                    rotulo_final="", revisor="", revisado_em=""))
    for item in _rows(path, "Releases"):
        suggestion, confidence, evidence = corrective(item.get("notas_da_release") or "", item.get("commits") or "")
        suggestions.append(dict(escopo="releases", repositorio=item["repositorio"], tag=item["tag"],
                                dimensao="corretiva", sugestao=suggestion, confianca=confidence,
                                evidencia=evidence, metodo=VERSION, origem="automatica_sem_revisao",
                                rotulo_final="", revisor="", revisado_em=""))
    write_csv(output, FIELDS, suggestions)
    return suggestions


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera sugestoes sem preencher rotulagem_joao.xlsx.")
    parser.add_argument("--planilha", type=Path, default=Path(__file__).resolve().parent / "amostra_ouro" / "rotulagem_joao.xlsx")
    parser.add_argument("--saida", type=Path, default=Path(__file__).resolve().parent / "amostra_ouro" / "sugestoes_automaticas_joao.csv")
    args = parser.parse_args(argv)
    if args.saida.exists():
        print(f"Arquivo ja existe, nao sobrescrito: {args.saida}")
        return 1
    rows = build(args.planilha, args.saida)
    print(f"OK: {args.saida} ({len(rows)} sugestoes; planilha final intacta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
