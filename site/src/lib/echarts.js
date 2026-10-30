// Só os módulos do ECharts que o painel usa (tree-shaking). Importado sob demanda.
import { use, init } from "echarts/core";
import { BarChart, LineChart, TreemapChart } from "echarts/charts";
import { GridComponent, TooltipComponent, MarkLineComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";

use([BarChart, LineChart, TreemapChart, GridComponent, TooltipComponent, MarkLineComponent, SVGRenderer]);

export { init };
