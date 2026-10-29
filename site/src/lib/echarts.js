// Só os módulos do ECharts que o painel usa (tree-shaking). Importado sob demanda.
import { use, init } from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent, MarkLineComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";

use([LineChart, GridComponent, TooltipComponent, MarkLineComponent, SVGRenderer]);

export { init };
