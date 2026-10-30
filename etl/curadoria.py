"""Leitura dos arquivos de curadoria manual (data/curadoria/*.yaml)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .comum import CURADORIA


def _carregar(nome: str, chave: str, pasta: Path | None = None) -> list[dict]:
    caminho = (pasta or CURADORIA) / nome
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    return [_datas_para_str(x) for x in dados.get(chave) or []]


def _datas_para_str(obj):
    """O YAML converte 2023-01-01 em date; o resto do ETL trabalha com strings ISO."""
    if isinstance(obj, dict):
        return {k: _datas_para_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_datas_para_str(v) for v in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def ministerios(pasta=None):
    return _carregar("ministerios.yaml", "ministerios", pasta)


def correspondencias(pasta=None):
    return _carregar("correspondencia_siorg_orcamento.yaml", "correspondencias", pasta)


def normas(pasta=None):
    return _carregar("normas.yaml", "normas", pasta)


def eventos(pasta=None):
    return _carregar("eventos_institucionais.yaml", "eventos", pasta)


def ocupacoes(pasta=None):
    return _carregar("ocupacoes.yaml", "ocupacoes", pasta)


def pessoas(pasta=None):
    return _carregar("pessoas.yaml", "pessoas", pasta)


def politicas(pasta=None):
    return _carregar("politicas_publicas.yaml", "politicas", pasta)


def totais_referencia(pasta=None):
    return _carregar("totais_referencia.yaml", "totais", pasta)


def versao_vigente(ministerio: dict) -> dict | None:
    vigentes = [v for v in ministerio["versoes"] if not v.get("valido_ate")]
    return vigentes[-1] if vigentes else None


def no_escopo(pasta=None) -> list[dict]:
    """Ministérios marcados `no_painel`, com a versão vigente achatada no topo do dict."""
    saida = []
    for m in ministerios(pasta):
        v = versao_vigente(m)
        if m.get("no_painel") and v:
            saida.append({"id": m["id"], "categoria": m.get("categoria", "ministerio"), **v})
    return saida
