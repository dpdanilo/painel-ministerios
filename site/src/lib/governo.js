/** Cálculos da visão de governo e da comparação (sobre index.json e agregados/comparacao.json). */

export const CATEGORIAS = {
  ministerio: { nome: "Ministério", cor: "--series-1" },
  presidencia: { nome: "Órgão da Presidência", cor: "--series-2" },
  orgao: { nome: "Outro órgão com status de ministério", cor: "--series-3" },
};

export const METRICAS = [
  { id: "orc_sem_oe", nome: "Orçamento sem operações especiais", dica: "Dotação atual, sem dívida pública, transferências constitucionais, sentenças e outros encargos", tipo: "brl",
    valor: (m) => m.orcamento_sem_oe?.dotacao_atual ?? null },
  { id: "orc", nome: "Orçamento total", dica: "Dotação atual, incluindo operações especiais (dívida, transferências, benefícios)", tipo: "brl",
    valor: (m) => m.orcamento?.dotacao_atual ?? null },
  { id: "cargos", nome: "Cargos e funções", dica: "CCE, FCE e Ministro alocados na estrutura (SIORG)", tipo: "num", valor: (m) => m.n_cargos },
  { id: "unidades", nome: "Unidades", dica: "Unidades na estrutura do órgão, incluindo colegiados e entidades vinculadas", tipo: "num", valor: (m) => m.n_unidades },
];

export function somarGoverno(ministerios) {
  const t = { n: ministerios.length, unidades: 0, cargos: 0, dotacao: 0, pago: 0, dotacao_sem_oe: 0, pago_sem_oe: 0 };
  for (const m of ministerios) {
    t.unidades += m.n_unidades;
    t.cargos += m.n_cargos;
    t.dotacao += m.orcamento?.dotacao_atual || 0;
    t.pago += m.orcamento?.pago || 0;
    t.dotacao_sem_oe += m.orcamento_sem_oe?.dotacao_atual || 0;
    t.pago_sem_oe += m.orcamento_sem_oe?.pago || 0;
  }
  return t;
}

/** % pago sobre a dotação atual (sem operações especiais). null se não há orçamento próprio. */
export function execucao(m) {
  const o = m.orcamento_sem_oe;
  return o && o.dotacao_atual ? o.pago / o.dotacao_atual : null;
}

/** Ordena com nulos sempre no fim. */
export function ordenar(lista, chave, desc = true) {
  return [...lista].sort((a, b) => {
    const va = chave(a), vb = chave(b);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "string") return desc ? vb.localeCompare(va, "pt-BR") : va.localeCompare(vb, "pt-BR");
    return desc ? vb - va : va - vb;
  });
}

/**
 * Cores estáveis da comparação: cada ministério guarda o slot que recebeu ao entrar, para que
 * remover um não repinte os outros. `anterior`: Map id→slot. Devolve um Map novo.
 */
export function atribuirSlots(ids, anterior = new Map(), maxSlots = 6) {
  const slots = new Map();
  for (const id of ids) if (anterior.has(id)) slots.set(id, anterior.get(id));
  const usados = new Set(slots.values());
  for (const id of ids) {
    if (slots.has(id)) continue;
    let s = 0;
    while (usados.has(s) && s < maxSlots) s++;
    slots.set(id, s);
    usados.add(s);
  }
  return slots;
}

/** Níveis de direção (categoria 1) presentes em qualquer dos ministérios, do maior para o menor. */
export function niveisDirecao(detalhes) {
  const n = new Set();
  for (const d of detalhes) for (const k of Object.keys(d.cargos_por_nivel)) {
    const m = /^(CCE|FCE) 1\.(\d+)$/.exec(k);
    if (m) n.add(Number(m[2]));
  }
  return [...n].sort((a, b) => b - a);
}

export function cargosDirecao(detalhe, nivel) {
  const c = detalhe.cargos_por_nivel;
  const nn = String(nivel).padStart(2, "0");
  return (c[`CCE 1.${nn}`] || 0) + (c[`FCE 1.${nn}`] || 0);
}

export const SEM_CANDIDATURA = "Sem candidatura";

/** Titulares atuais agrupados pelo partido da candidatura mais recente (TSE). */
export function porPartido(ministerios) {
  const g = new Map();
  for (const m of ministerios) {
    if (!m.ministro) continue;
    const sigla = m.ministro.partido?.sigla ?? SEM_CANDIDATURA;
    const v = g.get(sigla) || { sigla, n: 0, orcamento: 0, cargos: 0, orgaos: [] };
    v.n += 1;
    v.orcamento += m.orcamento_sem_oe?.dotacao_atual || 0;
    v.cargos += m.n_cargos;
    v.orgaos.push(m.sigla);
    g.set(sigla, v);
  }
  return [...g.values()].sort((a, b) => (a.sigla === SEM_CANDIDATURA) - (b.sigla === SEM_CANDIDATURA) || b.n - a.n || b.orcamento - a.orcamento);
}

/** Totais de rotatividade no governo (desde jan/2023). */
export function rotatividadeGoverno(ministerios) {
  let trocas = 0, mandatos = 0, somaMeses = 0, nMeses = 0, trocasSec = 0, somaSec = 0, nSec = 0;
  for (const m of ministerios) {
    const r = m.rotatividade;
    if (!r) continue;
    trocas += r.ministros.encerrados;
    mandatos += r.ministros.mandatos;
    if (r.ministros.meses_medio != null) { somaMeses += r.ministros.meses_medio * r.ministros.mandatos; nMeses += r.ministros.mandatos; }
    trocasSec += r.secretarios.encerrados;
    if (r.secretarios.meses_medio != null) { somaSec += r.secretarios.meses_medio * r.secretarios.mandatos; nSec += r.secretarios.mandatos; }
  }
  return { trocas, mandatos, meses_medio: nMeses ? somaMeses / nMeses : null, trocas_secretarios: trocasSec, meses_medio_secretario: nSec ? somaSec / nSec : null };
}
