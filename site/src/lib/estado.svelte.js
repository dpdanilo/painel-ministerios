/**
 * Estado global: rota (hash compartilhável) e tema.
 * Rotas:  #/                       início
 *         #/m/<id>/<aba>?u=…&prog=…  ministério (aba: estrutura|pessoas|orcamento|politicas|sobre)
 */

function lerHash() {
  const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  const [caminho, consulta = ""] = h.split("?");
  const partes = caminho.split("/").filter(Boolean);
  return { partes, params: Object.fromEntries(new URLSearchParams(consulta)) };
}

export const rota = $state(lerHash());

addEventListener("hashchange", () => Object.assign(rota, lerHash()));

export function href(partes, params = {}) {
  const limpos = Object.entries(params).filter(([, v]) => v != null && v !== "");
  const q = limpos.length ? "?" + new URLSearchParams(limpos).toString() : "";
  return "#/" + partes.join("/") + q;
}

/** Atualiza só os parâmetros (filtros) sem criar entrada no histórico. */
export function trocarParams(novos) {
  const params = { ...rota.params, ...novos };
  history.replaceState(null, "", href(rota.partes, params));
  rota.params = Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ""));
}

// ---------------------------------------------------------------- tema

const escuroSO = matchMedia("(prefers-color-scheme: dark)");

function temaEfetivo() {
  const t = document.documentElement.dataset.theme;
  return t || (escuroSO.matches ? "dark" : "light");
}

export const tema = $state({ atual: temaEfetivo() });

escuroSO.addEventListener("change", () => (tema.atual = temaEfetivo()));

export function alternarTema() {
  const novo = tema.atual === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = novo;
  try { localStorage.setItem("tema", novo); } catch {}
  tema.atual = novo;
}
