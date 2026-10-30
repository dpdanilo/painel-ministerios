/** Série histórica: eventos institucionais e orçamento corrigido pelo IPCA. */

export const TIPOS_EVENTO = {
  criacao: "Criação", recriacao: "Recriação", fusao: "Fusão", desmembramento: "Desmembramento",
  extincao: "Extinção", transformacao: "Transformação", renomeacao: "Novo nome",
};

/** Início de cada mandato presidencial no período (marcas de referência nos gráficos). */
export const GOVERNOS = [
  { x: "2003-01-01", rotulo: "Lula" },
  { x: "2011-01-01", rotulo: "Dilma" },
  { x: "2016-05-12", rotulo: "Temer" },
  { x: "2019-01-01", rotulo: "Bolsonaro" },
  { x: "2023-01-01", rotulo: "Lula" },
];

/** Agrupa eventos pela norma (uma reforma = uma MP), da mais recente para a mais antiga. */
export function porNorma(eventos, normas = {}) {
  const g = new Map();
  for (const e of eventos) {
    const k = e.norma || e.data;
    if (!g.has(k)) g.set(k, { norma: e.norma, info: normas[e.norma], data: e.data, eventos: [] });
    g.get(k).eventos.push(e);
  }
  return [...g.values()].sort((a, b) => b.data.localeCompare(a.data));
}

/** Valor em reais de hoje: multiplica pelo fator IPCA do ano (fatores vêm do index.json). */
export function corrigir(valor, ano, ipca) {
  const f = ipca?.fatores?.[ano];
  return valor == null ? null : f ? valor * f : valor;
}

/** Série anual [[ano, dot_ini, dot_atual, empenhado, pago, dot_atual_sem_oe, pago_sem_oe]] → pontos de uma coluna. */
export function serieAnual(linhas, coluna, { real = false, ipca = null } = {}) {
  const idx = { dotacao_inicial: 1, dotacao_atual: 2, empenhado: 3, pago: 4, dotacao_sem_oe: 5, pago_sem_oe: 6 }[coluna];
  return linhas.map((l) => [String(l[0]), real ? corrigir(l[idx], l[0], ipca) : l[idx]]);
}
