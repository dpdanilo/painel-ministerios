<script>
  import { href } from "../lib/estado.svelte.js";
  import { normalizar, data as fmtData, mesAno, partidoSigla, partidoDetalhe } from "../lib/formato.js";
  import BotaoCsv from "./BotaoCsv.svelte";
  import Fonte from "./Fonte.svelte";
  import AtosDou from "./AtosDou.svelte";

  let { m, idx } = $props();
  let filtro = $state("");

  let atuais = $derived(m.ocupantes.filter((o) => !o.ate));
  let lista = $derived(filtro
    ? atuais.filter((o) => normalizar(`${o.nome} ${o.cargo} ${o.uorg ?? ""} ${partidoSigla(o.partido) ?? ""}`).includes(normalizar(filtro)))
    : atuais);
  // Histórico: Ministros e Secretários (1.17–1.18) que já deixaram o cargo desde jan/2023.
  let historico = $derived(m.ocupantes.filter((o) => o.ate && (o.funcao === "MEST" || o.nivel >= 17))
    .sort((a, b) => (b.ate || "").localeCompare(a.ate || "")));
  let ministros = $derived(m.ocupantes.filter((o) => o.funcao === "MEST").sort((a, b) => (a.de || "").localeCompare(b.de || "")));

  const nomeUnidade = (o) => (o.unidade ? idx.porCodigo.get(o.unidade)?.s : null);
  const colunas = [
    { chave: "nome", titulo: "Nome" }, { chave: "cargo", titulo: "Cargo" }, { chave: "funcao", titulo: "Função" },
    { chave: "uorg", titulo: "Unidade (SIAPE)" }, { chave: "unidade", titulo: "Código SIORG" },
    { chave: "partido_sigla", titulo: "Partido (última candidatura)" }, { chave: "partido_ano", titulo: "Ano da candidatura" },
    { chave: "de", titulo: "Desde" }, { chave: "ate", titulo: "Saída (aprox.)" },
  ];
  const paraCsv = (ls) => () => ls.map((o) => ({ ...o, partido_sigla: partidoSigla(o.partido), partido_ano: o.partido?.ano }));
</script>

{#if ministros.length}
  <section class="cartao" aria-labelledby="t-min">
    <h2 id="t-min">Ministros desde 2023</h2>
    <ol class="linha-tempo">
      {#each ministros as o (o.pessoa + o.de)}
        <li class:atual={!o.ate}>
          <strong>{o.nome}</strong>
          <span class="sec">{fmtData(o.de) ?? "início não informado"} – {o.ate ? `~${mesAno(o.ate)}` : "hoje"}</span>
          <span class="chip" title={partidoDetalhe(o.partido)}>{partidoSigla(o.partido) ?? "sem candidatura"}</span>
        </li>
      {/each}
    </ol>
  </section>
{/if}

<AtosDou mid={m.id} titulo="Depois do SIAPE: atos no Diário Oficial" />

<section class="cartao" aria-labelledby="t-pessoas">
  <h2 id="t-pessoas">Quem ocupa os cargos de direção</h2>
  <p class="sec">Ministro(a) e cargos a partir de Diretor (CCE/FCE 1.15). “Desde” é a data de ingresso na função registrada no SIAPE. O partido é o da candidatura mais recente da pessoa no TSE; quem nunca foi candidato aparece como “sem candidatura”, o que não significa que não tenha partido.</p>
  <div class="filtros">
    <label>Filtrar
      <input type="search" bind:value={filtro} placeholder="Nome, cargo, unidade ou partido" />
    </label>
    <BotaoCsv arquivo={`${m.id}-dirigentes.csv`} {colunas} linhas={paraCsv(lista)} />
  </div>
  <div class="tabela-rolagem">
    <table>
      <thead><tr><th>Nome</th><th>Cargo</th><th>Unidade</th><th>Partido</th><th>Desde</th></tr></thead>
      <tbody>
        {#each lista as o, i (i)}
          <tr>
            <td><strong>{o.nome}</strong></td>
            <td>{o.cargo}{#if o.funcao !== "MEST"} <span class="mudo nowrap">{o.funcao}</span>{/if}</td>
            <td>
              {#if o.unidade}<a href={href(["m", m.id, "estrutura"], { u: o.unidade })}>{nomeUnidade(o)}</a>{/if}
              <span class="mudo pequeno">{o.uorg ?? ""}</span>
            </td>
            <td title={partidoDetalhe(o.partido)} class:mudo={!o.partido} class="nowrap">
              {partidoSigla(o.partido) ?? "sem candidatura"}
              {#if o.partido?.ano}<span class="mudo pequeno">({o.partido.ano})</span>{/if}
            </td>
            <td class="nowrap">{fmtData(o.de) ?? "–"}</td>
          </tr>
        {:else}
          <tr><td colspan="5" class="mudo">Ninguém encontrado.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
  <Fonte fonte={{ nome: "Portal da Transparência – Servidores (SIAPE)", url: m.fontes.ocupantes?.url, data: m.fontes.ocupantes?.data }} rotuloData="Dados de" />
  <Fonte fonte={m.fontes.partidos} rotuloData="" />
</section>

{#if historico.length}
  <section class="cartao" aria-labelledby="t-hist">
    <div class="cab-secao">
      <h2 id="t-hist">Quem já saiu (ministros e secretários, desde 2023)</h2>
      <BotaoCsv arquivo={`${m.id}-historico.csv`} {colunas} linhas={paraCsv(historico)} />
    </div>
    <div class="tabela-rolagem">
      <table>
        <thead><tr><th>Nome</th><th>Cargo</th><th>Partido</th><th>Período</th></tr></thead>
        <tbody>
          {#each historico as o, i (i)}
            <tr>
              <td>{o.nome}</td>
              <td>{o.cargo} <span class="mudo pequeno">{o.uorg ?? ""}</span></td>
              <td title={partidoDetalhe(o.partido)} class:mudo={!o.partido}>{partidoSigla(o.partido) ?? "sem candidatura"}</td>
              <td class="nowrap">{fmtData(o.de) ?? "?"} – ~{mesAno(o.ate)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="mudo pequeno">A saída é aproximada: é o primeiro mês em que a pessoa já não aparece no cadastro mensal do SIAPE.</p>
  </section>
{/if}

<style>
  .cartao + .cartao { margin-top: 16px; }
  .linha-tempo { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
  .linha-tempo li { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; padding: 6px 0 6px 14px; border-left: 3px solid var(--linha); }
  .linha-tempo li.atual { border-left-color: var(--marca); }
  .pequeno { font-size: 0.8rem; }
  td .pequeno { display: block; }
  .nowrap { white-space: nowrap; }
</style>
