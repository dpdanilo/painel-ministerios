"""Sugere correspondências UO (orçamento) ↔ unidade SIORG para UOs ainda não mapeadas.

Regras, em ordem:
1. UO da administração direta (código <2 dígitos do órgão>101, ex.: 56101) → o próprio ministério.
2. Nome do órgão subordinado igual (sem acento, caixa e pontuação) ao nome de uma unidade do ministério no SIORG.
3. Sem correspondência → `cod_siorg: null` com nota, para revisão humana.

As sugestões entram em correspondencia_siorg_orcamento.yaml com `metodo: automatico_nome`.
Uma pessoa pode corrigir a linha e trocar o método para `manual`.
"""
from __future__ import annotations

import re
import unicodedata

from . import curadoria
from .comum import CURADORIA, NORMALIZADO, hoje, ler_csv

ARQUIVO = CURADORIA / "correspondencia_siorg_orcamento.yaml"


def chave_nome(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\s*-\s*unidades com vinculo direto$", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(w for w in s.split() if w not in {"da", "do", "de", "dos", "das", "e", "s", "a"})


def sugerir(exercicio: int) -> list[dict]:
    escopo = {m["orgao_orcamentario"]: m for m in curadoria.no_escopo() if m.get("orgao_orcamentario")}
    ja = {c["cod_uo"] for c in curadoria.correspondencias()}
    unidades = [u for u in ler_csv(NORMALIZADO / "unidade.csv") if not u["valido_ate"]]
    por_min = {}
    for u in unidades:
        por_min.setdefault(u["ministerio_id"], {}).setdefault(chave_nome(u["nome"]), u["cod_siorg"])

    saida = []
    for uo in ler_csv(NORMALIZADO / "uo.csv"):
        if uo["exercicio"] != str(exercicio) or uo["cod_uo"] in ja or uo["cod_orgao_superior"] not in escopo:
            continue
        m = escopo[uo["cod_orgao_superior"]]
        nome_sub = chave_nome(uo["nome_orgao"])
        if uo["cod_uo"] == uo["cod_orgao_superior"][:2] + "101":
            cod, nota = m["cod_siorg"], None
        else:
            cod = por_min.get(m["id"], {}).get(nome_sub)
            nota = None if cod else "Sem correspondência automática pelo nome; revisar."
        linha = {"ministerio": m["id"], "cod_uo": uo["cod_uo"], "nome_uo": uo["nome"], "cod_siorg": cod,
                 "valido_de": f"{exercicio}-01-01", "metodo": "automatico_nome",
                 "fonte": f"Correspondência automática por nome: Portal da Transparência ({uo['nome_orgao']}) × SIORG, gerada em {hoje()}"}
        if nota:
            linha["nota"] = nota
        saida.append(linha)
    return saida


def _yaml_str(v) -> str:
    if v is None:
        return "null"
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def gravar(sugestoes: list[dict]) -> int:
    if not sugestoes:
        return 0
    blocos = []
    for s in sorted(sugestoes, key=lambda x: (x["ministerio"], x["cod_uo"])):
        campos = "\n".join(f"    {k}: {_yaml_str(v)}" for k, v in s.items() if k != "ministerio")
        blocos.append(f"  - ministerio: {s['ministerio']}\n{campos}\n")
    with open(ARQUIVO, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n  # --- Sugeridas automaticamente em {hoje()} (revisar)\n" + "\n".join(blocos))
    return len(sugestoes)
