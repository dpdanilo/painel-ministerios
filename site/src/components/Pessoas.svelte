<script>
  import { href } from "../lib/estado.svelte.js";
  import { normalizar, data as fmtData } from "../lib/formato.js";
  import { caminho, cargoDirigente } from "../lib/estrutura.js";
  import BotaoCsv from "./BotaoCsv.svelte";
  import Fonte from "./Fonte.svelte";

  let { m, idx } = $props();
  let filtro = $state("");

  // Ordena pela hierarquia: nível do cargo da unidade (Ministro primeiro), depois profundidade.
  let ordem = $derived(new Map(m.unidades.map((u, i) => [u.c, i])));
  let todos = $derived(m.ocupantes
    .map((o) => {
      const u = idx.porCodigo.get(o.unidade);
      const sec = caminho(idx, o.unidade)[1];
      const dir = cargoDirigente(m.cargos[o.unidade]);
      const nivel = dir?.rotulo === "Ministro de Estado" ? 99 : dir?.nivel ?? 0;
      return { ...o, sigla: u?.s, area: sec && sec.c !== o.unidade ? sec.s : u?.s, d: u?.d ?? 9, nivel };
    })
    .sort((a, b) => b.nivel - a.nivel || a.d - b.d || (a.papel === "titular" ? 0 : 1) - (b.papel === "titular" ? 0 : 1) || ordem.get(a.unidade) - ordem.get(b.unidade)));

  let lista = $derived(filtro ? todos.filter((o) => normalizar(`${o.nome} ${o.cargo} ${o.sigla} ${o.area}`).includes(normalizar(filtro))) : todos);

  const colunas = [
    { chave: "nome", titulo: "Nome" }, { chave: "cargo", titulo: "Cargo" }, { chave: "sigla", titulo: "Unidade" },
    { chave: "unidade", titulo: "Código SIORG" }, { chave: "papel", titulo: "Papel" }, { chave: "partido", titulo: "Partido" },
    { chave: "de", titulo: "Início" }, { chave: "ate", titulo: "Fim" }, { chave: "fonte", titulo: "Fonte" },
  ];
</script>

<section class="cartao" aria-labelledby="t-pessoas">
  <h2 id="t-pessoas">Quem é quem</h2>
  <p class="sec">Ministro, secretários e diretores em exercício. Datas de nomeação e partido ainda estão em curadoria: aparecem como “não verificado” até serem confirmados no Diário Oficial.</p>
  <div class="filtros">
    <label>Filtrar
      <input type="search" bind:value={filtro} placeholder="Nome, cargo ou sigla" />
    </label>
    <BotaoCsv arquivo={`${m.id}-ocupantes.csv`} {colunas} linhas={() => lista} />
  </div>
  <div class="tabela-rolagem">
    <table>
      <thead><tr><th>Nome</th><th>Cargo</th><th>Unidade</th><th>Partido</th><th>Início</th></tr></thead>
      <tbody>
        {#each lista as o (o.pessoa + o.unidade)}
          <tr>
            <td><strong>{o.nome}</strong></td>
            <td>{o.cargo}</td>
            <td><a href={href(["m", m.id, "estrutura"], { u: o.unidade })}>{o.sigla}</a>{#if o.area !== o.sigla}<span class="mudo"> · {o.area}</span>{/if}</td>
            <td class:mudo={!o.partido}>{o.partido || "não informado"}</td>
            <td class:mudo={!o.de}>{o.de ? fmtData(o.de) : "não verificado"}</td>
          </tr>
        {:else}
          <tr><td colspan="5" class="mudo">Ninguém encontrado.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
  <Fonte fonte={m.fontes.ocupantes} rotuloData="Verificado em" curado />
</section>
