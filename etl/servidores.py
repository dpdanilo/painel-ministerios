"""Ocupantes de cargos de direção — Portal da Transparência, "Servidores – SIAPE" (Cadastro), mensal.

Cada arquivo mensal (~80 MB) lista quem ocupa cada função comissionada (CCE/FCE, com o nível e a
unidade de exercício) e os cargos de Natureza Especial (Ministro de Estado e outros), com a data de
ingresso na função. Guardamos só as linhas de direção de cada mês (`dirigentes_AAAAMM.csv`) e, juntando
os meses, montamos as ocupações com vigência:

- início = DATA_INGRESSO_CARGOFUNCAO (dado oficial);
- fim    = aproximado: 1º mês em que a pessoa não aparece mais naquela função/unidade (`fim_aprox`).

O CPF vem mascarado (***.123.456-**). Só os 6 dígitos visíveis são usados, para cruzar com o TSE; eles
nunca são publicados — a pessoa é identificada por um hash.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import curadoria
from .comum import BRUTO, NORMALIZADO, baixar, gravar_csv, ler_csv, registrar_fonte, sha256_obj

BASE = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/servidores"
PASTA = BRUTO / "siape"
INICIO_SERIE = (2023, 1)
NIVEL_MINIMO = 13   # CCE/FCE 1.13 (Coordenador-Geral) para cima

CAMPOS_BRUTO = ["nome", "cpf6", "cargo", "sigla", "nivel", "atividade", "cod_uorg", "uorg", "cod_org", "org",
                "inicio", "situacao"]
CAMPOS_OCUPACAO = ["pessoa_id", "nome", "ministerio_id", "funcao", "nivel", "cargo", "cod_uorg", "uorg",
                   "cod_siorg", "inicio", "primeiro_mes", "ultimo_mes", "fim_aprox"]
CAMPOS_PESSOA = ["pessoa_id", "nome"]
# Os 6 dígitos de CPF ficam só no cache local (data/bruto, fora do git), para o cruzamento com o TSE.
ARQ_CPF6 = PASTA / "pessoas_cpf6.csv"


def chave(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s).split())


def pessoa_id(nome: str, cpf6: str) -> str:
    return hashlib.sha1(f"{chave(nome)}|{cpf6}".encode()).hexdigest()[:12]


def meses_desde(inicio=INICIO_SERIE, ate: date | None = None):
    ate = ate or date.today()
    a, m = inicio
    while (a, m) <= (ate.year, ate.month):
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def _data_iso(d: str) -> str:
    """'28/11/2024' → '2024-11-28'."""
    if not d or d.count("/") != 2:
        return ""
    dd, mm, aa = d.split("/")
    return f"{aa}-{mm}-{dd}"


def eh_dirigente(r: dict) -> bool:
    if "MINISTRO DE ESTADO" in r["DESCRICAO_CARGO"].upper() or r["SITUACAO_VINCULO"] == "NATUREZA ESPECIAL":
        return True
    sigla, nivel = r["SIGLA_FUNCAO"], r["NIVEL_FUNCAO"]
    return sigla in ("CCX", "FEX") and nivel[:2] == "01" and nivel[2:].isdigit() and int(nivel[2:]) >= NIVEL_MINIMO


def filtrar_zip(caminho_zip: Path) -> list[dict]:
    saida = []
    with zipfile.ZipFile(caminho_zip) as z:
        nome = next(n for n in z.namelist() if n.endswith("_Cadastro.csv"))
        with z.open(nome) as f:
            for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";"):
                if not eh_dirigente(r):
                    continue
                cpf6 = re.sub(r"\D", "", r["CPF"])[:6]
                saida.append({
                    "nome": r["NOME"].strip(), "cpf6": cpf6, "cargo": r["DESCRICAO_CARGO"].strip(),
                    "sigla": r["SIGLA_FUNCAO"], "nivel": r["NIVEL_FUNCAO"], "atividade": r["ATIVIDADE"].strip(),
                    "cod_uorg": r["COD_UORG_EXERCICIO"], "uorg": r["UORG_EXERCICIO"].strip(),
                    "cod_org": r["COD_ORG_EXERCICIO"], "org": r["ORG_EXERCICIO"].strip(),
                    "inicio": _data_iso(r["DATA_INGRESSO_CARGOFUNCAO"]), "situacao": r["SITUACAO_VINCULO"],
                })
    return saida


def coletar(desde=INICIO_SERIE) -> list[str]:
    """Baixa os meses que faltam (o Portal publica com ~2 meses de atraso). Devolve os meses novos."""
    PASTA.mkdir(parents=True, exist_ok=True)
    novos = []
    for a, m in meses_desde(desde):
        ref = f"{a}{m:02d}"
        destino = PASTA / f"dirigentes_{ref}.csv"
        if destino.exists():
            continue
        zipf = PASTA / f"{ref}.zip"
        try:
            baixar(f"{BASE}/{ref}_Servidores_SIAPE.zip", zipf, tentativas=2, timeout=900)
        except RuntimeError:
            continue   # mês ainda não publicado (403/404)
        linhas = filtrar_zip(zipf)
        gravar_csv(destino, linhas, CAMPOS_BRUTO)
        zipf.unlink()
        novos.append(ref)
        print(f"[siape] {ref}: {len(linhas)} dirigentes")
    return novos


# ------------------------------------------------------------------ normalização

def funcao_de(r: dict) -> tuple[str, int]:
    """('CCE 1.17', 17) · ('FCE 1.15', 15) · ('MEST', 99) · ('NE', 98)."""
    if "MINISTRO DE ESTADO" in r["cargo"].upper():
        return "MEST", 99
    if r["sigla"] in ("CCX", "FEX"):
        n = int(r["nivel"][2:])
        return f"{'CCE' if r['sigla'] == 'CCX' else 'FCE'} 1.{n:02d}", n
    return "NE", 98


def titulo(s: str) -> str:
    """'SECRETARIO(A) EXECUTIVO(A)' → 'Secretário(a) Executivo(a)' (sem inventar acentos: mantém a grafia)."""
    pequenas = {"DE", "DA", "DO", "DAS", "DOS", "E"}
    return " ".join(p.lower() if p in pequenas and i else p.capitalize() for i, p in enumerate(s.split()))


def mapa_orgaos(linhas: list[dict]) -> dict[str, str]:
    """cod_org SIAPE → ministerio_id. Primeiro pela curadoria (orgaos_siape.yaml), depois pelo nome do órgão."""
    manual = {o["cod_org"]: o["ministerio"] for o in curadoria._carregar("orgaos_siape.yaml", "orgaos")}
    nomes = {chave(m["nome"]): m["id"] for m in curadoria.no_escopo()}
    saida = dict(manual)
    for r in linhas:
        if r["cod_org"] not in saida and chave(r["org"]) in nomes:
            saida[r["cod_org"]] = nomes[chave(r["org"])]
    return saida


PRESIDENCIA = ("cc", "sg", "sri", "secom", "gsi")
DICAS_PRESIDENCIA = [("/CC", "cc"), ("CASA CIVIL", "cc"), ("/SG", "sg"), ("SECRETARIA GERAL", "sg"),
                     ("/SRI", "sri"), ("RELACOES INSTITUCIONAIS", "sri"), ("/GSI", "gsi"),
                     ("SEGURANCA INSTITUCIONAL", "gsi"), ("/SECOM", "secom"), ("COMUNICACAO SOCIAL", "secom")]


def resolvedor_presidencia():
    """Atribui uma UORG do código único da Presidência a um dos 5 órgãos: primeiro por sufixo/nome
    explícito (".../CC", "Casa Civil"…), depois pelo nome igual ao de uma unidade de um só desses órgãos no SIORG."""
    unidades = [u for u in ler_csv(NORMALIZADO / "unidade.csv") if not u["valido_ate"] and u["ministerio_id"] in PRESIDENCIA]
    por_nome = defaultdict(set)
    for u in unidades:
        por_nome[chave(u["nome"])].add(u["ministerio_id"])

    def resolver(uorg: str) -> str | None:
        bruto = (uorg or "").upper()
        k = chave(uorg)
        for dica, mid in DICAS_PRESIDENCIA:
            if dica in bruto or dica.replace("/", "") == k or (not dica.startswith("/") and dica in k):
                return mid
        donos = por_nome.get(k, set())
        return next(iter(donos)) if len(donos) == 1 else None
    return resolver


LIGACOES = {"DA", "DE", "DO", "DAS", "DOS", "E", "A", "O", "EM", "PARA", "AO"}


def bate_abreviado(siape: str, siorg: str) -> bool:
    """O SIAPE abrevia e pula palavras: 'MIN DO EMPRE MICRO EMP DE PEQUENO PORTE' bate com 'MINISTERIO DO
    EMPREENDEDORISMO DA MICROEMPRESA E DA EMPRESA DE PEQUENO PORTE'. Regra: cada palavra do SIAPE é o começo de
    uma palavra do SIORG, na mesma ordem; as palavras do SIORG puladas só podem ser preposições/conjunções.
    Se o nome do SIAPE foi cortado no limite de 40 caracteres, o resto do nome do SIORG pode sobrar."""
    a, b = siape.split(), siorg.split()
    cortado = len(siape) >= 38
    j = 0
    for x in a:
        while j < len(b) and not b[j].startswith(x):
            if b[j] not in LIGACOES:
                return False
            j += 1
        if j == len(b):
            return False
        j += 1
    return cortado or all(w in LIGACOES for w in b[j:])


def mapa_uorg_siorg(ocupacoes: list[dict]) -> dict[tuple, str]:
    """(ministerio_id, nome da UORG) → código SIORG, pelo nome da unidade (o SIAPE corta em 40 caracteres)."""
    unidades = [u for u in ler_csv(NORMALIZADO / "unidade.csv") if not u["valido_ate"]]
    por_min = defaultdict(list)
    siglas = defaultdict(lambda: defaultdict(list))
    for u in unidades:
        por_min[u["ministerio_id"]].append((chave(u["nome"]), u["cod_siorg"], int(u["profundidade"])))
        siglas[u["ministerio_id"]][chave(u["sigla"])].append(u["cod_siorg"])
    saida = {}
    for o in ocupacoes:
        k = (o["ministerio_id"], o["uorg"])
        if k in saida:
            continue
        alvo = chave(o["uorg"])
        cands = [(d, c) for n, c, d in por_min[o["ministerio_id"]] if n == alvo]
        if not cands:
            cands = [(d, c) for n, c, d in por_min[o["ministerio_id"]] if bate_abreviado(alvo, n)]
        if not cands and "/" in o["uorg"]:
            # Unidade escrita como caminho de siglas ("MJSP/SENAPPEN/DICAP"): a última é a sigla no SIORG.
            cands = [(0, c) for c in siglas[o["ministerio_id"]].get(chave(o["uorg"].split("/")[-1]), [])]
        # Nome repetido (ex.: "Gabinete") é ambíguo: só aceita se houver uma única unidade.
        saida[k] = cands[0][1] if len(cands) == 1 else ""
        if o["funcao"] == "MEST":
            raiz = next((c for n, c, d in por_min[o["ministerio_id"]] if d == 0), "")
            saida[k] = raiz
    return saida


TOLERANCIA_FALHA = 1     # meses de ausência que não encerram um mandato (falhas pontuais do cadastro)


def mandatos(presenca: dict[tuple, dict[int, dict]], meses: list[str], pessoas: dict) -> list[dict]:
    """Agrupa a presença mensal em mandatos.

    - Ausência de até TOLERANCIA_FALHA mês não encerra o mandato.
    - Registro isolado de 1 mês com ingresso mais de 6 meses antes é resíduo do cadastro (ex-ocupante que
      reaparece por um mês) e é descartado.
    """
    saida = []
    for k, por_i in presenca.items():
        idx = sorted(por_i)
        grupos, atual = [], [idx[0]]
        for i in idx[1:]:
            if i - atual[-1] <= TOLERANCIA_FALHA + 1:
                atual.append(i)
            else:
                grupos.append(atual); atual = [i]
        grupos.append(atual)
        for g in grupos:
            r0, r1 = por_i[g[0]], por_i[g[-1]]
            primeiro, ultimo = meses[g[0]], meses[g[-1]]
            inicio = r0["inicio"]
            if len(g) == 1 and g[0] > 0 and inicio and inicio[:7].replace("-", "") < _mes_menos(primeiro, 6):
                continue
            fim = "" if g[-1] == len(meses) - 1 else f"{meses[g[-1] + 1][:4]}-{meses[g[-1] + 1][4:]}"
            atividade = r1["atividade"] if r1["atividade"] and not r1["atividade"].startswith("Sem inform") else r1["cargo"]
            saida.append({
                "pessoa_id": k[0], "nome": pessoas[k[0]]["nome"], "ministerio_id": r1["_mid"], "funcao": r1["_funcao"],
                "nivel": r1["_nivel"], "cargo": titulo(atividade), "cod_uorg": r1["cod_uorg"], "uorg": r1["uorg"],
                "inicio": inicio, "primeiro_mes": primeiro, "ultimo_mes": ultimo, "fim_aprox": fim,
            })
    return encerrar_antecessores(saida)


def encerrar_antecessores(ocupacoes: list[dict]) -> list[dict]:
    """Um ministério tem um(a) Ministro(a) por vez: a posse de um sucessor encerra o mandato do anterior
    (o cadastro às vezes mantém o antecessor por meses depois da troca)."""
    por_min = defaultdict(list)
    for o in ocupacoes:
        if o["funcao"] == "MEST":
            por_min[o["ministerio_id"]].append(o)
    for lista in por_min.values():
        lista.sort(key=lambda o: (o["inicio"] or "", o["primeiro_mes"]))
        for a, b in zip(lista, lista[1:]):
            posse = (b["inicio"] or f"{b['primeiro_mes'][:4]}-{b['primeiro_mes'][4:]}")[:7]
            if not a["fim_aprox"] or a["fim_aprox"] > posse:
                a["fim_aprox"] = posse
    return ocupacoes


def _mes_menos(aaaamm: str, n: int) -> str:
    a, m = int(aaaamm[:4]), int(aaaamm[4:])
    m -= n
    while m <= 0:
        a, m = a - 1, m + 12
    return f"{a}{m:02d}"


def normalizar() -> bool:
    arquivos = sorted(PASTA.glob("dirigentes_*.csv"))
    if not arquivos:
        return False
    meses = [a.stem.split("_")[1] for a in arquivos]
    por_mes = {m: ler_csv(a) for m, a in zip(meses, arquivos)}
    orgaos = mapa_orgaos([r for ls in por_mes.values() for r in ls])

    # Presença mês a mês por chave. Para Ministro(a) a chave ignora a unidade: o código da UORG do gabinete
    # muda em reorganizações (ex.: nov/2023) sem que a pessoa deixe o cargo.
    presenca: dict[tuple, dict[int, dict]] = defaultdict(dict)
    pessoas = {}
    presidencia = resolvedor_presidencia()
    # Se a própria unidade tem o nome de um ministério, ela prevalece sobre o código do órgão:
    # ex.: em 2023 a Cultura recriada ainda usava o código do Turismo no SIAPE.
    nomes_ministerios = {chave(m["nome"]): m["id"] for m in curadoria.no_escopo()}

    def ministerio_pelo_nome(uorg: str) -> str | None:
        k = chave(uorg)
        if k in nomes_ministerios:
            return nomes_ministerios[k]
        if k.startswith("MIN"):
            achados = {mid for n, mid in nomes_ministerios.items() if bate_abreviado(k, n)}
            return achados.pop() if len(achados) == 1 else None
        return None
    for i, mes in enumerate(meses):
        for r in por_mes[mes]:
            mid = ministerio_pelo_nome(r["uorg"]) or orgaos.get(r["cod_org"])
            if mid == "presidencia":
                mid = presidencia(r["uorg"])
            if not mid:
                continue
            funcao, nivel = funcao_de(r)
            pid = pessoa_id(r["nome"], r["cpf6"])
            pessoas[pid] = {"pessoa_id": pid, "nome": titulo(r["nome"]), "cpf6": r["cpf6"]}
            k = (pid, funcao, mid) if funcao == "MEST" else (pid, funcao, r["cod_uorg"])
            presenca[k].setdefault(i, {**r, "_mid": mid, "_funcao": funcao, "_nivel": nivel})

    ocupacoes = mandatos(presenca, meses, pessoas)
    siorg = mapa_uorg_siorg(ocupacoes)
    for o in ocupacoes:
        o["cod_siorg"] = siorg.get((o["ministerio_id"], o["uorg"]), "")

    ultimo = meses[-1]
    gravar_csv(NORMALIZADO / "ocupacao.csv", ocupacoes, CAMPOS_OCUPACAO,
               ["ministerio_id", "nivel", "pessoa_id", "inicio", "cod_uorg"])
    gravar_csv(NORMALIZADO / "pessoa.csv", list(pessoas.values()), CAMPOS_PESSOA, ["pessoa_id"])
    gravar_csv(ARQ_CPF6, list(pessoas.values()), CAMPOS_PESSOA + ["cpf6"], ["pessoa_id"])
    sem_orgao = sorted({(r["cod_org"], r["org"]) for r in por_mes[ultimo] if r["cod_org"] not in orgaos})
    if sem_orgao:
        print(f"[siape] {len(sem_orgao)} órgãos do SIAPE fora do painel (ex.: {sem_orgao[:3]})")
    conteudo = sorted(tuple(o[c] for c in CAMPOS_OCUPACAO) for o in ocupacoes)
    return registrar_fonte("siape", "Portal da Transparência – Servidores (SIAPE), cadastro mensal (CGU)",
                           "https://portaldatransparencia.gov.br/download-de-dados/servidores",
                           sha256_obj(conteudo), f"{ultimo[:4]}-{ultimo[4:]}-01")
