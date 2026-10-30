const inteiro = new Intl.NumberFormat("pt-BR");
const umaCasa = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

/** R$ 15,0 bi · R$ 323,4 mi · R$ 12,5 mil · R$ 980 */
export function brlCompacto(v) {
  if (v == null || Number.isNaN(v)) return "–";
  const a = Math.abs(v);
  const s = v < 0 ? "−" : "";
  if (a >= 1e9) return `${s}R$ ${umaCasa.format(a / 1e9)} bi`;
  if (a >= 1e6) return `${s}R$ ${umaCasa.format(a / 1e6)} mi`;
  if (a >= 1e3) return `${s}R$ ${umaCasa.format(a / 1e3)} mil`;
  return `${s}R$ ${inteiro.format(Math.round(a))}`;
}

export const brl = (v) => (v == null ? "–" : reais.format(v));
export const num = (v) => (v == null ? "–" : inteiro.format(v));

export function pct(parte, todo) {
  if (!todo) return "–";
  return `${umaCasa.format((100 * parte) / todo)}%`;
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const mesCurto = (m) => MESES[m - 1];

/** "2026-10-19" → "19/10/2026" */
export function data(iso) {
  if (!iso) return null;
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

/** Código de cargo: CCE, categoria 1, nível 17 → "CCE 1.17" */
export function rotuloCargo(tipo, categoria, nivel) {
  if (!categoria || !nivel) return tipo;
  return `${tipo} ${categoria}.${nivel}`;
}

/** Remove acentos e caixa para busca. */
export const normalizar = (s) => (s || "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

/** Nomes do orçamento vêm em CAIXA ALTA sem acento: deixa só a 1ª letra maiúscula. */
export function capitalizar(s) {
  if (!s) return s;
  if (s !== s.toUpperCase()) return s;
  const minusculo = s.toLowerCase();
  return minusculo.charAt(0).toUpperCase() + minusculo.slice(1);
}

/** Partido vindo do TSE (candidatura mais recente) ou da curadoria. */
export function partidoSigla(p) {
  return p?.sigla ?? null;
}

export function partidoDetalhe(p) {
  if (!p) return "Sem candidatura registrada no TSE (2018–2026)";
  if (p.fonte === "TSE") return `Partido na candidatura a ${p.cargo} em ${p.ano}${p.uf ? ` (${p.uf})` : ""} · TSE`;
  return "Filiação informada na curadoria";
}

/** "2026-08" ou "2026-08-15" → "ago/2026" */
export function mesAno(iso) {
  if (!iso) return null;
  return `${mesCurto(Number(iso.slice(5, 7)))}/${iso.slice(0, 4)}`;
}

/** Meses → "1 ano e 3 meses" */
export function duracao(meses) {
  if (meses == null) return "–";
  const a = Math.floor(meses / 12), m = Math.round(meses % 12);
  const pa = a ? `${a} ano${a > 1 ? "s" : ""}` : "";
  const pm = m ? `${m} ${m > 1 ? "meses" : "mês"}` : "";
  return [pa, pm].filter(Boolean).join(" e ") || "menos de 1 mês";
}
