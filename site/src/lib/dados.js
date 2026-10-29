const BASE = import.meta.env.BASE_URL + "data/";
const cache = new Map();

/** Busca um JSON publicado (cacheado em memória durante a sessão). */
export function carregar(caminho) {
  if (!cache.has(caminho)) {
    const p = fetch(BASE + caminho).then((r) => {
      if (!r.ok) throw new Error(`Não foi possível carregar ${caminho} (${r.status})`);
      return r.json();
    });
    p.catch(() => cache.delete(caminho));
    cache.set(caminho, p);
  }
  return cache.get(caminho);
}

export const carregarIndice = () => carregar("index.json");
export const carregarMinisterio = (id) => carregar(`ministerios/${id}.json`);
