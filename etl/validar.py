"""Validação da curadoria e dos dados normalizados.

Erros bloqueiam a publicação; avisos aparecem no log (e viram issue no GitHub Actions).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from . import curadoria
from .comum import NORMALIZADO, fontes, ler_csv

# Idade máxima (dias) da data de referência de cada fonte antes de gerar alerta.
IDADE_MAXIMA = {"transparencia-orcamento": 21}   # o SIAPE tem ~2 meses de atraso por natureza: sem alerta


class Relatorio:
    def __init__(self):
        self.erros: list[str] = []
        self.avisos: list[str] = []

    def erro(self, msg):
        self.erros.append(msg)

    def aviso(self, msg):
        self.avisos.append(msg)

    def texto(self) -> str:
        linhas = [f"ERRO  {e}" for e in self.erros] + [f"AVISO {a}" for a in self.avisos]
        return "\n".join(linhas) or "OK – nenhuma inconsistência"


def _sobrepoe(a_de, a_ate, b_de, b_ate) -> bool:
    fim = "9999-12-31"
    return (a_de or "0000") < (b_ate or fim) and (b_de or "0000") < (a_ate or fim)


def _checar_vigencia(rel, onde, de, ate):
    if de and ate and de > ate:
        rel.erro(f"{onde}: valido_de {de} posterior a valido_ate {ate}")


def validar_curadoria(rel: Relatorio, pasta=None, unidades: dict | None = None, acoes: set | None = None,
                      programas: set | None = None, uos: set | None = None) -> None:
    normas = {n["id"]: n for n in curadoria.normas(pasta)}
    ministerios = curadoria.ministerios(pasta)
    ids_min = set()

    for n in normas.values():
        if not n.get("url"):
            rel.erro(f"norma {n['id']}: sem url/fonte")

    for m in ministerios:
        if m["id"] in ids_min:
            rel.erro(f"ministério {m['id']}: id duplicado")
        ids_min.add(m["id"])
        versoes = m.get("versoes") or []
        if m.get("no_painel") and not curadoria.versao_vigente(m):
            rel.erro(f"ministério {m['id']}: está no painel mas não tem versão vigente")
        for i, v in enumerate(versoes):
            onde = f"ministério {m['id']} versão {i + 1}"
            if not v.get("fonte"):
                rel.erro(f"{onde}: sem fonte")
            _checar_vigencia(rel, onde, v.get("valido_de"), v.get("valido_ate"))
            for campo in ("norma_criacao", "norma_extincao", "norma_organizacao", "norma_estrutura"):
                if v.get(campo) and v[campo] not in normas:
                    rel.erro(f"{onde}: {campo} '{v[campo]}' não existe em normas.yaml")
            for w in versoes[i + 1:]:
                if _sobrepoe(v.get("valido_de"), v.get("valido_ate"), w.get("valido_de"), w.get("valido_ate")):
                    rel.erro(f"ministério {m['id']}: versões com vigências sobrepostas")
        if m.get("no_painel"):
            vig = curadoria.versao_vigente(m) or {}
            if unidades is not None and vig.get("cod_siorg") and vig["cod_siorg"] not in unidades:
                rel.erro(f"ministério {m['id']}: cod_siorg {vig['cod_siorg']} não está nos dados do SIORG")

    for e in curadoria.eventos(pasta):
        if not e.get("fonte"):
            rel.erro(f"evento {e['id']}: sem fonte")
        if e.get("norma") and e["norma"] not in normas:
            rel.erro(f"evento {e['id']}: norma '{e['norma']}' não existe")
        for mid in (e.get("origem") or []) + (e.get("destino") or []):
            if mid not in ids_min:
                rel.erro(f"evento {e['id']}: ministério '{mid}' não existe em ministerios.yaml")

    for c in curadoria.correspondencias(pasta):
        onde = f"correspondência UO {c['cod_uo']}"
        if not c.get("fonte"):
            rel.erro(f"{onde}: sem fonte")
        if c["ministerio"] not in ids_min:
            rel.erro(f"{onde}: ministério '{c['ministerio']}' não existe")
        if unidades is not None and c.get("cod_siorg") and c["cod_siorg"] not in unidades:
            rel.erro(f"{onde}: cod_siorg {c['cod_siorg']} não existe no SIORG")
        if uos is not None and c["cod_uo"] not in uos:
            rel.aviso(f"{onde}: UO não aparece no orçamento coletado")
    if uos is not None:
        mapeadas = {c["cod_uo"] for c in curadoria.correspondencias(pasta)}
        faltam = sorted(uos - mapeadas)
        if faltam:
            rel.aviso(f"{len(faltam)} UOs do orçamento sem correspondência (rode `python -m etl correspondencias`): "
                      + ", ".join(faltam[:10]) + ("…" if len(faltam) > 10 else ""))
    revisar = [c["cod_uo"] for c in curadoria.correspondencias(pasta) if not c.get("cod_siorg") and c.get("metodo") == "automatico_nome"]
    if revisar:
        rel.aviso(f"{len(revisar)} UOs sem unidade SIORG correspondente pelo nome (revisar à mão): "
                  + ", ".join(revisar[:10]) + ("…" if len(revisar) > 10 else ""))

    for p in curadoria.pessoas(pasta):
        fil = p.get("filiacoes") or []
        for f in fil:
            if not f.get("fonte"):
                rel.erro(f"pessoa {p['nome']}: filiação sem fonte")
            _checar_vigencia(rel, f"pessoa {p['nome']} filiação {f.get('partido')}", f.get("valido_de"), f.get("valido_ate"))
        for i, a in enumerate(fil):
            for b in fil[i + 1:]:
                if _sobrepoe(a.get("valido_de"), a.get("valido_ate"), b.get("valido_de"), b.get("valido_ate")):
                    rel.erro(f"pessoa {p['nome']}: filiações com vigências sobrepostas")

    por_posto = defaultdict(list)
    for o in curadoria.ocupacoes(pasta):
        onde = f"ocupação manual {o.get('nome')} ({o.get('cargo')})"
        if not o.get("fonte"):
            rel.erro(f"{onde}: sem fonte")
        if unidades is not None and o.get("unidade") not in unidades:
            rel.erro(f"{onde}: unidade {o.get('unidade')} não existe no SIORG")
        _checar_vigencia(rel, onde, o.get("valido_de"), o.get("valido_ate"))
        if o.get("papel", "titular") == "titular":
            por_posto[o.get("unidade")].append(o)
    for unidade, lista in por_posto.items():
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                if _sobrepoe(a.get("valido_de"), a.get("valido_ate"), b.get("valido_de"), b.get("valido_ate")):
                    rel.erro(f"unidade {unidade}: titulares com períodos sobrepostos ({a.get('nome')} × {b.get('nome')})")

    for p in curadoria.politicas(pasta):
        if p["ministerio"] not in ids_min:
            rel.erro(f"política {p['id']}: ministério '{p['ministerio']}' não existe")
        if p.get("norma") and p["norma"] not in normas:
            rel.erro(f"política {p['id']}: norma '{p['norma']}' não existe")
        for u in p.get("unidades") or []:
            if unidades is not None and u not in unidades:
                rel.erro(f"política {p['id']}: unidade {u} não existe no SIORG")
        for v in p.get("vinculos") or []:
            if not v.get("fonte") or not v.get("justificativa"):
                rel.erro(f"política {p['id']}: vínculo sem fonte ou justificativa")
            ex = str(v.get("exercicio"))
            if acoes is not None and v.get("acao") and (ex, v["acao"]) not in acoes:
                rel.erro(f"política {p['id']}: ação {v['acao']} não existe no orçamento de {ex}")
            if programas is not None and v.get("programa") and (ex, v["programa"]) not in programas:
                rel.erro(f"política {p['id']}: programa {v['programa']} não existe no orçamento de {ex}")
        for pend in p.get("pendentes") or []:
            rel.aviso(f"política {p['id']}: vínculo pendente – {pend.get('motivo')}")


def validar_unidades(rel: Relatorio, linhas: list[dict]) -> None:
    vigentes = {}
    for u in linhas:
        _checar_vigencia(rel, f"unidade {u['cod_siorg']}", u.get("valido_de"), u.get("valido_ate"))
        if not u.get("valido_ate"):
            if u["cod_siorg"] in vigentes:
                rel.erro(f"unidade {u['cod_siorg']}: mais de uma versão vigente")
            vigentes[u["cod_siorg"]] = u
    for cod, u in vigentes.items():
        if u["cod_pai"] and u["cod_pai"] not in vigentes:
            rel.erro(f"unidade {cod}: pai {u['cod_pai']} inexistente")
        if u["profundidade"] != "0" and not u["bloco"]:
            rel.erro(f"unidade {cod}: sem bloco")
        if u["bloco"] == "outro":
            rel.aviso(f"unidade {cod} ({u['sigla']}): categoria {u['categoria']} sem bloco mapeado")
        # Ciclo: subir pelos pais não pode voltar à própria unidade.
        vistos, atual = set(), u
        while atual and atual["cod_pai"]:
            if atual["cod_siorg"] in vistos:
                rel.erro(f"unidade {cod}: ciclo na hierarquia")
                break
            vistos.add(atual["cod_siorg"])
            atual = vigentes.get(atual["cod_pai"])


def validar_orcamento(rel: Relatorio, linhas: list[dict], pasta=None, mensal: list[dict] | None = None) -> None:
    if not linhas:
        rel.aviso("orçamento ainda não coletado")
        return
    orgao_de = {m["id"]: m.get("orgao_orcamentario") for m in curadoria.no_escopo(pasta)}
    totais = defaultdict(lambda: defaultdict(float))
    for r in linhas:
        k = (r["cod_orgao_superior"], r["exercicio"])
        for c in ("dotacao_inicial", "dotacao_atual", "empenhado", "liquidado", "pago", "empenhado_orcdesp"):
            totais[k][c] += float(r[c])
    # O arquivo anual costuma ser gerado alguns dias antes do mensal mais recente, então pode não
    # conter os lançamentos do último mês: aceita o anual entre "até o mês anterior" e "até o último mês".
    uo_orgao = {r["cod_uo"]: r["cod_orgao_superior"] for r in linhas}
    ultimo_mes, emp_ultimo = {}, defaultdict(float)
    mensal = mensal if mensal is not None else ler_csv(NORMALIZADO / "orcamento_mensal.csv")
    for r in mensal:
        k = (uo_orgao.get(r["cod_uo"]), r["exercicio"])
        ultimo_mes[k] = max(ultimo_mes.get(k, 0), int(r["mes"]))
    for r in mensal:
        k = (uo_orgao.get(r["cod_uo"]), r["exercicio"])
        if int(r["mes"]) == ultimo_mes[k]:
            emp_ultimo[k] += float(r["empenhado"])
    for (orgao, ex), t in totais.items():
        if t["liquidado"] > t["empenhado"] * 1.001 or t["pago"] > t["liquidado"] * 1.001:
            rel.erro(f"orçamento {orgao}/{ex}: pago > liquidado ou liquidado > empenhado")
        anual, ate_ultimo = t["empenhado_orcdesp"], t["empenhado"]
        ate_anterior = ate_ultimo - emp_ultimo[(orgao, ex)]
        if anual and not (min(ate_anterior, ate_ultimo) * 0.98 <= anual <= max(ate_anterior, ate_ultimo) * 1.02):
            rel.aviso(f"orçamento {orgao}/{ex}: empenhado do arquivo anual ({anual / 1e9:.2f} bi) fora da faixa da "
                      f"soma mensal ({ate_anterior / 1e9:.2f} a {ate_ultimo / 1e9:.2f} bi)")
    for ref in curadoria.totais_referencia(pasta):
        k = (orgao_de.get(ref["ministerio"]), str(ref["exercicio"]))
        if k not in totais:
            continue
        valor = totais[k][ref["campo"]]
        desvio = abs(valor - ref["valor"]) / ref["valor"]
        if desvio > ref["tolerancia"]:
            rel.erro(f"orçamento {ref['ministerio']}/{ref['exercicio']}: {ref['campo']} = {valor / 1e9:.2f} bi, "
                     f"referência {ref['valor'] / 1e9:.2f} bi ({ref['fonte']})")


def validar_ocupacoes(rel: Relatorio, linhas: list[dict]) -> None:
    atuais = defaultdict(list)
    for o in linhas:
        if o["funcao"] == "MEST" and not o["fim_aprox"]:
            atuais[o["ministerio_id"]].append(o["nome"])
    for mid, nomes in atuais.items():
        if len(nomes) > 1:
            rel.aviso(f"{mid}: {len(nomes)} pessoas como Ministro(a) de Estado no último mês do SIAPE ({', '.join(nomes)}); "
                      "o site mostra a de posse mais recente")
    sem = [o for o in linhas if not o["inicio"] and int(o["nivel"]) >= 17]
    if sem:
        rel.aviso(f"{len(sem)} ocupações de nível 1.17+ sem data de ingresso no SIAPE")


def validar_idade(rel: Relatorio) -> None:
    for fid, f in fontes().items():
        for prefixo, limite in IDADE_MAXIMA.items():
            if fid.startswith(prefixo) and f["data_referencia"] and fid.endswith(str(date.today().year)):
                idade = (date.today() - date.fromisoformat(f["data_referencia"])).days
                if idade > limite:
                    rel.aviso(f"fonte {fid}: dados de {f['data_referencia']} ({idade} dias, limite {limite})")
    dou = fontes().get("dou")
    if dou and dou["data_referencia"] and (date.today() - date.fromisoformat(dou["data_referencia"])).days > 3:
        rel.aviso(f"fonte dou: Diário Oficial lido só até {dou['data_referencia']} (a coleta diária parou?)")


def validar_tudo() -> Relatorio:
    rel = Relatorio()
    un = ler_csv(NORMALIZADO / "unidade.csv")
    orc = ler_csv(NORMALIZADO / "orcamento.csv")
    validar_unidades(rel, un)
    validar_orcamento(rel, orc)
    validar_curadoria(
        rel,
        unidades={u["cod_siorg"] for u in un if not u["valido_ate"]} or None,
        acoes={(a["exercicio"], a["cod_acao"]) for a in ler_csv(NORMALIZADO / "acao.csv")} or None,
        programas={(p["exercicio"], p["cod_programa"]) for p in ler_csv(NORMALIZADO / "programa.csv")} or None,
        uos={u["cod_uo"] for u in ler_csv(NORMALIZADO / "uo.csv")} or None,
    )
    validar_ocupacoes(rel, ler_csv(NORMALIZADO / "ocupacao.csv"))
    validar_idade(rel)
    return rel
