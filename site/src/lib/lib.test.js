import { test } from "node:test";
import assert from "node:assert/strict";
import { brlCompacto, pct, capitalizar, rotuloCargo, normalizar } from "./formato.js";
import { paraCsv } from "./csv.js";
import { indexar, caminho, cargoDirigente, buscar } from "./estrutura.js";
import { linhas, agrupar, acumuladoMensal } from "./orcamento.js";

const nb = (s) => s.replace(/ /g, " ");

test("formatação", () => {
  assert.equal(nb(brlCompacto(15_004_000_000)), "R$ 15,0 bi");
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
