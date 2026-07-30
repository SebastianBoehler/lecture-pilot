import type { CanvasComponentData, CanvasComponentFrame } from "./types";
import { useI18n } from "./i18n";
import { formatChartNumber } from "./canvasChartData";

type ChartDataTableProps = {
  data: CanvasComponentData;
  frame: CanvasComponentFrame;
};

export function ChartDataTable({ data, frame }: ChartDataTableProps) {
  const { t } = useI18n();
  return (
    <details className="canvas-chart-data">
      <summary>{t("component.chart.data")}</summary>
      {data.chart_type === "scatter" ? (
        <ScatterTable data={data} frame={frame} />
      ) : data.chart_type === "heatmap" ? (
        <HeatmapTable data={data} frame={frame} />
      ) : (
        <SeriesTable data={data} frame={frame} />
      )}
    </details>
  );
}

function SeriesTable({ data, frame }: ChartDataTableProps) {
  const { t } = useI18n();
  return (
    <table>
      <thead>
        <tr>
          <th scope="col">{data.x_label || t("component.chart.category")}</th>
          <th scope="col">{data.y_label || t("component.chart.value")}</th>
        </tr>
      </thead>
      <tbody>
        {data.labels.map((label, index) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            <td>{formatChartNumber(frame.values[index])}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ScatterTable({ data, frame }: ChartDataTableProps) {
  const { t } = useI18n();
  return (
    <table>
      <thead>
        <tr>
          <th scope="col">{t("component.chart.point")}</th>
          <th scope="col">{t("component.chart.series")}</th>
          <th scope="col">{data.x_label}</th>
          <th scope="col">{data.y_label}</th>
        </tr>
      </thead>
      <tbody>
        {(frame.points ?? []).map((point) => (
          <tr key={`${point.label}-${point.x}-${point.y}`}>
            <th scope="row">{point.label}</th>
            <td>{point.series || "—"}</td>
            <td>{formatChartNumber(point.x)}</td>
            <td>{formatChartNumber(point.y)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function HeatmapTable({ data, frame }: ChartDataTableProps) {
  return (
    <table>
      <thead>
        <tr>
          <th scope="col">{data.y_label}</th>
          {data.labels.map((label) => (
            <th key={label} scope="col">
              {label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {(data.row_labels ?? []).map((label, rowIndex) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            {(frame.matrix?.[rowIndex] ?? []).map((value, columnIndex) => (
              <td key={`${label}-${data.labels[columnIndex]}`}>{formatChartNumber(value)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
