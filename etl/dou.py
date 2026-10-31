"""Diário Oficial da União (Imprensa Nacional): nomeações e exonerações do alto escalão e normas de estrutura.

Serve para cobrir o atraso de ~2 meses do SIAPE: o site mostra o que saiu no DOU depois do último mês do SIAPE.

- Uma página por dia e seção (`in.gov.br/leiturajornal?data=DD-MM-AAAA&secao=do1|do2|do1e|do2e`), sem chave.
  Ela traz, em JSON, todos os atos do dia com título, órgão e o começo do texto.
- Só se abre o texto completo dos atos candidatos: na seção 2, os que falam em nomear/exonerar (ou designar/dispensar,
  para funções FCE) e saem da
  Presidência da República, de "Atos do Poder Executivo" (decretos do Presidente) ou do gabinete/secretaria-executiva
  de um ministério. Universidades, institutos e autarquias ficam de fora.
- Do texto se extrai pessoa, cargo e código (CCE/FCE 1.xx). Ficam os cargos a partir de 1.15, Natureza Especial,
  Ministro(a) de Estado e os cargos providos por decreto do Presidente.
- Na seção 1, ficam os decretos de estrutura regimental e as normas que mudam a organização dos ministérios.
"""
from __future__ import annotations

import html
import json
import re
import urllib.request
from datetime import date, timedelta

from . import curadoria
from .comum import BRUTO, NORMALIZADO, USER_AGENT, fontes, gravar_csv, ler_csv, registrar_fonte, sha256_obj
from .servidores import chave

PASTA = BRUTO / "dou"
URL_DIA = "https://www.in.gov.br/leiturajornal?data={dia}&secao={secao}"
URL_ATO = "https://www.in.gov.br/web/dou/-/{url}"
SECOES = ("do1", "do2", "do1e", "do2e")
JANELA_MINIMA = 90       # dias: no mínimo, os últimos 90 dias (mesmo que o SIAPE esteja em dia)
REBAIXAR_DIAS = 3        # edições extras podem sair à tarde: os últimos dias são lidos de novo
NIVEL_MINIMO = 15        # CCE/FCE 1.15 (Diretor) para cima, como no site
# O portal da Imprensa Nacional recusa (403) o User-Agent padrão do projeto; este continua identificando o painel.
CABECALHOS = {"User-Agent": f"Mozilla/5.0 (compatible; {USER_AGENT.split(' ')[0]}; https://github.com/dpdanilo/painel-ministerios)",
              "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "pt-BR,pt;q=0.9"}

CAMPOS_ATO = ["id", "data", "edicao", "acao", "nome", "cargo", "codigo", "funcao", "nivel", "ministerio_id",
              "titulo", "url"]
CAMPOS_NORMA = ["id", "data", "edicao", "tipo", "titulo", "resumo", "ministerio_id", "url"]
ARQ_ATOS = NORMALIZADO / "dou_ato.csv"
ARQ_NORMAS = NORMALIZADO / "dou_norma.csv"
ARQ_NOVOS = PASTA / "novos.md"   # resumo para a issue de curadoria (lido pelo GitHub Actions)


# ---------------------------------------------------------------- coleta

def inicio_janela(hoje: date | None = None) -> date:
    """Primeiro dia do mês de referência do SIAPE, ou 90 dias atrás, o que vier antes."""
    hoje = hoje or date.today()
    ref = (fontes().get("siape", {}).get("data_referencia") or "")[:7]
    minimo = hoje - timedelta(days=JANELA_MINIMA)
    if ref:
        d = date(int(ref[:4]), int(ref[5:7]), 1)
        return min(d, minimo)
    return minimo


def _get(url: str, tentativas: int = 4, pausa: float = 0.5) -> str:
    import time
    erro = None
    for n in range(tentativas):
        time.sleep(pausa * 2 ** n)
        try:
            req = urllib.request.Request(url, headers=CABECALHOS)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001 — rede instável: tenta de novo
            erro = e
    raise RuntimeError(f"Falha ao ler {url}: {erro}")


def atos_do_dia(pagina: str) -> list[dict]:
    m = re.search(r'<script id="params" type="application/json">(.*?)</script>', pagina, re.S)
    if not m:
        raise RuntimeError("página do DOU sem o bloco de dados (o formato mudou?)")
    return json.loads(m.group(1)).get("jsonArray", [])


VERBO = re.compile(r"\b(nomear|exonerar|designar|dispensar)\b", re.I)
GABINETE = re.compile(r"^(Gabinete d[oa] Ministr[oa]|Secretaria[- ]Executiva)$", re.I)
ESTRUTURA = re.compile(r"Estrutura Regimental|organiza[çc][ãa]o b[áa]sica dos [óo]rg[ãa]os|Lei n[ºo°] ?14\.600|"
                       r"transforma[çc][ãa]o de cargos em comiss[ãa]o", re.I)


def candidato_pessoal(a: dict) -> bool:
    if not VERBO.search(a.get("content", "")):
        return False
    h = a.get("hierarchyList") or []
    if not h:
        return False
    if h[0] in ("Atos do Poder Executivo", "Presidência da República"):
        return len(h) <= 2
    return h[0].startswith("Ministério") and (len(h) == 1 or (len(h) == 2 and bool(GABINETE.match(h[1]))))


def norma_de_estrutura(a: dict) -> bool:
    # artType vem como "Decreto numerado", "Decreto", "Medida Provisória", "Lei"...; decreto de pessoal não é norma
    tipo = a.get("artType", "")
    return (bool(re.match(r"(Decreto(?! de Pessoal)|Medida Provis|Lei\b)", tipo))
            and bool(ESTRUTURA.search(a.get("content", ""))))


def coletar(hoje: date | None = None) -> None:
    hoje = hoje or date.today()
    (PASTA / "dias").mkdir(parents=True, exist_ok=True)
    (PASTA / "textos").mkdir(parents=True, exist_ok=True)
    d = inicio_janela(hoje)
    while d <= hoje:
        arq = PASTA / "dias" / f"{d.isoformat()}.json"
        if not arq.exists() or d >= hoje - timedelta(days=REBAIXAR_DIAS):
            dia = {}
            for s in SECOES:
                atos = atos_do_dia(_get(URL_DIA.format(dia=d.strftime("%d-%m-%Y"), secao=s)))
                dia[s] = [a for a in atos if candidato_pessoal(a) or norma_de_estrutura(a)]
            arq.write_text(json.dumps(dia, ensure_ascii=False), encoding="utf-8")
        for s, atos in json.loads(arq.read_text(encoding="utf-8")).items():
            for a in atos:
                if not candidato_pessoal(a):
                    continue
                t = arq_texto(a)
                if not t.exists():
                    t.write_text(texto_do_ato(_get(URL_ATO.format(url=a["urlTitle"]))), encoding="utf-8")
        d += timedelta(days=1)


def arq_texto(a: dict):
    return PASTA / "textos" / f"{re.sub(r'[^0-9a-z.-]', '_', a['urlTitle'])[-150:]}.txt"


def texto_do_ato(pagina: str) -> str:
    """Parágrafos do ato, um por linha, com a classe do parágrafo: 'classe<TAB>texto'."""
    m = re.search(r'<div class="texto-dou">(.*?)</div>', pagina, re.S)
    if not m:
        raise RuntimeError("ato do DOU sem o bloco de texto (o formato mudou?)")
    linhas = []
    for cls, corpo in re.findall(r'<p class="([^"]*)"[^>]*>(.*?)</p>', m.group(1), re.S):
        t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", corpo)).split())
        if t:
            linhas.append(f"{cls.strip()}\t{t}")
    return "\n".join(linhas)


# ---------------------------------------------------------------- leitura dos atos

def resolvedor_ministerios():
    """Texto (cargo, cabeçalho ou órgão) → ministerio_id, pelo nome do órgão no texto."""
    contidos, exatos = [], {}
    for m in curadoria.no_escopo():
        k = chave(m["nome"])
        contidos.append((k, m["id"]))
        curto = k.replace(" DA PRESIDENCIA DA REPUBLICA", "")
        exatos[curto] = m["id"]
    contidos += [("CASA CIVIL", "cc"), ("ADVOGADO GERAL DA UNIAO", "agu"), ("GABINETE DE SEGURANCA INSTITUCIONAL", "gsi"),
                 ("SECRETARIA DE RELACOES INSTITUCIONAIS", "sri"), ("SECRETARIA DE COMUNICACAO SOCIAL DA PRESIDENCIA", "secom"),
                 ("SECRETARIA GERAL DA PRESIDENCIA", "sg")]

    def resolver(texto: str, exato: bool = False) -> str | None:
        k = chave(texto)
        k = re.sub(r"\bMINISTR[OA] DE ESTADO( CHEFE)?\b", "MINISTERIO", k)
        if exato:
            return exatos.get(k) or next((mid for n, mid in contidos if n == k), None)
        achados = []
        for n, mid in contidos:
            i = re.search(rf"\b{re.escape(n)}\b", k)
            if i:
                achados.append((i.start(), -len(n), mid))
        return min(achados)[2] if achados else None
    return resolver


NOME = r"(?P<nome>[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ'’.\- ]{3,}?)"
LIGACAO_CARGO = (r"(?:para exercer o|do|para o|para exercer a|da) (?:cargo|função|Cargo Comissionado Executivo|"
                 r"Função Comissionada Executiva)(?: em comissão)? de")
PADRAO = re.compile(
    r"\b(?P<verbo>NOMEAR|EXONERAR|DESIGNAR|DISPENSAR|Nomear|Exonerar|Designar|Dispensar)\b\s*(?:,?\s*a pedido,?)?(?:,?\s*a (?:partir|contar) de [^,]+,)?\s*"
    r"(?:(?:o|a) (?:servidora?|senhora?)\s+)?" + NOME + r"\s*,?\s*(?:(?:matrícula|CPF)[^,]+,\s*)?" + LIGACAO_CARGO +
    r"\s+(?P<resto>.+)")
CODIGO = re.compile(r",?\s*c[óo]digo\s+(?P<cod>(?:CCE|FCE|CCX|FEX)\s*-?\s*\d\.\d{2}|[A-Z]{2,4}[- ]?\d[\d.]*)")


def classificar(cargo: str, codigo: str, decreto: bool) -> tuple[str, int | None]:
    c = chave(cargo)
    if re.search(r"\bMINISTR[OA] DE ESTADO\b", c) and not re.search(r"\b(ASSESSOR|CHEFE DE GABINETE|SUBSTITUT)", c):
        return "Ministro(a) de Estado", 20
    if "NATUREZA ESPECIAL" in c or "NATUREZA ESPECIAL" in chave(codigo):
        return "Natureza Especial", 19
    # Secretário(a)-Executivo(a) de ministério é cargo de Natureza Especial (o decreto nem sempre diz)
    if decreto and not codigo and re.match(r"SECRETARI[OA] EXECUTIV[OA] D[AO]S? (MINISTERIO|CASA CIVIL|SECRETARIA|"
                                           r"CONTROLADORIA|ADVOCACIA|GABINETE)", c):
        return "Natureza Especial", 19
    m = re.match(r"(CCE|FCE|CCX|FEX)\s*-?\s*1\.(\d{2})", codigo or "")
    if m:
        return f"{m.group(1)} 1.{m.group(2)}", int(m.group(2))
    # Sem código, por decreto: só dirigentes (de agências, entidades, comandos). Reitor, adido, embaixador, membro
    # de conselho etc. são providos por decreto mas não são cargos da estrutura dos ministérios.
    if decreto and not codigo and re.match(r"(PRESIDENTE|DIRETOR|SECRETARI|SUPERINTENDENTE|COMANDANTE|PROCURADOR GERAL|"
                                           r"CORREGEDOR GERAL|OUVIDOR GERAL|SUBCHEFE|CHEFE DO ESTADO MAIOR)", c):
        return "Decreto do Presidente", 18
    if decreto and not codigo:
        return "", None
    return codigo or "", None


def ler_ato(a: dict, texto: str, resolver) -> list[dict]:
    """Pessoas nomeadas/exoneradas num ato (um ato pode ter várias portarias, como as da Casa Civil)."""
    paragrafos = [l.split("\t", 1) for l in texto.splitlines() if "\t" in l]
    h = a.get("hierarchyList") or []
    padrao_orgao = resolver("/".join(h[:2])) if h and h[0] != "Atos do Poder Executivo" else None
    decreto = a.get("artType") == "Decreto de Pessoal" or h[:1] == ["Atos do Poder Executivo"]
    contexto = None
    saida = []
    i = 0
    while i < len(paragrafos):
        cls, t = paragrafos[i]
        cab = cls in ("titulo", "subtitulo") or (t.isupper() and len(t) < 160 and not VERBO.search(t))
        if cab:
            contexto = resolver(t) or resolver(t, exato=True) or contexto
        else:
            seg = t
            # "Nº 250 - EXONERAR" num parágrafo e a pessoa no seguinte
            if re.fullmatch(r"(?:N[ºo°] ?[\d.]+\s*-\s*)?(NOMEAR|EXONERAR|DESIGNAR|DISPENSAR)\s*(?:,?\s*a pedido)?\s*[,:]?", t, re.I) and i + 1 < len(paragrafos):
                seg = f"{t} {paragrafos[i + 1][1]}"
                i += 1
            for m in PADRAO.finditer(seg):
                resto = m.group("resto")
                cod = CODIGO.search(resto)
                cargo = resto[:cod.start()] if cod else re.split(r",\s*ficando|\.\s|;|\.$", resto)[0]
                cargo = cargo.strip(" ,.")
                codigo = " ".join(cod.group("cod").replace("-", " ").split()) if cod else ""
                funcao, nivel = classificar(cargo, codigo, decreto)
                if nivel is None or nivel < NIVEL_MINIMO or "SUBSTITUT" in chave(cargo):
                    continue
                mid = resolver(cargo) or contexto or padrao_orgao
                if not mid:
                    continue
                nome = " ".join(m.group("nome").split()).strip(" ,.-")
                # designar/dispensar = funções FCE (servidores de carreira); valem como nomeação/exoneração
                acao = "nomeacao" if m.group("verbo").lower() in ("nomear", "designar") else "exoneracao"
                saida.append({
                    "id": f"{a['urlTitle'].rsplit('-', 1)[-1]}-{len(saida)}",
                    "data": _iso(a["pubDate"]), "edicao": a.get("pubName", ""), "acao": acao,
                    "nome": nome.title().replace(" Da ", " da ").replace(" De ", " de ").replace(" Do ", " do ")
                                .replace(" Dos ", " dos ").replace(" Das ", " das ").replace(" E ", " e "),
                    "cargo": cargo, "codigo": codigo, "funcao": funcao, "nivel": nivel, "ministerio_id": mid,
                    "titulo": a.get("title", ""), "url": URL_ATO.format(url=a["urlTitle"]),
                })
        i += 1
    return saida


def _iso(dd_mm_aaaa: str) -> str:
    d, m, a = dd_mm_aaaa.split("/")
    return f"{a}-{m}-{d}"


def ler_norma(a: dict, resolver) -> dict:
    resumo = a.get("content", "")
    t = a.get("title", "")
    resumo = resumo[len(t):].strip() if resumo.upper().startswith(t.upper()) else resumo
    # a ementa termina onde começa o preâmbulo ("O PRESIDENTE DA REPÚBLICA, no uso...")
    resumo = re.split(r"\s(?:O|A) (?:PRESIDENTE|PRESIDENTA|VICE-PRESIDENTE|MINISTR[OA])\b", resumo)[0].strip()
    return {"id": a["urlTitle"].rsplit("-", 1)[-1], "data": _iso(a["pubDate"]), "edicao": a.get("pubName", ""),
            "tipo": a.get("artType", ""), "titulo": t, "resumo": resumo[:400], "ministerio_id": resolver(resumo) or "",
            "url": URL_ATO.format(url=a["urlTitle"])}


# ---------------------------------------------------------------- normalização

def normalizar(hoje: date | None = None) -> bool:
    hoje = hoje or date.today()
    if not (PASTA / "dias").exists():
        return False
    resolver = resolvedor_ministerios()
    desde = inicio_janela(hoje).isoformat()
    atos, normas = {}, {}
    for arq in sorted((PASTA / "dias").glob("*.json")):
        if arq.stem < desde:
            continue
        for s, lista in json.loads(arq.read_text(encoding="utf-8")).items():
            for a in lista:
                if norma_de_estrutura(a):
                    n = ler_norma(a, resolver)
                    normas[n["id"]] = n
                if candidato_pessoal(a) and arq_texto(a).exists():
                    for r in ler_ato(a, arq_texto(a).read_text(encoding="utf-8"), resolver):
                        atos[r["id"]] = r
    anteriores = {r["id"] for r in ler_csv(ARQ_ATOS)} | {r["id"] for r in ler_csv(ARQ_NORMAS)}
    gravar_csv(ARQ_ATOS, list(atos.values()), CAMPOS_ATO, ["data", "ministerio_id", "id"])
    gravar_csv(ARQ_NORMAS, list(normas.values()), CAMPOS_NORMA, ["data", "id"])
    escrever_novos([a for a in atos.values() if a["id"] not in anteriores],
                   [n for n in normas.values() if n["id"] not in anteriores], hoje)
    # O dia lido entra no hash: "lido até" no site precisa ser verdadeiro, mesmo num dia sem atos novos.
    ultimo = max((a.stem for a in (PASTA / "dias").glob("*.json")), default="")
    return registrar_fonte("dou", "Imprensa Nacional – Diário Oficial da União, seções 1 e 2 (inclusive extras)",
                           "https://www.in.gov.br/leiturajornal",
                           sha256_obj([ultimo, [atos[k] for k in sorted(atos)], [normas[k] for k in sorted(normas)]]), ultimo)


def escrever_novos(atos: list[dict], normas: list[dict], hoje: date) -> None:
    """Resumo para a issue de curadoria: trocas de ministro, Natureza Especial e normas de estrutura dos últimos 7 dias.
    (Na primeira coleta, a janela inteira é "nova": só os últimos 7 dias viram issue.)"""
    corte = (hoje - timedelta(days=7)).isoformat()
    nomes = {m["id"]: m["nome"] for m in curadoria.no_escopo()}
    altos = [a for a in atos if a["nivel"] >= 19 and a["data"] >= corte]
    normas = [n for n in normas if n["data"] >= corte]
    ARQ_NOVOS.unlink(missing_ok=True)
    if not altos and not normas:
        return
    ls = ["Atos novos no Diário Oficial que podem pedir revisão da curadoria (`data/curadoria/`).", ""]
    if altos:
        ls += ["### Ministros e cargos de Natureza Especial", "",
               "Conferir partido (`pessoas.yaml`) e, se preciso, registrar a ocupação em `ocupacoes.yaml` até o SIAPE chegar.", ""]
        for a in sorted(altos, key=lambda x: (x["data"], x["ministerio_id"])):
            verbo = "Nomeação" if a["acao"] == "nomeacao" else "Exoneração"
            ls.append(f"- {a['data']} · **{verbo}** de {a['nome']} · {a['cargo']} ({nomes.get(a['ministerio_id'], a['ministerio_id'])}) · [DOU]({a['url']})")
        ls.append("")
    if normas:
        ls += ["### Normas de estrutura", "",
               "Conferir `normas.yaml` (decreto de estrutura vigente) e `eventos_institucionais.yaml` (se cria, funde ou extingue órgão).", ""]
        for n in sorted(normas, key=lambda x: x["data"]):
            ls.append(f"- {n['data']} · [{n['titulo']}]({n['url']}): {n['resumo'][:200]}")
    ARQ_NOVOS.write_text("\n".join(ls) + "\n", encoding="utf-8")
