"""Gera os arquivos estáticos lidos pelo site (site/public/data).

- index.json                → carregado na abertura: lista de ministérios, sínteses, fontes.
- ministerios/<id>.json     → carregado ao abrir um ministério.
Só dados normalizados e curados entram aqui; nada de dado bruto.
"""
from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from functools import cache

from . import curadoria
from .comum import NORMALIZADO, PUBLICADO, agora_utc, fontes, ler_csv


def _gravar(caminho, obj) -> int:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    caminho.write_text(texto, encoding="utf-8")
    return len(texto.encode())


@cache
def _csv(nome: str) -> tuple[dict, ...]:
    """Cada CSV normalizado é lido uma vez por publicação (são 38 ministérios)."""
    return tuple(ler_csv(NORMALIZADO / nome))


def _f(v) -> float:
    return round(float(v or 0), 2)


def separar_competencias(texto: str) -> list[str]:
    """Quebra "I - ...; II - ...; e III - ..." em itens."""
    if not texto:
        return []
    partes = re.split(r"(?:^|;\s*(?:e\s+)?)\s*(?=[IVXL]+\s*[-–]\s)", texto.strip())
    itens = [re.sub(r"^[IVXL]+\s*[-–]\s*", "", p).strip(" ;.") for p in partes]
    return [i[0].upper() + i[1:] for i in itens if i]


def _vigente(r) -> bool:
    return not r.get("valido_ate")


def montar_ministerio(m: dict, exercicio: int, normas: dict, fontes_reg: dict) -> dict:
    unidades = [u for u in _csv("unidade.csv") if u["ministerio_id"] == m["id"] and _vigente(u)]
    cargos = [c for c in _csv("cargo.csv") if c["ministerio_id"] == m["id"] and _vigente(c)]

    cargos_por_unidade = defaultdict(list)
    for c in cargos:
        cargos_por_unidade[c["cod_unidade"]].append([c["tipo"], c["categoria"], c["nivel"], c["denominacao"],
                                                    int(c["quantidade"]), c["mobilidade"]])

    raiz = next(u for u in unidades if u["profundidade"] == "0")
    lista_unidades = [{
        "c": u["cod_siorg"], "p": u["cod_pai"], "s": u["sigla"], "n": u["nome"], "b": u["bloco"],
        "a": u["atividade"], "t": u["tipo"], "d": int(u["profundidade"]),
        "ato": {"tipo": u["ato_tipo"], "numero": u["ato_numero"], "vigencia": u["ato_vigencia"], "url": u["ato_url"]}
        if u["ato_tipo"] else None,
    } for u in unidades]

    # Competências de cada unidade vão num arquivo à parte, carregado ao abrir o detalhe de uma unidade.
    competencias_unidades = {u["cod_siorg"]: c for u in unidades if u is not raiz
                             if (c := separar_competencias(u["competencia"]))}

    ocupantes = montar_ocupantes(m, {u["cod_siorg"] for u in unidades})

    orcamento = montar_orcamento(m, exercicio)
    politicas = [p for p in curadoria.politicas() if p["ministerio"] == m["id"]]
    for p in politicas:
        p.pop("pendentes", None)
    eventos = [e for e in curadoria.eventos() if m["id"] in (e.get("origem") or []) + (e.get("destino") or [])]
    citadas = {m.get(k) for k in ("norma_criacao", "norma_organizacao", "norma_estrutura")}
    citadas |= {e.get("norma") for e in eventos} | {p.get("norma") for p in politicas}
    siorg = fontes_reg.get("siorg", {})
    orc_fonte = fontes_reg.get(f"transparencia-orcamento-{exercicio}", {})
    return {
        "id": m["id"], "sigla": m["sigla"], "nome": m["nome"], "cod_siorg": m["cod_siorg"],
        "categoria": m.get("categoria"), "orgao_orcamentario": m.get("orgao_orcamentario"),
        "norma_criacao": m.get("norma_criacao"), "norma_organizacao": m.get("norma_organizacao"),
        "norma_estrutura": m.get("norma_estrutura"), "valido_de": m.get("valido_de"),
        "competencias": separar_competencias(raiz["competencia"]),
        "competencias_unidades": competencias_unidades,   # removido do JSON principal em publicar()
        "unidades": lista_unidades,
        "cargos": cargos_por_unidade,
        "ocupantes": ocupantes,
        "orcamento": orcamento,
        "politicas": politicas,
        "eventos": eventos,
        "normas": {k: normas[k] for k in sorted(c for c in citadas if c and c in normas)},
        "fontes": {
            "estrutura": {"nome": siorg.get("nome"), "url": siorg.get("url"), "data": siorg.get("coletado_em"),
                          "referencia": siorg.get("data_referencia")},
            "orcamento": {"nome": orc_fonte.get("nome"), "url": orc_fonte.get("url"), "data": orc_fonte.get("data_referencia")},
            "ocupantes": {"nome": fontes_reg.get("siape", {}).get("nome"), "url": fontes_reg.get("siape", {}).get("url"),
                          "data": fontes_reg.get("siape", {}).get("data_referencia"), "referencia_mes": True},
            "partidos": {"nome": fontes_reg.get("tse", {}).get("nome"), "url": fontes_reg.get("tse", {}).get("url"), "data": None},
            "politicas": {"nome": "Curadoria (data/curadoria/politicas_publicas.yaml)", "url": None, "data": None},
        },
    }


NIVEL_PUBLICADO = 15   # no site: Diretor (1.15) para cima; 1.13/1.14 ficam no CSV normalizado


def do_governo_atual(o: dict) -> bool:
    """O 1º arquivo do SIAPE (jan/2023) ainda lista dirigentes do governo anterior, exonerados em 1º/01/2023."""
    return not (o["inicio"] and o["inicio"] < "2023-01-01" and o["fim_aprox"] and o["fim_aprox"] <= "2023-03")


@cache
def _partidos() -> dict:
    """pessoa_id → candidatura mais recente no TSE (partido, ano, cargo, resultado)."""
    saida = {}
    for c in sorted(_csv("candidatura.csv"), key=lambda c: c["ano"]):
        saida[c["pessoa_id"]] = {"sigla": c["partido"], "ano": int(c["ano"]), "cargo": c["cargo"], "uf": c["uf"],
                                 "resultado": c["resultado"].capitalize(), "fonte": "TSE"}
    return saida


@cache
def _filiacoes_manuais() -> dict:
    """nome normalizado → filiação vigente informada à mão em pessoas.yaml (prevalece sobre o TSE)."""
    from .servidores import chave
    saida = {}
    for p in curadoria.pessoas():
        vig = [f for f in p.get("filiacoes") or [] if not f.get("valido_ate")]
        if vig:
            f = vig[-1]
            saida[chave(p["nome"])] = {"sigla": f["partido"], "ano": None, "cargo": None, "uf": None,
                                       "resultado": None, "fonte": f.get("fonte")}
    return saida


def montar_ocupantes(m: dict, cods: set) -> list[dict]:
    from .servidores import chave
    partidos, manuais = _partidos(), _filiacoes_manuais()
    saida = []
    for o in _csv("ocupacao.csv"):
        if o["ministerio_id"] != m["id"] or int(o["nivel"]) < NIVEL_PUBLICADO or not do_governo_atual(o):
            continue
        cargo = o["cargo"]
        papel = "titular" if o["funcao"] == "MEST" else ("adjunto" if "ADJUNT" in cargo.upper() else "titular")
        saida.append({
            "pessoa": o["pessoa_id"], "nome": o["nome"], "funcao": o["funcao"], "nivel": int(o["nivel"]),
            "cargo": "Ministro(a) de Estado" if o["funcao"] == "MEST" else cargo, "uorg": o["uorg"],
            "unidade": o["cod_siorg"] if o["cod_siorg"] in cods else None, "papel": papel,
            "de": o["inicio"] or None, "ate": o["fim_aprox"] or None,
            "partido": manuais.get(chave(o["nome"])) or partidos.get(o["pessoa_id"]),
        })
    # Acréscimos manuais (ex.: nomeação recente no DOU que o SIAPE ainda não trouxe).
    for o in curadoria.ocupacoes():
        if o["unidade"] in cods and not any(chave(x["nome"]) == chave(o.get("nome", "")) and not x["ate"] for x in saida):
            saida.append({"pessoa": None, "nome": o.get("nome"), "funcao": o.get("funcao"), "nivel": o.get("nivel", 0),
                          "cargo": o.get("cargo"), "uorg": None, "unidade": o["unidade"], "papel": o.get("papel", "titular"),
                          "de": o.get("valido_de"), "ate": o.get("valido_ate"), "partido": manuais.get(chave(o.get("nome", ""))),
                          "fonte": o.get("fonte")})
    return sorted(saida, key=lambda o: (-o["nivel"], o["ate"] is not None, o["de"] or ""))


def meses_entre(de: str | None, ate: str | None, ref: str) -> float | None:
    """Duração em meses entre 'AAAA-MM-DD' e 'AAAA-MM' (ou a data de referência, se ainda no cargo)."""
    if not de:
        return None
    a1, m1 = int(de[:4]), int(de[5:7])
    fim = ate or ref
    a2, m2 = int(fim[:4]), int(fim[5:7])
    return max(0, (a2 - a1) * 12 + (m2 - m1))


def rotatividade(ocupantes: list[dict], ref: str) -> dict:
    """Trocas e tempo médio no cargo desde jan/2023: ministros e secretários (CCE/FCE 1.17–1.18)."""
    def resumo(lista):
        dur = [d for o in lista if (d := meses_entre(o["de"], o["ate"], ref)) is not None]
        encerrados = [o for o in lista if o["ate"]]
        return {"mandatos": len(lista), "encerrados": len(encerrados),
                "meses_medio": round(sum(dur) / len(dur), 1) if dur else None}
    ministros = [o for o in ocupantes if o["funcao"] == "MEST"]
    secretarios = [o for o in ocupantes if o["nivel"] in (17, 18) and o["papel"] == "titular"]
    return {"ministros": resumo(ministros), "secretarios": resumo(secretarios)}


def montar_orcamento(m: dict, exercicio: int) -> dict | None:
    orgao = m.get("orgao_orcamentario")
    ex = str(exercicio)
    # Linhas só com restos a pagar de anos anteriores (sem dotação nem execução no ano) ficam de fora.
    valores = ("dotacao_inicial", "dotacao_atual", "empenhado", "liquidado", "pago")
    linhas = [r for r in _csv("orcamento.csv")
              if r["exercicio"] == ex and r["cod_orgao_superior"] == orgao and any(float(r[c]) for c in valores)]
    if not linhas:
        return None
    uos = {u["cod_uo"]: u["nome"] for u in _csv("uo.csv") if u["exercicio"] == ex and u["cod_orgao_superior"] == orgao}
    programas = {p["cod_programa"]: p["nome"] for p in _csv("programa.csv") if p["exercicio"] == ex}
    acoes = {a["cod_acao"]: a["nome"] for a in _csv("acao.csv") if a["exercicio"] == ex}
    usados_p = {r["cod_programa"] for r in linhas}
    usados_a = {r["cod_acao"] for r in linhas}

    mensal = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in _csv("orcamento_mensal.csv"):
        if r["exercicio"] == ex and r["cod_uo"] in uos:
            v = mensal[(int(r["mes"]), r["cod_programa"])]
            v[0] += float(r["empenhado"]); v[1] += float(r["liquidado"]); v[2] += float(r["pago"])

    corresp = {c["cod_uo"]: c.get("cod_siorg") for c in curadoria.correspondencias() if c["ministerio"] == m["id"]}
    return {
        "exercicio": exercicio,
        "data_extracao": max(r["data_extracao"] for r in linhas),
        "colunas": ["uo", "programa", "acao", "dotacao_inicial", "dotacao_atual", "empenhado", "liquidado", "pago",
                    "empenhado_emendas"],
        "linhas": [[r["cod_uo"], r["cod_programa"], r["cod_acao"], _f(r["dotacao_inicial"]), _f(r["dotacao_atual"]),
                    _f(r["empenhado"]), _f(r["liquidado"]), _f(r["pago"]), _f(r["empenhado_emendas"])]
                   for r in linhas],
        "mensal_colunas": ["mes", "programa", "empenhado", "liquidado", "pago"],
        "mensal": [[k[0], k[1], round(v[0], 2), round(v[1], 2), round(v[2], 2)] for k, v in sorted(mensal.items())],
        "uos": {c: {"nome": n, "siorg": corresp.get(c)} for c, n in uos.items()},
        "programas": {c: programas.get(c, c) for c in sorted(usados_p)},
        "acoes": {c: acoes.get(c, c) for c in sorted(usados_a)},
        # Dívida, transferências constitucionais, sentenças etc.: distorcem comparações entre ministérios.
        "operacoes_especiais": sorted(c for c in usados_p if e_operacao_especial(programas.get(c, ""))),
    }


def e_operacao_especial(nome_programa: str) -> bool:
    return nome_programa.upper().startswith("OPERACOES ESPECIAIS")


def _totais(orc: dict | None, sem_oe: bool = False) -> dict | None:
    if not orc:
        return None
    oe = set(orc["operacoes_especiais"]) if sem_oe else set()
    tot = defaultdict(float)
    for linha in orc["linhas"]:
        if linha[1] in oe:
            continue
        for i, c in enumerate(orc["colunas"][3:], start=3):
            tot[c] += linha[i]
    return {k: round(v, 2) for k, v in tot.items()}


def _mensal_acumulado(orc: dict | None, sem_oe: bool = False) -> list:
    """[[mes, empenhado, liquidado, pago]] acumulados no ano."""
    if not orc:
        return []
    oe = set(orc["operacoes_especiais"]) if sem_oe else set()
    por_mes = defaultdict(lambda: [0.0, 0.0, 0.0])
    for mes, prog, emp, liq, pago in orc["mensal"]:
        if prog not in oe:
            v = por_mes[mes]; v[0] += emp; v[1] += liq; v[2] += pago
    acc, saida = [0.0, 0.0, 0.0], []
    for mes in sorted(por_mes):
        acc = [a + b for a, b in zip(acc, por_mes[mes])]
        saida.append([mes] + [round(x, 2) for x in acc])
    return saida


def resumir(m: dict, dados: dict) -> tuple[dict, dict]:
    """Resumo para o index.json e detalhe para agregados/comparacao.json."""
    orc = dados["orcamento"]
    unidades = dados["unidades"]
    ministros = sorted([o for o in dados["ocupantes"] if o["funcao"] == "MEST"], key=lambda o: o["de"] or "")
    atuais = [o for o in ministros if not o["ate"]]
    titular = atuais[-1] if atuais else None   # mais de um no mesmo mês: o de posse mais recente
    ref = (fontes().get("siape", {}).get("data_referencia") or "")[:7] or None
    por_bloco = defaultdict(int)
    for u in unidades:
        if u["d"] > 0:
            por_bloco[u["b"]] += 1
    cargos_nivel = defaultdict(int)
    for lista in dados["cargos"].values():
        for tipo, cat, nivel, _, qtd, _ in lista:
            cargos_nivel[f"{tipo} {cat}.{nivel}" if cat and nivel else tipo] += qtd
    resumo = {
        "id": m["id"], "sigla": m["sigla"], "nome": m["nome"], "categoria": m.get("categoria"),
        "ministro": titular and {"nome": titular["nome"], "partido": titular["partido"], "desde": titular["de"]},
        "ministros": [{"nome": o["nome"], "de": o["de"], "ate": o["ate"], "partido": (o["partido"] or {}).get("sigla")} for o in ministros],
        "rotatividade": rotatividade(dados["ocupantes"], ref) if ref else None,
        "n_unidades": len(unidades),
        "n_cargos": sum(cargos_nivel.values()),
        "n_secretarias": sum(1 for u in unidades if u["d"] == 1 and u["b"] == "singular"),
        "pct_fim": round(sum(1 for u in unidades if u["a"] == "fim") / max(1, len(unidades)), 4),
        "orcamento": orc and {"exercicio": orc["exercicio"], **_totais(orc)},
        "orcamento_sem_oe": _totais(orc, sem_oe=True),
    }
    programas = []
    if orc:
        por_prog = defaultdict(lambda: [0.0, 0.0])
        for linha in orc["linhas"]:
            por_prog[linha[1]][0] += linha[4]; por_prog[linha[1]][1] += linha[7]
        top = sorted(((c, v) for c, v in por_prog.items() if c not in orc["operacoes_especiais"]), key=lambda kv: -kv[1][0])[:5]
        programas = [{"codigo": c, "nome": orc["programas"][c], "dotacao_atual": round(v[0], 2), "pago": round(v[1], 2)} for c, v in top]
    detalhe = {
        "id": m["id"],
        "unidades_por_bloco": dict(por_bloco),
        "cargos_por_nivel": dict(sorted(cargos_nivel.items())),
        "mensal": _mensal_acumulado(orc),
        "mensal_sem_oe": _mensal_acumulado(orc, sem_oe=True),
        "principais_programas": programas,
        "politicas": [p["nome"] for p in dados["politicas"]],
        "ocupantes": [{"nome": o["nome"], "cargo": o["cargo"], "partido": (o["partido"] or {}).get("sigla")}
                      for o in dados["ocupantes"] if o["papel"] == "titular" and not o["ate"]][:8],
    }
    return resumo, detalhe


def publicar(exercicio: int) -> dict[str, int]:
    """Regera site/public/data do zero. Devolve o tamanho (bytes) de cada arquivo."""
    _csv.cache_clear(); _partidos.cache_clear(); _filiacoes_manuais.cache_clear()
    if PUBLICADO.exists():
        shutil.rmtree(PUBLICADO)
    normas = {n["id"]: n for n in curadoria.normas()}
    fontes_reg = fontes()
    tamanhos, resumos, detalhes = {}, [], []
    for m in curadoria.no_escopo():
        dados = montar_ministerio(m, exercicio, normas, fontes_reg)
        comp = dados.pop("competencias_unidades")
        tamanhos[f"ministerios/{m['id']}.json"] = _gravar(PUBLICADO / "ministerios" / f"{m['id']}.json", dados)
        tamanhos[f"ministerios/{m['id']}-competencias.json"] = _gravar(
            PUBLICADO / "ministerios" / f"{m['id']}-competencias.json", comp)
        r, d = resumir(m, dados)
        resumos.append(r)
        detalhes.append(d)
    index = {
        "gerado_em": agora_utc(),
        "exercicio": exercicio,
        "ministerios": sorted(resumos, key=lambda r: r["nome"]),
        "eventos": curadoria.eventos(),
        "fontes": {k: {c: v[c] for c in ("nome", "url", "data_referencia", "coletado_em")} for k, v in fontes_reg.items()},
    }
    tamanhos["index.json"] = _gravar(PUBLICADO / "index.json", index)
    tamanhos["agregados/comparacao.json"] = _gravar(PUBLICADO / "agregados" / "comparacao.json",
                                                    {"exercicio": exercicio, "ministerios": detalhes})
    return tamanhos
