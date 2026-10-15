"""Pagina local para revisar sugestoes sem expor rotulos de outros avaliadores."""

from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path
from typing import Sequence

from openpyxl import load_workbook

from labs.lab03_dora.amostra_ouro import GOLD_DIR

HTML = r"""<!doctype html>
<html lang="pt-BR"><meta charset="utf-8"><title>Revisão da rotulagem de João</title>
<style>
body{font:16px system-ui;margin:0;background:#f5f6f8;color:#17202a}
main{max-width:960px;margin:24px auto;padding:24px;background:white;border-radius:12px}
header{display:flex;justify-content:space-between;gap:16px;align-items:center}
button{padding:10px 14px;margin:4px;border:1px solid #aeb5bf;border-radius:7px;background:white;cursor:pointer}
button.selected{background:#174ea6;color:white}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:300px;overflow:auto;background:#f5f6f8;padding:14px}
.meta{color:#555} .warning{color:#a43b00;font-weight:bold}
</style>
<main>
<header><h1>Revisão da rotulagem</h1><span id="progress"></span></header>
<p class="warning">As sugestões vieram de regras automáticas. Confirme cada decisão pelas evidências.</p>
<h2 id="title"></h2><p id="meta" class="meta"></p><p id="suggestion"></p>
<p><a id="link" target="_blank" rel="noopener noreferrer">Abrir no GitHub</a></p>
<h3>Evidências</h3><pre id="evidence"></pre>
<h3>Seu rótulo final</h3><div id="choices"></div>
<p><button id="back">Anterior</button><button id="next">Próximo</button>
<button id="export">Exportar decisões CSV</button></p>
</main>
<script>
const payload = JSON.parse(new TextDecoder().decode(Uint8Array.from(atob("DATA_B64"), c => c.charCodeAt(0))));
const items = payload.items, key = "lab03-revisao-joao-v1";
let state = JSON.parse(localStorage.getItem(key) || "{}"), index = 0;
const $ = id => document.getElementById(id);
function options(item) {
  if(item.dimensao==="tipo_projeto") return ["biblioteca/framework","aplicacao/servico","ferramenta CLI","outro"];
  return item.dimensao==="entregas_reais" ? ["sim","nao","incerto"] : ["sim","nao"];
}
function render() {
  const item=items[index], id=String(index), chosen=state[id];
  $("progress").textContent=(index+1)+"/"+items.length+" · "+Object.keys(state).length+" revisados";
  $("title").textContent=item.repositorio+(item.tag?" · "+item.tag:"")+" · "+item.dimensao;
  $("meta").textContent="Confiança automática: "+item.confianca+" · Método: "+item.metodo;
  $("suggestion").textContent="Sugestão: "+item.sugestao+" · "+item.evidencia;
  $("evidence").textContent=item.texto;
  $("link").href=item.link.startsWith("https://github.com/")?item.link:"#";
  $("choices").replaceChildren();
  for(const label of options(item)) {
    const button=document.createElement("button");
    button.textContent=label;
    if(chosen && chosen.rotulo_final===label) button.classList.add("selected");
    button.onclick=()=>{state[id]={rotulo_final:label,revisor:"João",revisado_em:new Date().toISOString()};
      localStorage.setItem(key,JSON.stringify(state));render();};
    $("choices").append(button);
  }
}
$("back").onclick=()=>{index=Math.max(0,index-1);render()};
$("next").onclick=()=>{index=Math.min(items.length-1,index+1);render()};
$("export").onclick=()=>{
  const headers=["escopo","repositorio","tag","dimensao","sugestao","confianca","evidencia","metodo","origem","rotulo_final","revisor","revisado_em"];
  const quote=v=>'"'+String(v??"").replaceAll('"','""')+'"';
  const rows=[headers.join(",")];
  items.forEach((item,i)=>{const decision=state[String(i)]||{};
    const merged={...item,...decision,origem:decision.rotulo_final?"automatico_revisado":"automatica_sem_revisao"};
    rows.push(headers.map(h=>quote(merged[h])).join(","));});
  const blob=new Blob([rows.join("\r\n")+"\r\n"],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob), a=document.createElement("a");
  a.href=url;a.download="revisao_joao.csv";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
render();
</script></html>"""


def sheet_rows(path: Path, name: str) -> list[dict]:
    book = load_workbook(path, read_only=True, data_only=True)
    rows = book[name].values
    header = next(rows)
    result = [dict(zip(header, row)) for row in rows]
    book.close()
    return result


def build(gold_dir: Path, output: Path) -> Path:
    with (gold_dir / "sugestoes_automaticas_joao.csv").open(newline="", encoding="utf-8") as file:
        suggestions = list(csv.DictReader(file))
    source = gold_dir / "rotulagem_joao.xlsx"
    repos = {row["repositorio"]: row for row in sheet_rows(source, "Repositorios")}
    releases = {(row["repositorio"], row["tag"]): row for row in sheet_rows(source, "Releases")}
    items = []
    for suggestion in suggestions:
        repo, tag = suggestion["repositorio"], suggestion["tag"]
        row = repos[repo] if suggestion["escopo"] == "repositorios" else releases[(repo, tag)]
        text = (
            f"Descrição: {row.get('descricao') or ''}\nTópicos: {row.get('topicos') or ''}"
            if not tag else f"Notas:\n{row.get('notas_da_release') or ''}\n\nCommits:\n{row.get('commits') or ''}"
        )
        link = row.get("link") if not tag else row.get("link_release")
        items.append({**suggestion, "texto": text, "link": link or ""})
    encoded = base64.b64encode(json.dumps({"items": items}, ensure_ascii=False).encode()).decode()
    output.write_text(HTML.replace("DATA_B64", encoded), encoding="utf-8")
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera pagina HTML de revisao da amostra-ouro.")
    parser.add_argument("--amostra", type=Path, default=GOLD_DIR)
    parser.add_argument("--saida", type=Path, default=GOLD_DIR / "revisao_joao.html")
    args = parser.parse_args(argv)
    try:
        path = build(args.amostra, args.saida)
    except (FileNotFoundError, KeyError) as error:
        print(f"Nao foi possivel gerar revisao: {error}")
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
