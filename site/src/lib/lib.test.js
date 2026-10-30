import { test } from "node:test";
import assert from "node:assert/strict";
import { brlCompacto, pct, capitalizar, rotuloCargo, normalizar } from "./formato.js";
import { paraCsv } from "./csv.js";
import { indexar, caminho, cargoDirigente, buscar } from "./estrutura.js";
import { linhas, agrupar, acumuladoMensal } from "./orcamento.js";

const nb = (s) => s.replace(/ /g, " ");

test("formatação", () => {
  assert.equal(nb(brlCompacto(15_004_000_000)), "R$ 15,0 bi");
  assert.equal(nb(brlCompacto(2_437_700_000_000)), "R$ 2,4 tri");
  assert.equal(nb(brlCompacto(323_400_000)), "R$ 323,4 mi");
  assert.equal(nb(brlCompacto(-1500)), "−R$ 1,5 mil");
  assert.equal(pct(1, 4), "25,0%");
  assert.equal(pct(1, 0), "–");
  assert.equal(capitalizar("MORADIA DIGNA"), "Moradia digna");
  assert.equal(capitalizar("Já formatado"), "Já formatado");
  assert.equal(rotuloCargo("CCE", "1", "17"), "CCE 1.17");
  assert.equal(normalizar("Habitação"), "habitacao");
});

test("CSV para Excel pt-BR", () => {
  const s = paraCsv([{ chave: "a", titulo: "A" }, { chave: "b", titulo: "B" }], [{ a: 'x;"y"', b: 1.5 }]);
  assert.equal(s, '﻿A;B\r\n"x;""y""";1,5\r\n');
});

const m = {
  unidades: [
    { c: "1", p: "", s: "M", n: "Ministério", d: 0 },
    { c: "2", p: "1", s: "SNH", n: "Secretaria Nacional de Habitação", d: 1 },
    { c: "3", p: "2", s: "DPH", n: "Departamento", d: 2 },
  ],
  cargos: { "1": [["MEST", "", "", "Ministro de Estado", 1, "FX"]], "2": [["CCE", "1", "17", "Secretário", 1, "FX"], ["FCE", "2", "13", "Assessor", 3, "DD"], ["FCE", "1", "13", "Coordenador-Geral", 1, "DD"]] },
  ocupantes: [{ pessoa: "a", nome: "Fulana", cargo: "Secretária", unidade: "2", papel: "titular" }],
  politicas: [{ id: "mcmv", nome: "Minha Casa, Minha Vida" }],
  orcamento: null,
};

test("estrutura: caminho, dirigente e busca", () => {
  const idx = indexar(m);
  assert.deepEqual(caminho(idx, "3").map((u) => u.s), ["M", "SNH", "DPH"]);
  assert.equal(cargoDirigente(m.cargos["2"]).rotulo, "CCE 1.17");
  assert.equal(cargoDirigente(m.cargos["1"]).rotulo, "Ministro de Estado");
  assert.deepEqual(buscar(m, "habitacao").map((r) => r.tipo), ["Unidade"]);
  assert.deepEqual(buscar(m, "fulana")[0].rota, ["estrutura", { u: "2" }]);
  assert.equal(buscar(m, "minha casa")[0].tipo, "Política");
});

test("orçamento: agrupar e acumular", () => {
  const orc = {
    colunas: ["uo", "programa", "acao", "dotacao_inicial", "dotacao_atual", "empenhado", "liquidado", "pago", "empenhado_emendas"],
    linhas: [["1", "P1", "A", 10, 10, 5, 4, 3, 0], ["1", "P1", "B", 5, 5, 1, 1, 1, 0], ["2", "P2", "C", 20, 30, 2, 2, 2, 1]],
    mensal: [[1, "P1", 1, 1, 1], [2, "P1", 2, 1, 1], [1, "P2", 5, 0, 0]],
  };
  const g = agrupar(linhas(orc), "programa");
  assert.deepEqual(g.map((x) => [x.codigo, x.dotacao_atual, x.pago]), [["P2", 30, 2], ["P1", 15, 4]]);
  assert.equal(linhas(orc, { uo: "1" }).length, 2);
  assert.deepEqual(acumuladoMensal(orc).map((x) => x.empenhado), [6, 8]);
  assert.deepEqual(acumuladoMensal(orc, { prog: "P1" }).map((x) => x.pago), [1, 2]);
});

import { somarGoverno, execucao, ordenar, atribuirSlots, niveisDirecao, cargosDirecao } from "./governo.js";

test("governo: somas, execução e ordenação com nulos", () => {
  const ms = [
    { id: "a", n_unidades: 10, n_cargos: 5, orcamento: { dotacao_atual: 100, pago: 50 }, orcamento_sem_oe: { dotacao_atual: 80, pago: 40 } },
    { id: "b", n_unidades: 3, n_cargos: 2, orcamento: null, orcamento_sem_oe: null },
  ];
  const t = somarGoverno(ms);
  assert.deepEqual([t.n, t.unidades, t.cargos, t.dotacao, t.dotacao_sem_oe], [2, 13, 7, 100, 80]);
  assert.equal(execucao(ms[0]), 0.5);
  assert.equal(execucao(ms[1]), null);
  assert.deepEqual(ordenar(ms, execucao).map((m) => m.id), ["a", "b"]);
  assert.deepEqual(ordenar(ms, execucao, false).map((m) => m.id), ["a", "b"]);
});

test("comparação: cores estáveis ao remover e adicionar", () => {
  const s1 = atribuirSlots(["a", "b", "c"]);
  assert.deepEqual([...s1.values()], [0, 1, 2]);
  const s2 = atribuirSlots(["a", "c"], s1);
  assert.equal(s2.get("c"), 2);
  const s3 = atribuirSlots(["a", "c", "d"], s2);
  assert.equal(s3.get("d"), 1);
});

test("comparação: níveis de direção", () => {
  const d = [{ cargos_por_nivel: { "CCE 1.17": 2, "FCE 1.13": 4, "CCE 2.13": 9, MEST: 1 } }, { cargos_por_nivel: { "CCE 1.18": 1, "CCE 1.13": 1 } }];
  assert.deepEqual(niveisDirecao(d), [18, 17, 13]);
  assert.equal(cargosDirecao(d[0], 13), 4);
});

import { partidoDetalhe, mesAno, duracao } from "./formato.js";

test("partido e datas", () => {
  assert.equal(partidoDetalhe({ sigla: "PT", ano: 2022, cargo: "Senador", uf: "PI", fonte: "TSE" }), "Partido na candidatura a Senador em 2022 (PI) · TSE");
  assert.match(partidoDetalhe(null), /Sem candidatura/);
  assert.equal(mesAno("2026-08"), "ago/2026");
  assert.equal(duracao(15), "1 ano e 3 meses");
  assert.equal(duracao(1), "1 mês");
  assert.equal(duracao(0), "menos de 1 mês");
});

import { porPartido, rotatividadeGoverno, SEM_CANDIDATURA } from "./governo.js";

test("governo: por partido e rotatividade", () => {
  const ms = [
    { sigla: "A", n_cargos: 10, orcamento_sem_oe: { dotacao_atual: 5 }, ministro: { partido: { sigla: "PT" } },
      rotatividade: { ministros: { mandatos: 2, encerrados: 1, meses_medio: 20 }, secretarios: { mandatos: 4, encerrados: 2, meses_medio: 10 } } },
    { sigla: "B", n_cargos: 5, orcamento_sem_oe: null, ministro: { partido: null },
      rotatividade: { ministros: { mandatos: 1, encerrados: 0, meses_medio: 40 }, secretarios: { mandatos: 0, encerrados: 0, meses_medio: null } } },
    { sigla: "C", n_cargos: 1, ministro: { partido: { sigla: "PT" } }, rotatividade: null },
  ];
  const p = porPartido(ms);
  assert.deepEqual(p.map((x) => [x.sigla, x.n]), [["PT", 2], [SEM_CANDIDATURA, 1]]);
  const r = rotatividadeGoverno(ms);
  assert.equal(r.trocas, 1);
  assert.equal(r.mandatos, 3);
  assert.equal(r.meses_medio, (20 * 2 + 40) / 3);
});

import { porNorma, corrigir, serieAnual } from "./historia.js";

test("história: agrupamento por norma e correção pelo IPCA", () => {
  const ev = [{ id: "a", norma: "mp1", data: "2016-05-12" }, { id: "b", norma: "mp1", data: "2016-05-12" }, { id: "c", norma: "mp2", data: "2019-01-01" }];
  const g = porNorma(ev, { mp1: { numero: "726" } });
  assert.deepEqual(g.map((x) => [x.norma, x.eventos.length]), [["mp2", 1], ["mp1", 2]]);
  assert.equal(g[1].info.numero, "726");
  const ipca = { fatores: { 2014: 2, 2026: 1 } };
  assert.equal(corrigir(10, 2014, ipca), 20);
  assert.equal(corrigir(10, 2020, ipca), 10);
  const linhas = [[2014, 1, 2, 3, 4, 5, 6], [2026, 1, 2, 3, 4, 5, 6]];
  assert.deepEqual(serieAnual(linhas, "pago_sem_oe", { real: true, ipca }), [["2014", 12], ["2026", 6]]);
});
