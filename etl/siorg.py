"""SIORG (MGI): árvore organizacional, competências e cargos/funções alocados.

API: https://api.siorg.economia.gov.br (documentação) — base https://estruturaorganizacional.dados.gov.br/doc
"""
from __future__ import annotations

import re
from collections import defaultdict

from . import curadoria
from .comum import BRUTO, NORMALIZADO, baixar, gravar_csv, hoje, ler_csv, ler_json, registrar_fonte, sha256_obj
from .versionamento import mesclar

BASE = "https://estruturaorganizacional.dados.gov.br/doc"
PASTA = BRUTO / "siorg"

# Categoria SIORG do órgão de 1º nível → bloco do art. 2º dos decretos de estrutura.
BLOCO_POR_CATEGORIA = {"6": "assistencia", "8": "singular", "7": "colegiado"}
ATIVIDADE = {"Finalística": "fim", "Suporte": "meio"}

CAMPOS_UNIDADE = [
    "cod_siorg", "cod_pai", "ministerio_id", "sigla", "nome", "tipo", "categoria", "bloco",
    "atividade", "profundidade", "competencia", "ato_tipo", "ato_numero", "ato_vigencia", "ato_url",
    "versao_siorg", "valido_de", "valido_ate",
]
MONITORADOS_UNIDADE = ["cod_pai", "sigla", "nome", "tipo", "categoria", "bloco", "atividade", "competencia"]

CAMPOS_CARGO = [
    "cod_unidade", "ministerio_id", "tipo", "categoria", "nivel", "denominacao", "mobilidade",
    "quantidade", "valido_de", "valido_ate",
]


def _id(uri: str | None) -> str:
    """O SIORG devolve códigos como URIs (…/unidade-organizacional/308798)."""
    return (uri or "").rstrip("/").rsplit("/", 1)[-1]


def coletar() -> None:
    for m in curadoria.no_escopo():
        url = f"{BASE}/estrutura-organizacional/completa?codigoUnidade={m['cod_siorg']}&retornarOrgaoEntidadeVinculados=SIM"
        baixar(url, PASTA / f"estrutura_{m['cod_siorg']}.json")
    # Não há filtro por órgão neste serviço: baixa o governo todo (~55 MB) e filtra depois.
    baixar(f"{BASE}/cargo-funcao/alocados-estrutura", PASTA / "cargos_alocados.json", timeout=600)


def _limpar(texto: str | None) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def unidades_de(bruto: list[dict], ministerio_id: str, cod_ministerio: str) -> list[dict]:
    """Normaliza a resposta de /estrutura-organizacional/completa de um ministério."""
    por_cod = {_id(u["codigoUnidade"]): u for u in bruto}
    filhos = defaultdict(list)
    for cod, u in por_cod.items():
        filhos[_id(u["codigoUnidadePai"])].append(cod)

    saida = []

    def visitar(cod: str, profundidade: int, bloco_herdado: str):
        u = por_cod[cod]
        tipo = _id(u["codigoTipoUnidade"])
        categoria = _id(u.get("codigoCategoriaUnidade"))
        if tipo == "unidade-colegiada":
            bloco = "colegiado"
        elif tipo == "entidade":
            bloco = "vinculada"
        elif profundidade == 1:
            bloco = BLOCO_POR_CATEGORIA.get(categoria, "outro")
        else:
            bloco = bloco_herdado
        ato = u.get("atoNormativo") or {}
        saida.append({
            "cod_siorg": cod,
            "cod_pai": "" if profundidade == 0 else _id(u["codigoUnidadePai"]),
            "ministerio_id": ministerio_id,
            "sigla": _limpar(u.get("sigla")),
            "nome": _limpar(u.get("nome")),
            "tipo": tipo,
            "categoria": categoria,
            "bloco": "" if profundidade == 0 else bloco,
            "atividade": ATIVIDADE.get(u.get("areaAtuacao") or "", ""),
            "profundidade": profundidade,
            "competencia": _limpar(u.get("competencia")),
            "ato_tipo": ato.get("tipoAto") or "",
            "ato_numero": ato.get("numero") or "",
            "ato_vigencia": ato.get("dataVigencia") or "",
            "ato_url": ato.get("url") or "",
            "versao_siorg": u.get("versaoConsulta") or "",
            "valido_de": u.get("dataInicialVersaoConsulta") or "",
        })
        # Entidades vinculadas entram só como nó; sua estrutura interna é de outro órgão.
        if tipo != "entidade":
            for f in sorted(filhos.get(cod, []), key=lambda c: por_cod[c].get("nome") or ""):
                visitar(f, profundidade + 1, bloco)

    visitar(cod_ministerio, 0, "")
    return saida


def cargos_de(alocados: list[dict], ministerio_id: str, cod_ministerio: str) -> list[dict]:
    agregados: dict[tuple, int] = defaultdict(int)
    for c in alocados:
        if str(c.get("codigoOrgao")) != cod_ministerio:
            continue
        chave = (str(c["codigoUnidade"]), c.get("siglaCargo") or "", c.get("categoriaCargo") or "",
                 c.get("nivelCargo") or "", _limpar(c.get("denominacaoCargo")), c.get("mobilidade") or "")
        agregados[chave] += int(c.get("total") or 0)
    return [
        {"cod_unidade": k[0], "ministerio_id": ministerio_id, "tipo": k[1], "categoria": k[2], "nivel": k[3],
         "denominacao": k[4], "mobilidade": k[5], "quantidade": q}
        for k, q in agregados.items()
    ]


def normalizar() -> bool:
    escopo = curadoria.no_escopo()
    alocados = ler_json(PASTA / "cargos_alocados.json")["cargosAlocadosEstrutura"]
    novas_unidades, novos_cargos, datas = [], [], []
    for m in escopo:
        bruto = ler_json(PASTA / f"estrutura_{m['cod_siorg']}.json")["unidades"]
        un = unidades_de(bruto, m["id"], m["cod_siorg"])
        novas_unidades += un
        datas.append(un[0]["valido_de"])
        novos_cargos += cargos_de(alocados, m["id"], m["cod_siorg"])

    ids = {"ministerio_id": {m["id"] for m in escopo}}
    snapshot = hoje()
    unidades = mesclar(ler_csv(NORMALIZADO / "unidade.csv"), novas_unidades, ["cod_siorg"],
                       MONITORADOS_UNIDADE, snapshot, ids)
    cargos = mesclar(ler_csv(NORMALIZADO / "cargo.csv"), novos_cargos,
                     ["cod_unidade", "tipo", "categoria", "nivel", "denominacao", "mobilidade"],
                     ["quantidade"], snapshot, ids)
    gravar_csv(NORMALIZADO / "unidade.csv", unidades, CAMPOS_UNIDADE, ["ministerio_id", "cod_siorg", "valido_de"])
    gravar_csv(NORMALIZADO / "cargo.csv", cargos, CAMPOS_CARGO,
               ["ministerio_id", "cod_unidade", "tipo", "categoria", "nivel", "denominacao", "mobilidade", "valido_de"])

    # O hash ignora o cabeçalho "servico" (traz data e IP da requisição, que mudam sempre).
    conteudo = {"unidades": sorted(novas_unidades, key=lambda r: r["cod_siorg"]),
                "cargos": sorted(novos_cargos, key=lambda r: tuple(map(str, r.values())))}
    return registrar_fonte("siorg", "SIORG – Estrutura Organizacional (MGI)",
                           "https://estruturaorganizacional.dados.gov.br/doc", sha256_obj(conteudo),
                           max(datas) if datas else "")
