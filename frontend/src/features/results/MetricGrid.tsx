import type { WeatherMetric } from "../../shared/types";

interface MetricGridProps {
  metrics: WeatherMetric[];
}

export default function MetricGrid(props: MetricGridProps) {
  const metrics = props.metrics.filter((item) =>
    ["temperature_overview", "feels_like", "humidity", "wind"].includes(item.key),
  );

  if (!metrics.length) {
    return null;
  }

  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <div key={metric.key} className="panel p-5">
          <div className="field-label">
            {metric.icon} {metric.label}
          </div>
          {metric.key === "temperature_overview" ? (
            <div className="mt-3">
              <div className="text-3xl font-semibold text-emerald-500">{metric.value}</div>
              <div className="mt-4 flex items-center justify-between text-sm font-medium">
                <div className="flex items-center gap-1 text-blue-600">
                  <span>↓</span>
                  <span>{metric.subvalue_left}</span>
                </div>
                <div className="flex items-center gap-1 text-rose-500">
                  <span>↑</span>
                  <span>{metric.subvalue_right}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-3 text-3xl font-semibold text-slate-900">{metric.value}</div>
          )}
        </div>
      ))}
    </section>
  );
}
