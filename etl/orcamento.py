"""Orçamento e execução — downloads abertos do Portal da Transparência (CGU), sem chave de API.

- "Orçamento da Despesa" (anual): dotação inicial e atualizada por UO, programa e ação.
- "Despesas – Execução" (mensal): empenhado, liquidado e pago no mês, com autor de emenda.
"""
from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import curadoria
from .comum import BRUTO, NORMALIZADO, baixar, gravar_csv, ler_csv, registrar_fonte, sha256_obj

BASE = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida"
PASTA = BRUTO / "transparencia"

CAMPOS_ORC = [
    "exercicio", "cod_orgao_superior", "cod_orgao", "cod_uo", "cod_programa", "cod_acao",
    "dotacao_inicial", "dotacao_atual", "empenhado", "liquidado", "pago", "rp_pago",
    "empenhado_emendas", "empenhado_orcdesp", "data_extracao",
]
CAMPOS_MENSAL = ["exercicio", "mes", "cod_uo", "cod_programa", "cod_acao", "empenhado", "liquidado", "pago"]


def url_anual(ano: int) -> str:
    return f"{BASE}/orcamento-despesa/{ano}_OrcamentoDespesa.zip"


def url_mensal(ano: int, mes: int) -> str:
    return f"{BASE}/despesas-execucao/{ano}{mes:02d}_Despesas.zip"


def coletar(exercicio: int) -> None:
    baixar(url_anual(exercicio), PASTA / f"orcamento_{exercicio}.zip")
    hoje = date.today()
    ultimo_mes = hoje.month if exercicio == hoje.year else 12
    for mes in range(1, ultimo_mes + 1):
        destino = PASTA / f"execucao_{exercicio}{mes:02d}.zip"
        # Meses antigos já baixados não mudam; os 2 mais recentes ainda recebem lançamentos.
        if destino.exists() and mes < ultimo_mes - 1:
            continue
        try:
            baixar(url_mensal(exercicio, mes), destino)
        except RuntimeError:
            if mes >= ultimo_mes - 1:   # mês corrente ainda não publicado
                break
            raise


def _num(s: str) -> float:
    return float((s or "0").replace(".", "").replace(",", ".")) if s and "," in s else float(s or 0)


def _linhas_zip(caminho: Path, info: dict):
    """Lê o CSV (latin-1, ';') de dentro do zip e grava em `info["data"]` a data do arquivo."""
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        info["data"] = date(*z.getinfo(nome).date_time[:3]).isoformat()
        with z.open(nome) as f:
            yield from csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")


def ler_anual(caminho: Path, orgaos: set[str]):
    """Agrega o arquivo anual por UO × programa × ação."""
    agg = defaultdict(lambda: defaultdict(float))
    nomes = {"uo": {}, "programa": {}, "acao": {}}
    info = {}
    for r in _linhas_zip(caminho, info):
        if r["CÓDIGO ÓRGÃO SUPERIOR"] not in orgaos:
            continue
        k = (r["EXERCÍCIO"], r["CÓDIGO ÓRGÃO SUPERIOR"], r["CÓDIGO ÓRGÃO SUBORDINADO"],
             r["CÓDIGO UNIDADE ORÇAMENTÁRIA"], r["CÓDIGO PROGRAMA ORÇAMENTÁRIO"], r["CÓDIGO AÇÃO"])
        a = agg[k]
        a["dotacao_inicial"] += _num(r["ORÇAMENTO INICIAL (R$)"])
        a["dotacao_atual"] += _num(r["ORÇAMENTO ATUALIZADO (R$)"])
        a["empenhado_orcdesp"] += _num(r["ORÇAMENTO EMPENHADO (R$)"])
        nomes["uo"][r["CÓDIGO UNIDADE ORÇAMENTÁRIA"]] = (r["NOME UNIDADE ORÇAMENTÁRIA"], r["CÓDIGO ÓRGÃO SUBORDINADO"],
                                                        r["NOME ÓRGÃO SUBORDINADO"], r["CÓDIGO ÓRGÃO SUPERIOR"])
        nomes["programa"][r["CÓDIGO PROGRAMA ORÇAMENTÁRIO"]] = r["NOME PROGRAMA ORÇAMENTÁRIO"]
        nomes["acao"][r["CÓDIGO AÇÃO"]] = (r["NOME AÇÃO"], r["CÓDIGO PROGRAMA ORÇAMENTÁRIO"])
    return agg, nomes, info["data"]


def ler_mensal(caminho: Path, uos: set[str]):
    """Agrega um mês de execução por UO × programa × ação. Filtra pela UO (e não pelo órgão
    da unidade gestora) para incluir despesas descentralizadas para outros órgãos executarem."""
    agg = defaultdict(lambda: defaultdict(float))
    info = {}
    for r in _linhas_zip(caminho, info):
        if r["Código Unidade Orçamentária"] not in uos:
            continue
        k =(r["Código Unidade Orçamentária"], r["Código Programa Orçamentário"], r["Código Ação"])
        a = agg[k]
        a["empenhado"] += _num(r["Valor Empenhado (R$)"])
        a["liquidado"] += _num(r["Valor Liquidado (R$)"])
        a["pago"] += _num(r["Valor Pago (R$)"])
        a["rp_pago"] += _num(r["Valor Restos a Pagar Pagos (R$)"])
        if r["Nome Autor Emenda"] not in ("SEM EMENDA", "Sem informação", ""):
            a["empenhado_emendas"] += _num(r["Valor Empenhado (R$)"])
    return agg, info["data"]


def _r(v: float) -> str:
    return f"{v:.2f}"


def normalizar(exercicio: int) -> bool:
    escopo = curadoria.no_escopo()
    orgaos = {m["orgao_orcamentario"] for m in escopo if m.get("orgao_orcamentario")}
    anual, nomes, data_anual = ler_anual(PASTA / f"orcamento_{exercicio}.zip", orgaos)
    uos = set(nomes["uo"])

    acumulado = defaultdict(lambda: defaultdict(float))
    mensal, datas = [], [data_anual]
    for arq in sorted(PASTA.glob(f"execucao_{exercicio}??.zip")):
        agg, data_arq = ler_mensal(arq, uos)
        datas.append(data_arq)
        mes = int(arq.stem[-2:])
        for k, v in agg.items():
            for campo, valor in v.items():
                acumulado[k][campo] += valor
            mensal.append({"exercicio": exercicio, "mes": mes, "cod_uo": k[0], "cod_programa": k[1], "cod_acao": k[2],
                           "empenhado": _r(v["empenhado"]), "liquidado": _r(v["liquidado"]), "pago": _r(v["pago"])})

    extracao = max(datas)
    linhas, chaves_exec = [], set(acumulado)
    for k, a in anual.items():
        e = acumulado.get((k[3], k[4], k[5]), {})
        chaves_exec.discard((k[3], k[4], k[5]))
        linhas.append(_linha(k, a, e, extracao))
    # Execução sem dotação no arquivo anual (ex.: créditos extraordinários tardios) não pode sumir.
    for uo, prog, acao in chaves_exec:
        _, cod_orgao, _, sup = nomes["uo"][uo]
        linhas.append(_linha((str(exercicio), sup, cod_orgao, uo, prog, acao), {}, acumulado[(uo, prog, acao)], extracao))

    _substituir_exercicio("orcamento.csv", linhas, CAMPOS_ORC, exercicio,
                          ["exercicio", "cod_uo", "cod_programa", "cod_acao"])
    _substituir_exercicio("orcamento_mensal.csv", mensal, CAMPOS_MENSAL, exercicio,
                          ["exercicio", "mes", "cod_uo", "cod_programa", "cod_acao"])
    _substituir_exercicio("uo.csv", [{"exercicio": exercicio, "cod_uo": c, "nome": n[0], "cod_orgao": n[1],
                                      "nome_orgao": n[2], "cod_orgao_superior": n[3]} for c, n in nomes["uo"].items()],
                          ["exercicio", "cod_uo", "nome", "cod_orgao", "nome_orgao", "cod_orgao_superior"],
                          exercicio, ["exercicio", "cod_uo"])
    _substituir_exercicio("programa.csv", [{"exercicio": exercicio, "cod_programa": c, "nome": n}
                                           for c, n in nomes["programa"].items()],
                          ["exercicio", "cod_programa", "nome"], exercicio, ["exercicio", "cod_programa"])
    _substituir_exercicio("acao.csv", [{"exercicio": exercicio, "cod_acao": c, "cod_programa": n[1], "nome": n[0]}
                                       for c, n in nomes["acao"].items()],
                          ["exercicio", "cod_acao", "cod_programa", "nome"], exercicio, ["exercicio", "cod_acao"])

    conteudo = sorted((tuple(r[c] for c in CAMPOS_ORC if c != "data_extracao") for r in linhas))
    return registrar_fonte(f"transparencia-orcamento-{exercicio}",
                           f"Portal da Transparência – Orçamento da Despesa e Execução {exercicio} (CGU)",
                           f"https://portaldatransparencia.gov.br/download-de-dados/orcamento-despesa/{exercicio}",
                           sha256_obj(conteudo), extracao)


def _linha(k, a, e, extracao):
    return {
        "exercicio": k[0], "cod_orgao_superior": k[1], "cod_orgao": k[2], "cod_uo": k[3],
        "cod_programa": k[4], "cod_acao": k[5],
        "dotacao_inicial": _r(a.get("dotacao_inicial", 0)), "dotacao_atual": _r(a.get("dotacao_atual", 0)),
        "empenhado": _r(e.get("empenhado", 0)), "liquidado": _r(e.get("liquidado", 0)), "pago": _r(e.get("pago", 0)),
        "rp_pago": _r(e.get("rp_pago", 0)), "empenhado_emendas": _r(e.get("empenhado_emendas", 0)),
        "empenhado_orcdesp": _r(a.get("empenhado_orcdesp", 0)), "data_extracao": extracao,
    }


def _substituir_exercicio(nome: str, novas: list[dict], campos: list[str], exercicio: int, chave: list[str]) -> None:
    """Orçamento é versionado por exercício + data de extração: as linhas do exercício são trocadas."""
    caminho = NORMALIZADO / nome
    mantidas = [r for r in ler_csv(caminho) if r["exercicio"] != str(exercicio)]
    gravar_csv(caminho, mantidas + novas, campos, chave)
