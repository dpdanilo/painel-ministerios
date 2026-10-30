"""Série histórica do orçamento (2014 em diante) e IPCA para correção monetária.

- Orçamento: arquivo anual "Orçamento da Despesa" do Portal da Transparência (2014 é o 1º disponível).
  Para anos encerrados ele já traz o valor final de empenhado e realizado (pago). Não há liquidado.
- A série é por **órgão orçamentário** (código estável, ex.: 56000). O Portal rotula cada código com o nome
  atual, mesmo em anos em que o órgão tinha outro nome ou estava dentro de outro ministério.
- IPCA: número-índice mensal do IBGE (SIDRA, tabela 1737), para expressar valores em reais de hoje.
"""
from __future__ import annotations

import json
import urllib.request
from collections import defaultdict
from datetime import date

from . import curadoria
from .comum import BRUTO, NORMALIZADO, USER_AGENT, baixar, gravar_csv, registrar_fonte, sha256_obj
from .orcamento import PASTA, _linhas_zip, _num, url_anual
from .publicar import e_operacao_especial

PRIMEIRO_ANO = 2014
URL_IPCA = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/all"

CAMPOS = ["exercicio", "cod_orgao_superior", "cod_programa", "nome_programa", "operacao_especial",
          "dotacao_inicial", "dotacao_atual", "empenhado", "pago"]


def anos_encerrados() -> list[int]:
    return list(range(PRIMEIRO_ANO, date.today().year))


def coletar() -> None:
    for ano in anos_encerrados():
        destino = PASTA / f"orcamento_{ano}.zip"
        # Ano encerrado há mais de um ano não muda; o anterior ainda recebe ajustes de fechamento.
        if destino.exists() and ano < date.today().year - 1:
            continue
        baixar(url_anual(ano), destino, pausa=2.0)
    req = urllib.request.Request(URL_IPCA, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        (BRUTO / "ipca.json").write_bytes(r.read())


def normalizar() -> bool:
    orgaos = {m["orgao_orcamentario"] for m in curadoria.no_escopo() if m.get("orgao_orcamentario")}
    orgaos |= {c for m in curadoria.ministerios() for v in m["versoes"] for c in v.get("orgaos_orcamentarios_historicos") or []}
    agg = defaultdict(lambda: defaultdict(float))
    nomes = {}
    for ano in anos_encerrados():
        arq = PASTA / f"orcamento_{ano}.zip"
        if not arq.exists():
            continue
        info = {}
        for r in _linhas_zip(arq, info):
            if r["CÓDIGO ÓRGÃO SUPERIOR"] not in orgaos:
                continue
            k = (ano, r["CÓDIGO ÓRGÃO SUPERIOR"], r["CÓDIGO PROGRAMA ORÇAMENTÁRIO"])
            nomes[k] = r["NOME PROGRAMA ORÇAMENTÁRIO"]
            a = agg[k]
            a["dotacao_inicial"] += _num(r["ORÇAMENTO INICIAL (R$)"])
            a["dotacao_atual"] += _num(r["ORÇAMENTO ATUALIZADO (R$)"])
            a["empenhado"] += _num(r["ORÇAMENTO EMPENHADO (R$)"])
            a["pago"] += _num(r["ORÇAMENTO REALIZADO (R$)"])
    linhas = [{
        "exercicio": k[0], "cod_orgao_superior": k[1], "cod_programa": k[2], "nome_programa": nomes[k],
        "operacao_especial": int(e_operacao_especial(nomes[k], k[2])),
        **{c: f"{v[c]:.2f}" for c in ("dotacao_inicial", "dotacao_atual", "empenhado", "pago")},
    } for k, v in agg.items()]
    gravar_csv(NORMALIZADO / "orcamento_historico.csv", linhas, CAMPOS, ["exercicio", "cod_orgao_superior", "cod_programa"])

    ipca = []
    if (BRUTO / "ipca.json").exists():
        for r in json.loads((BRUTO / "ipca.json").read_text(encoding="utf-8"))[1:]:
            if r["V"] not in ("", "...", "-"):
                ipca.append({"mes": f"{r['D3C'][:4]}-{r['D3C'][4:]}", "indice": r["V"]})
        gravar_csv(NORMALIZADO / "ipca.csv", ipca, ["mes", "indice"], ["mes"])
        registrar_fonte("ipca", "IBGE – IPCA, número-índice (SIDRA, tabela 1737)", "https://sidra.ibge.gov.br/tabela/1737",
                        sha256_obj(ipca), (ipca[-1]["mes"] + "-01") if ipca else "")
    return registrar_fonte("transparencia-orcamento-historico",
                           f"Portal da Transparência – Orçamento da Despesa {PRIMEIRO_ANO}–{anos_encerrados()[-1]} (CGU)",
                           "https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa",
                           sha256_obj(sorted(tuple(l.values()) for l in linhas)), f"{anos_encerrados()[-1]}-12-31")


def fatores_ipca(ipca: list[dict]) -> dict[int, float]:
    """Multiplicador para levar valores de cada ano a reais do último mês com IPCA.
    Usa a média do índice no ano (o gasto se distribui ao longo dele)."""
    if not ipca:
        return {}
    por_ano = defaultdict(list)
    for r in ipca:
        por_ano[int(r["mes"][:4])].append(float(r["indice"]))
    atual = float(ipca[-1]["indice"])
    return {ano: round(atual / (sum(v) / len(v)), 6) for ano, v in por_ano.items()}
