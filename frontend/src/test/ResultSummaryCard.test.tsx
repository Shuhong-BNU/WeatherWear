import { render, screen } from "@testing-library/react";
import ResultSummaryCard from "../features/results/ResultSummaryCard";
import { createResultViewModel } from "./mockViewModel";

describe("ResultSummaryCard", () => {
  it("renders headline advice instead of reusing the first time-of-day line", () => {
    const viewModel = createResultViewModel({
      fashion: {
        text: "### 今日建议\n全天偏凉，建议保暖内搭配外套。\n\n### 分时段建议\n- 早晨：只是一条早晨提示。",
        headline_advice: "全天偏凉，建议保暖内搭配外套。",
        time_of_day_advice: "- 早晨：只是一条早晨提示。",
        layering_advice: "- 内层：保暖打底。",
        bottomwear_advice: "",
        shoes_accessories_advice: "",
        notes_advice: "",
        source: "rule_based_fashion",
        used_llm: false,
        error: "",
      },
      hero_summary: {
        ...createResultViewModel().hero_summary,
        one_line_advice: "全天偏凉，建议保暖内搭配外套。",
      },
    });

    render(<ResultSummaryCard resultVm={viewModel} viewMode="user" />);

    expect(screen.getByText("全天偏凉，建议保暖内搭配外套。")).toBeInTheDocument();
    expect(screen.queryByText("- 早晨：只是一条早晨提示。")).not.toBeInTheDocument();
  });

  it("shows the actual target date label instead of a fixed today label", () => {
    const viewModel = createResultViewModel({
      hero_summary: {
        ...createResultViewModel().hero_summary,
        advice_label: "2026-03-27 穿搭建议",
      },
      summary: {
        ...createResultViewModel().summary,
        query_context: {
          ...createResultViewModel().summary.query_context,
          target_date: "2026-03-27",
          forecast_mode: "forecast_day",
        },
      },
      weather: {
        ...createResultViewModel().weather,
        forecast_date: "2026-03-27",
        forecast_mode: "forecast_day",
        observed_at_local: "2026-03-27 12:00",
      },
    });

    render(<ResultSummaryCard resultVm={viewModel} viewMode="user" />);

    expect(screen.getByText("2026-03-27 穿搭建议")).toBeInTheDocument();
    expect(screen.getByText("目标日期：2026-03-27")).toBeInTheDocument();
  });

  it("shows both weather time and local time chips", () => {
    const viewModel = createResultViewModel({
      weather: {
        ...createResultViewModel().weather,
        observed_at_local: "2026-03-24 20:00",
        city_local_time: "2026-03-24 20:05",
      },
    });

    render(<ResultSummaryCard resultVm={viewModel} viewMode="user" />);

    expect(screen.getByText("天气时间：2026-03-24 20:00")).toBeInTheDocument();
    expect(screen.getByText("当地时间：2026-03-24 20:05")).toBeInTheDocument();
  });

  it("renders degree celsius without mojibake", () => {
    const viewModel = createResultViewModel({
      weather: {
        ...createResultViewModel().weather,
        daily_range_text: "-10.3°C ~ 0.2°C",
      },
    });

    render(<ResultSummaryCard resultVm={viewModel} viewMode="user" />);

    expect(screen.getByText("温度范围：-10.3°C ~ 0.2°C")).toBeInTheDocument();
    expect(screen.queryByText(/掳C/)).not.toBeInTheDocument();
  });
});
