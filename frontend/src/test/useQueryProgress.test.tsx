import { act, renderHook } from "@testing-library/react";
import i18n from "../i18n";
import { useQueryProgress } from "../shared/hooks/useQueryProgress";
import { createResultViewModel } from "./mockViewModel";

describe("useQueryProgress", () => {
  beforeEach(async () => {
    await act(async () => {
      await i18n.changeLanguage("en-US");
    });
    vi.useFakeTimers();
  });

  afterEach(async () => {
    vi.useRealTimers();
    await act(async () => {
      await i18n.changeLanguage("zh-CN");
    });
  });

  it("keeps stepper moving forward and completes at 100%", () => {
    const { result, rerender } = renderHook(
      (props: Parameters<typeof useQueryProgress>[0]) => useQueryProgress(props),
      {
        initialProps: {
          isPending: true,
          isError: false,
          resultVm: null,
          requestKind: "text" as const,
        },
      },
    );

    expect(result.current.steps[0].state).toBe("current");

    act(() => {
      vi.advanceTimersByTime(2500);
    });

    expect(result.current.steps[0].state).toBe("complete");
    expect(result.current.steps[1].state).not.toBe("upcoming");

    act(() => {
      rerender({
        isPending: false,
        isError: false,
        resultVm: createResultViewModel(),
        requestKind: "text" as const,
      });
    });

    expect(result.current.progress).toBe(100);
    expect(result.current.title).toBe("Query complete");
    expect(result.current.steps.every((step) => step.state === "complete")).toBe(true);
  });

  it("shows a paused state after the active query is interrupted", () => {
    const { result, rerender } = renderHook(
      (props: Parameters<typeof useQueryProgress>[0]) => useQueryProgress(props),
      {
        initialProps: {
          isPending: true,
          isError: false,
          isPaused: false,
          resultVm: null,
          requestKind: "text" as const,
        },
      },
    );

    act(() => {
      vi.advanceTimersByTime(1400);
    });

    act(() => {
      rerender({
        isPending: false,
        isError: false,
        isPaused: true,
        resultVm: null,
        requestKind: "text" as const,
      });
    });

    expect(result.current.title).toBe("Query paused");
    expect(result.current.tone).toBe("paused");
    expect(result.current.visible).toBe(true);
  });
});
