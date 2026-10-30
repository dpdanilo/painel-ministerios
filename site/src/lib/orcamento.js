/** Agregações sobre `orcamento.linhas` do JSON do ministério. */

export const ETAPAS = [
  { chave: "dotacao_atual", nome: "Dotação atual" },
  { chave: "empenhado", nome: "Empenhado" },
  { chave: "liquidado", nome: "Liquidado" },
  { chave: "pago", nome: "Pago" },
];

/** Linhas como objetos, já filtradas. filtro: { uo, prog, acao } (valores vazios = todos) */
export function linhas(orc, filtro = {}) {
  if (!orc) return [];
  return orc.linhas
    .map((l) => Object.fromEntries(orc.colunas.map((c, i) => [c, l[i]])))
    .filter((l) => (!filtro.uo || l.uo === filtro.uo) && (!filtro.prog || l.programa === filtro.prog) && (!filtro.acao || l.acao === filtro.acao));
}

export function somar(lista) {
  const t = { dotacao_inicial: 0, dotacao_atual: 0, empenhado: 0, liquidado: 0, pago: 0, empenhado_emendas: 0 };
  for (const l of lista) for (const k in t) t[k] += l[k] || 0;
  return t;
}

/** Agrupa por `campo` ("programa" | "acao" | "uo"), maior dotação atual primeiro. */
export function agrupar(lista, campo) {
  const g = new Map();
  for (const l of lista) {
    if (!g.has(l[campo])) g.set(l[campo], []);
    g.get(l[campo]).push(l);
  }
  return [...g].map(([codigo, ls]) => ({ codigo, ...somar(ls) })).sort((a, b) => b.dotacao_atual - a.dotacao_atual || b.pago - a.pago);
}

/** Série mensal acumulada (jan..último mês) de empenhado, liquidado e pago.
 *  filtro: { prog, excluir: Set de programas a ignorar } */
export function acumuladoMensal(orc, filtro = {}) {
  if (!orc) return [];
  const programasPermitidos = filtro.prog ? new Set([filtro.prog]) : null;
  const porMes = new Map();
  for (const [mes, prog, emp, liq, pago] of orc.mensal) {
    if (programasPermitidos && !programasPermitidos.has(prog)) continue;
    if (filtro.excluir?.has(prog)) continue;
    const v = porMes.get(mes) || [0, 0, 0];
    porMes.set(mes, [v[0] + emp, v[1] + liq, v[2] + pago]);
  }
  const meses = [...porMes.keys()].sort((a, b) => a - b);
  const acc = [0, 0, 0];
  return meses.map((m) => {
    const v = porMes.get(m);
    acc[0] += v[0]; acc[1] += v[1]; acc[2] += v[2];
    return { mes: m, empenhado: acc[0], liquidado: acc[1], pago: acc[2] };
  });
}
