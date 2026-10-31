<script>
  import { carregar } from "../lib/dados.js";
  import { href } from "../lib/estado.svelte.js";
  import { data as fmtData, mesAno, normalizar } from "../lib/formato.js";
  import { decodificar, filtrarAtos, contar, depoisDoSiape, ACOES, ALTO } from "../lib/dou.js";
  import BotaoCsv from "./BotaoCsv.svelte";
  import Fonte from "./Fonte.svelte";

  /** mid: só os atos de um órgão (tela do ministério); nomes: id → sigla (tela de governo). */
  let { mid = null, nomes = null, titulo = "Publicado no Diário Oficial" } = $props();

  let dou = $state(null);
  let erro = $state(false);
  carregar("dou.json").then((d) => (dou = d), () => (erro = true));

  // Num ministério há poucos atos de alto escalão: lá o padrão é a partir de Diretor.
  let alto = $state(!mid);
  let acao = $state("");
  let soNovos = $state(true);
  let filtro = $state("");
  let limite = $state(25);

  let todos = $derived(dou ? dou.atos.map(decodificar) : []);
  let corte = $derived(dou ? depoisDoSiape(dou.referencia_siape) : null);
  let base = $derived(filtrarAtos(todos, { mid, nivelMin: alto ? ALTO : 15, desde: soNovos ? corte : null }));
  let lista = $derived(filtrarAtos(base, { acao }).filter((a) => !filtro || normalizar(`${a.nome} ${a.cargo} ${nomes?.[a.mid] ?? ""}`).includes(normalizar(filtro))));
  let n = $derived(contar(base));
  let normas = $derived(dou ? dou.normas.filter((x) => (!mid || x.ministerio_id === mid) && (!soNovos || x.data >= corte)) : []);

  const colunas = [
    { chave: "data", titulo: "Publicação" }, { chave: "ato", titulo: "Ato" }, { chave: "nome", titulo: "Pessoa" },
    { chave: "cargo", titulo: "Cargo" }, { chave: "funcao", titulo: "Código/natureza" }, { chave: "orgao", titulo: "Órgão" },
    { chave: "url", titulo: "Link no DOU" },
  ];
  const linhasCsv = () => lista.map((a) => ({ ...a, ato: ACOES[a.acao], orgao: nomes?.[a.mid] ?? a.mid }));
</script>

{#if dou && !erro}
  <section class="cartao" aria-labelledby={`t-dou-${mid ?? "gov"}`}>
    <div class="cab-secao">
      <h2 id={`t-dou-${mid ?? "gov"}`}>{titulo}</h2>
      <BotaoCsv arquivo={`${mid ?? "governo"}-dou.csv`} {colunas} linhas={linhasCsv} />
    </div>
    <p class="sec pequeno">
      Nomeações e exonerações publicadas no Diário Oficial{#if soNovos && corte}{" "}desde {fmtData(corte)}, que o cadastro de servidores (SIAPE, dados até {mesAno(dou.referencia_siape)}) ainda não mostra{/if}.
      Lido automaticamente todo dia: confira sempre o ato original.
    </p>

    <div class="tiles tres">
      <div class="tile"><div class="rot">Nomeações</div><div class="val num">{n.nomeacao}</div></div>
      <div class="tile"><div class="rot">Exonerações</div><div class="val num">{n.exoneracao}</div></div>
      <div class="tile"><div class="rot">{mid ? "Novo(a) ministro(a)" : "Ministros nomeados"}</div><div class="val num">{n.ministros}</div></div>
    </div>

    <div class="filtros">
      <div class="segmentado" role="group" aria-label="Cargos">
        <button type="button" aria-pressed={alto} onclick={() => (alto = true)}>Alto escalão</button>
        <button type="button" aria-pressed={!alto} onclick={() => (alto = false)}>A partir de Diretor</button>
      </div>
      <label class="sr-only" for={`acao-${mid ?? "gov"}`}>Tipo de ato</label>
      <select id={`acao-${mid ?? "gov"}`} bind:value={acao}>
        <option value="">Nomeações e exonerações</option>
        <option value="nomeacao">Só nomeações</option>
        <option value="exoneracao">Só exonerações</option>
      </select>
      <label class="caixa"><input type="checkbox" bind:checked={soNovos} /> Só depois do SIAPE</label>
      {#if !mid}<input type="search" bind:value={filtro} placeholder="Nome, cargo ou órgão" aria-label="Filtrar atos" />{/if}
    </div>
    <p class="mudo pequeno">Alto escalão: ministros, cargos de Natureza Especial (secretários-executivos), CCE/FCE 1.17 e 1.18 (secretários, presidentes de autarquias) e cargos providos por decreto do Presidente.</p>

    <div class="tabela-rolagem">
      <table class="atos">
        <thead><tr><th>Publicação</th><th>Ato</th><th>Pessoa</th><th>Cargo</th>{#if !mid}<th>Órgão</th>{/if}<th><span class="sr-only">Link</span></th></tr></thead>
        <tbody>
          {#each lista.slice(0, limite) as a, i (a.url + i)}
            <tr class:destaque={a.nivel === 20}>
              <td class="nowrap">{fmtData(a.data)}</td>
              <td><span class="chip" class:sai={a.acao === "exoneracao"}>{ACOES[a.acao]}</span></td>
              <td><strong>{a.nome}</strong></td>
              <td>{a.cargo} <span class="mudo nowrap">{a.funcao}</span></td>
              {#if !mid}<td>{#if nomes?.[a.mid]}<a href={href(["m", a.mid, "pessoas"])}>{nomes[a.mid]}</a>{:else}{a.mid}{/if}</td>{/if}
              <td><a href={a.url} target="_blank" rel="noopener">DOU</a></td>
            </tr>
          {:else}
            <tr><td colspan={mid ? 5 : 6} class="mudo">Nenhum ato no período.</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if lista.length > limite}
      <button type="button" class="botao mais" onclick={() => (limite += 50)}>Mostrar mais ({lista.length - limite} restantes)</button>
    {/if}

    {#if normas.length}
      <h3>Normas de estrutura</h3>
      <ul class="normas">
        {#each normas as x (x.url)}
          <li>
            <span class="quando num">{fmtData(x.data)}</span>
            <a href={x.url} target="_blank" rel="noopener">{x.titulo}</a>
            {#if !mid && nomes?.[x.ministerio_id]}<span class="chip">{nomes[x.ministerio_id]}</span>{/if}
            <span class="mudo resumo">{x.resumo}</span>
          </li>
        {/each}
      </ul>
    {/if}
    <Fonte fonte={{ nome: "Imprensa Nacional – Diário Oficial da União (seções 1 e 2, inclusive edições extras)", url: "https://www.in.gov.br/leiturajornal", data: dou.ultimo_dia }} rotuloData="Lido até" />
  </section>
{/if}

<style>
  .pequeno { font-size: 0.82rem; }
  .filtros { margin: 14px 0 6px; display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }
  .filtros > * { flex: 0 1 auto; }
  .filtros select, .filtros input[type="search"] { width: auto; min-width: min(240px, 100%); }
  .caixa { display: flex !important; align-items: center; gap: 8px; min-height: 38px; flex: 0 1 auto !important; font-size: 0.88rem !important; }
  .caixa input { width: 18px; height: 18px; accent-color: var(--marca); }
  .chip.sai { border-style: dashed; }
  tr.destaque td { background: var(--cartao-2); }
  .mais { margin-top: 10px; }
  .tiles.tres { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
  /* No celular, cada ato vira um bloco: a coluna de cargo ficava espremida. */
  @media (max-width: 640px) {
    .tiles.tres .tile { padding: 8px 10px; }
    .tiles.tres .rot { font-size: 0.74rem; }
    .atos, .atos tbody, .atos tr, .atos td { display: block; }
    .atos thead { display: none; }
    .atos tr { padding: 10px 0; border-bottom: 1px solid var(--linha); }
    .atos td { border: 0; padding: 2px 0; }
    .atos td:first-child, .atos td:nth-child(2) { display: inline-block; margin-right: 8px; }
  }
  h3 { margin: 20px 0 8px; font-size: 1rem; }
  .normas { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
  .normas li { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; padding-bottom: 8px; border-bottom: 1px solid var(--linha); }
  .resumo { flex-basis: 100%; font-size: 0.82rem; }
  .quando { font-size: 0.8rem; color: var(--mudo); }
</style>
