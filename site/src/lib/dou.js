// Atos do Diário Oficial (dou.json): nomeações e exonerações a partir de Diretor (1.15) e normas de estrutura.

/** [data, acao, nome, cargo, funcao, nivel, ministerio_id, url] → objeto */
export const decodificar = (l) => ({
  data: l[0], acao: l[1] === "n" ? "nomeacao" : "exoneracao", nome: l[2], cargo: l[3],
  funcao: l[4], nivel: l[5], mid: l[6], url: l[7],
});

export const ACOES = { nomeacao: "Nomeação", exoneracao: "Exoneração" };

/** Alto escalão: Ministro(a) (20), Natureza Especial (19) e 1.17–1.18 / decretos do Presidente (18). */
export const ALTO = 17;

/** Primeiro dia depois do mês de referência do SIAPE ("2026-08" → "2026-09-01"): o que o SIAPE ainda não mostra. */
export function depoisDoSiape(ref) {
  if (!ref) return null;
  const [a, m] = ref.split("-").map(Number);
  return m === 12 ? `${a + 1}-01-01` : `${a}-${String(m + 1).padStart(2, "0")}-01`;
}

export function filtrarAtos(atos, { mid = null, nivelMin = 15, acao = "", desde = null } = {}) {
  return atos.filter((a) => (!mid || a.mid === mid) && a.nivel >= nivelMin && (!acao || a.acao === acao) && (!desde || a.data >= desde));
}

/** Última nomeação de Ministro(a) de cada órgão publicada depois de `desde` (mid → ato). */
export function ministrosNovos(atos, desde) {
  const r = new Map();
  for (const a of atos) {
    if (a.nivel !== 20 || a.acao !== "nomeacao" || (desde && a.data < desde)) continue;
    if (!r.has(a.mid) || r.get(a.mid).data < a.data) r.set(a.mid, a);
  }
  return r;
}

export function contar(atos) {
  const c = { nomeacao: 0, exoneracao: 0, ministros: 0 };
  for (const a of atos) {
    c[a.acao]++;
    if (a.nivel === 20 && a.acao === "nomeacao") c.ministros++;
  }
  return c;
}
