"""Partido dos dirigentes — candidaturas registradas no TSE (dados abertos, sem chave).

Não existe base pública de filiação partidária com CPF. O que existe, com CPF, são as candidaturas:
o TSE publica o partido pelo qual cada pessoa concorreu. Cruzamos cada dirigente (nome + os 6 dígitos
visíveis do CPF no SIAPE) com as candidaturas de 2018 a 2026.

O painel mostra isso como "partido na candidatura mais recente (TSE, ano)". Quem nunca foi candidato
fica "sem candidatura registrada" — o que NÃO quer dizer "sem partido".
"""
from __future__ import annotations

import csv
import io
import zipfile

from .comum import BRUTO, NORMALIZADO, baixar, gravar_csv, hoje, ler_csv, registrar_fonte, sha256_obj
from .servidores import chave

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand"
PASTA = BRUTO / "tse"
ANOS = [2018, 2020, 2022, 2024, 2026]
CAMPOS = ["pessoa_id", "ano", "partido", "nome_partido", "cargo", "uf", "municipio", "situacao_candidatura", "resultado"]


def coletar(anos=ANOS) -> None:
    for ano in anos:
        destino = PASTA / f"consulta_cand_{ano}.zip"
        # Eleições passadas não mudam muito; a do ano corrente é atualizada pelo TSE.
        if destino.exists() and ano < max(anos):
            continue
        baixar(f"{BASE}/consulta_cand_{ano}.zip", destino, timeout=900)


def candidaturas(caminho_zip, alvo: dict[tuple, str]):
    """Linhas do arquivo do TSE cujo (6 dígitos centrais do CPF, nome) está em `alvo`."""
    with zipfile.ZipFile(caminho_zip) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        # Se houver o arquivo nacional, ele já contém todas as UFs.
        brasil = [n for n in nomes if "BRASIL" in n.upper()]
        for nome in brasil or nomes:
            with z.open(nome) as f:
                for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";"):
                    cpf = "".join(c for c in r.get("NR_CPF_CANDIDATO", "") if c.isdigit()).zfill(11)
                    pid = alvo.get((cpf[3:9], chave(r["NM_CANDIDATO"])))
                    if pid:
                        yield pid, r


def normalizar() -> bool:
    from .servidores import ARQ_CPF6
    pessoas = ler_csv(ARQ_CPF6)
    alvo = {(p["cpf6"], chave(p["nome"])): p["pessoa_id"] for p in pessoas if len(p["cpf6"]) == 6}
    linhas, vistos = [], set()
    for ano in ANOS:
        arq = PASTA / f"consulta_cand_{ano}.zip"
        if not arq.exists():
            continue
        for pid, r in candidaturas(arq, alvo):
            k = (pid, ano, r["SG_PARTIDO"], r["DS_CARGO"])
            if k in vistos:   # 1º e 2º turno repetem a candidatura
                continue
            vistos.add(k)
            linhas.append({
                "pessoa_id": pid, "ano": ano, "partido": r["SG_PARTIDO"], "nome_partido": r["NM_PARTIDO"],
                "cargo": r["DS_CARGO"].title(), "uf": r["SG_UF"], "municipio": r["NM_UE"].title() if r["TP_ABRANGENCIA"] == "MUNICIPAL" else "",
                "situacao_candidatura": r["DS_SITUACAO_CANDIDATURA"], "resultado": r["DS_SIT_TOT_TURNO"],
            })
    gravar_csv(NORMALIZADO / "candidatura.csv", linhas, CAMPOS, ["pessoa_id", "ano", "cargo"])
    return registrar_fonte("tse", "TSE – Candidaturas (dados abertos), 2018 a 2026",
                           "https://dadosabertos.tse.jus.br/dataset/?q=candidatos",
                           sha256_obj(sorted(tuple(map(str, l.values())) for l in linhas)), hoje())
