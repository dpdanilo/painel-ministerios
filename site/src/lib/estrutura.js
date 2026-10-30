import { normalizar, rotuloCargo } from "./formato.js";

export const BLOCOS = [
  { id: "assistencia", nome: "Assistência direta e imediata ao Ministro", resumo: "Apoio político, jurídico, de controle e de gestão" },
  { id: "singular", nome: "Órgãos específicos singulares", resumo: "Secretarias finalísticas: executam as políticas públicas" },
  { id: "descentralizada", nome: "Unidades descentralizadas", resumo: "Superintendências, escritórios regionais e representações no exterior" },
  { id: "pesquisa", nome: "Unidades de pesquisa", resumo: "Institutos e centros de pesquisa da administração direta" },
  { id: "forcas", nome: "Forças Armadas", resumo: "Comandos da Marinha, do Exército e da Aeronáutica" },
  { id: "colegiado", nome: "Órgãos colegiados", resumo: "Conselhos e comitês de participação social e gestão de fundos" },
  { id: "vinculada", nome: "Entidades vinculadas", resumo: "Administração indireta sob supervisão do ministério" },
];

/** Hierarquia típica (Lei 14.204/2021) — docs/estrutura-ministerios-referencia.md §4 */
export const HIERARQUIA = [
  { cargo: "Ministro de Estado", nivel: "fora da escala" },
  { cargo: "Secretário-Executivo", nivel: "CCE 1.18" },
  { cargo: "Secretário Nacional", nivel: "CCE 1.17" },
  { cargo: "Diretor de Departamento", nivel: "CCE 1.15" },
  { cargo: "Coordenador-Geral", nivel: "CCE/FCE 1.13" },
  { cargo: "Coordenador", nivel: "abaixo de 1.13" },
];

/** Índices sobre a lista plana de unidades do JSON do ministério. */
export function indexar(m) {
  const porCodigo = new Map(m.unidades.map((u) => [u.c, u]));
  const filhos = new Map();
  for (const u of m.unidades) {
    if (!u.p || !porCodigo.has(u.p)) continue;
    if (!filhos.has(u.p)) filhos.set(u.p, []);
    filhos.get(u.p).push(u);
  }
  const raiz = m.unidades.find((u) => u.d === 0);
  const ocupantesPorUnidade = new Map();
  for (const o of m.ocupantes) {
    if (o.ate) continue;
    if (!ocupantesPorUnidade.has(o.unidade)) ocupantesPorUnidade.set(o.unidade, []);
    ocupantesPorUnidade.get(o.unidade).push(o);
  }
  return { porCodigo, filhos, raiz, ocupantesPorUnidade };
}

/** Caminho da raiz até a unidade (inclusive). */
export function caminho(idx, cod) {
  const saida = [];
  let u = idx.porCodigo.get(cod);
  while (u) {
    saida.unshift(u);
    u = u.p ? idx.porCodigo.get(u.p) : null;
  }
  return saida;
}

/** Total de unidades abaixo de `cod`. */
export function contarDescendentes(idx, cod) {
  let n = 0;
  for (const f of idx.filhos.get(cod) || []) n += 1 + contarDescendentes(idx, f.c);
  return n;
}

/** Cargo do dirigente: o de categoria 1 (direção) com maior nível; Ministro (MEST) na raiz. */
export function cargoDirigente(cargos) {
  if (!cargos?.length) return null;
  const mest = cargos.find((c) => c[0] === "MEST");
  if (mest) return { rotulo: "Ministro de Estado", denominacao: mest[3] };
  const direcao = cargos.filter((c) => c[1] === "1").sort((a, b) => Number(b[2]) - Number(a[2]));
  const c = direcao[0];
  return c ? { rotulo: rotuloCargo(c[0], c[1], c[2]), denominacao: c[3], nivel: Number(c[2]) } : null;
}

/** Contagem de cargos por tipo+categoria+nível (ex.: "CCE 1.17" → 5). */
export function cargosPorNivel(m) {
  const tot = new Map();
  for (const lista of Object.values(m.cargos)) {
    for (const [tipo, cat, nivel, , qtd] of lista) {
      const k = rotuloCargo(tipo, cat, nivel);
      tot.set(k, (tot.get(k) || 0) + qtd);
    }
  }
  return tot;
}

/** Busca por unidade, pessoa, programa, ação ou política. */
export function buscar(m, termo, limite = 30) {
  const q = normalizar(termo.trim());
  if (q.length < 2) return [];
  const bate = (...textos) => textos.some((t) => normalizar(t).includes(q));
  const r = [];
  for (const u of m.unidades) if (bate(u.n, u.s)) r.push({ tipo: "Unidade", titulo: `${u.s} – ${u.n}`, rota: ["estrutura", { u: u.c }] });
  for (const o of m.ocupantes) {
    if (!o.ate && bate(o.nome, o.cargo)) r.push({ tipo: "Pessoa", titulo: `${o.nome} – ${o.cargo}`, rota: o.unidade ? ["estrutura", { u: o.unidade }] : ["pessoas", {}] });
  }
  for (const p of m.politicas) if (bate(p.nome)) r.push({ tipo: "Política", titulo: p.nome, rota: ["politicas", { p: p.id }] });
  const orc = m.orcamento;
  if (orc) {
    for (const [c, n] of Object.entries(orc.programas)) if (bate(n, c)) r.push({ tipo: "Programa", titulo: `${c} – ${n}`, rota: ["orcamento", { prog: c }] });
    for (const [c, n] of Object.entries(orc.acoes)) if (bate(n, c)) r.push({ tipo: "Ação", titulo: `${c} – ${n}`, rota: ["orcamento", { acao: c }] });
  }
  return r.slice(0, limite);
}
