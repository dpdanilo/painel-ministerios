"""Linha de comando do ETL.

    python -m etl coletar siorg|orcamento [--exercicio 2026]
    python -m etl normalizar siorg|orcamento [--exercicio 2026]
    python -m etl atualizar siorg|orcamento|tudo     (coletar + normalizar)
    python -m etl validar [--estrito]
    python -m etl publicar [--exercicio 2026]
    python -m etl correspondencias [--exercicio 2026]   (sugere UO ↔ SIORG para UOs novas)

Código de saída: 0 ok · 1 erro de validação/coleta · 3 dados mudaram (só em `atualizar`, se pedido
com --sinalizar-mudanca, para o GitHub Actions decidir se faz commit e deploy).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from . import correspondencia, orcamento, publicar, siorg, validar


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="python -m etl")
    ap.add_argument("comando", choices=["coletar", "normalizar", "atualizar", "validar", "publicar", "correspondencias"])
    ap.add_argument("fonte", nargs="?", choices=["siorg", "orcamento", "tudo"], default="tudo")
    ap.add_argument("--exercicio", type=int, default=date.today().year)
    ap.add_argument("--estrito", action="store_true", help="avisos também falham a validação")
    ap.add_argument("--sinalizar-mudanca", action="store_true")
    a = ap.parse_args(argv)
    fontes = ["siorg", "orcamento"] if a.fonte == "tudo" else [a.fonte]

    if a.comando in ("coletar", "atualizar"):
        for f in fontes:
            print(f"[coletar] {f}")
            siorg.coletar() if f == "siorg" else orcamento.coletar(a.exercicio)
    mudou = False
    if a.comando in ("normalizar", "atualizar"):
        for f in fontes:
            m = siorg.normalizar() if f == "siorg" else orcamento.normalizar(a.exercicio)
            print(f"[normalizar] {f}: {'MUDOU' if m else 'sem mudança'}")
            mudou |= m
    if a.comando == "correspondencias" or (a.comando == "atualizar" and "orcamento" in fontes):
        n = correspondencia.gravar(correspondencia.sugerir(a.exercicio))
        print(f"[correspondencias] {n} UOs novas sugeridas")
        mudou |= n > 0
    if a.comando == "validar":
        rel = validar.validar_tudo()
        print(rel.texto())
        return 1 if rel.erros or (a.estrito and rel.avisos) else 0
    if a.comando == "publicar":
        rel = validar.validar_tudo()
        if rel.erros:
            print(rel.texto())
            print("Publicação cancelada: corrija os erros acima.")
            return 1
        for nome, tam in publicar.publicar(a.exercicio).items():
            print(f"[publicar] {nome}: {tam / 1024:.1f} KB")
    return 3 if (mudou and a.sinalizar_mudanca) else 0


if __name__ == "__main__":
    sys.exit(main())
