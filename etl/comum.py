"""Utilitários compartilhados pelo ETL: caminhos, HTTP com retentativas, CSV e metadados de fonte."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"
BRUTO = DADOS / "bruto"            # cache local, fora do git
CURADORIA = DADOS / "curadoria"    # editado à mão
NORMALIZADO = DADOS / "normalizado"  # gerado pelo ETL, versionado no git
PUBLICADO = RAIZ / "site" / "public" / "data"  # o que vai para o GitHub Pages

USER_AGENT = "painel-ministerios/1.0 (+https://github.com/dpdanilo/painel-ministerios)"


def hoje() -> str:
    return date.today().isoformat()


def agora_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def baixar(url: str, destino: Path, tentativas: int = 4, timeout: int = 300, pausa: float = 1.0) -> Path:
    """Baixa `url` para `destino`, com retentativas e backoff exponencial.

    Grava primeiro num arquivo temporário para nunca deixar um download pela metade no cache.
    `pausa` é aplicada antes de cada requisição para respeitar os limites das APIs.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    ultimo_erro: Exception | None = None
    for n in range(tentativas):
        time.sleep(pausa if n == 0 else pausa * 2 ** n)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
                while bloco := resp.read(1 << 20):
                    f.write(bloco)
            os.replace(tmp, destino)
            return destino
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultimo_erro = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                break
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"Falha ao baixar {url}: {ultimo_erro}")


def ler_json(caminho: Path):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        while bloco := f.read(1 << 20):
            h.update(bloco)
    return h.hexdigest()


def sha256_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ler_csv(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def gravar_csv(caminho: Path, linhas: list[dict], campos: list[str], chave: list[str] | None = None) -> None:
    """Grava CSV ordenado por `chave`, para que diffs no git mostrem só mudanças reais."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if chave:
        linhas = sorted(linhas, key=lambda r: tuple(str(r.get(k) or "") for k in chave))
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in linhas:
            w.writerow({k: ("" if r.get(k) is None else r[k]) for k in campos})


# ---------------------------------------------------------------- fonte_metadado

ARQ_FONTES = NORMALIZADO / "fonte_metadado.csv"
CAMPOS_FONTES = ["fonte_id", "nome", "url", "data_referencia", "coletado_em", "hash"]


def registrar_fonte(fonte_id: str, nome: str, url: str, hash_conteudo: str, data_referencia: str = "") -> bool:
    """Atualiza o registro de uma fonte. Retorna True se o conteúdo mudou.

    `coletado_em` só avança quando o hash muda: assim uma coleta sem novidade não gera commit.
    """
    linhas = {r["fonte_id"]: r for r in ler_csv(ARQ_FONTES)}
    atual = linhas.get(fonte_id)
    mudou = atual is None or atual["hash"] != hash_conteudo
    if mudou:
        linhas[fonte_id] = {
            "fonte_id": fonte_id, "nome": nome, "url": url,
            "data_referencia": data_referencia, "coletado_em": hoje(), "hash": hash_conteudo,
        }
        gravar_csv(ARQ_FONTES, list(linhas.values()), CAMPOS_FONTES, ["fonte_id"])
    return mudou


def fontes() -> dict[str, dict]:
    return {r["fonte_id"]: r for r in ler_csv(ARQ_FONTES)}
