"""Mescla de snapshots com vigência (valido_de / valido_ate).

Cada coleta traz a foto atual de uma fonte. Comparando com o CSV já versionado:
- linha nova                → entra com valido_de = data informada pela fonte (ou do snapshot);
- linha com campo alterado  → a versão antiga é fechada e uma nova é aberta;
- linha que sumiu da fonte  → a versão vigente é fechada na data do snapshot.
Versões fechadas nunca são alteradas, então o histórico se acumula a cada coleta.
"""
from __future__ import annotations


def mesclar(antigas: list[dict], novas: list[dict], chave: list[str], monitorados: list[str],
            data_snapshot: str, escopo: dict[str, set] | None = None) -> list[dict]:
    """`escopo` restringe o fechamento por ausência às linhas cujo campo está no conjunto
    (ex.: {"ministerio_id": {"mcid"}}), para não fechar linhas de ministérios não coletados agora."""
    k = lambda r: tuple(str(r.get(c) or "") for c in chave)
    vigentes = {k(r): r for r in antigas if not r.get("valido_ate")}
    saida = [r for r in antigas if r.get("valido_ate")]
    vistos = set()

    for nova in novas:
        chave_nova = k(nova)
        vistos.add(chave_nova)
        velha = vigentes.get(chave_nova)
        if velha is None:
            saida.append({**nova, "valido_de": nova.get("valido_de") or data_snapshot, "valido_ate": ""})
        elif any(str(velha.get(c) or "") != str(nova.get(c) or "") for c in monitorados):
            inicio = nova.get("valido_de") or data_snapshot
            # Se a fonte não informa uma data nova de vigência, usa a do snapshot.
            if inicio <= (velha.get("valido_de") or ""):
                inicio = data_snapshot
            saida.append({**velha, "valido_ate": inicio})
            saida.append({**nova, "valido_de": inicio, "valido_ate": ""})
        else:
            saida.append({**velha, **{c: nova.get(c) for c in nova if c not in ("valido_de", "valido_ate")},
                          "valido_de": velha.get("valido_de"), "valido_ate": ""})

    for chave_velha, velha in vigentes.items():
        if chave_velha in vistos:
            continue
        fora_do_escopo = escopo and any(str(velha.get(c)) not in vals for c, vals in escopo.items())
        saida.append(velha if fora_do_escopo else {**velha, "valido_ate": data_snapshot})
    return saida
