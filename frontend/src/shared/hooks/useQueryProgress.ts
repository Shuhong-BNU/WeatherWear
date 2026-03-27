import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { QueryProgressState, RequestKind, ResultViewModel } from "../types";

function buildPendingState(
  steps: string[],
  elapsedMs: number,
  t: (key: string) => string,
): QueryProgressState {
  const stepDurationMs = 1200;
  const activeIndex = Math.min(steps.length - 1, Math.floor(elapsedMs / stepDurationMs));
  const progress = Math.min(92, Math.round(14 + (elapsedMs / (steps.length * stepDurationMs)) * 78));
  return {
    visible: true,
    title: t("status.runningTitle"),
    detail: steps[activeIndex],
    tone: "running",
    progress,
    elapsedSeconds: elapsedMs / 1000,
    steps: steps.map((label, index) => ({
      label,
      state: index < activeIndex ? "complete" : index === activeIndex ? "current" : "upcoming",
    })),
  };
}

function buildSettledState(
  kind: RequestKind,
  steps: string[],
  resultVm: ResultViewModel | null,
  hasError: boolean,
  isPaused: boolean,
  elapsedMs: number,
  t: (key: string) => string,
): QueryProgressState {
  if (isPaused) {
    const completedIndex = Math.min(steps.length - 1, 0);
    return {
      visible: true,
      title: t("status.pausedTitle"),
      detail: t("status.pausedDetailFallback"),
      tone: "paused",
      progress: Math.max(10, Math.min(88, Math.round((completedIndex / Math.max(steps.length, 1)) * 100))),
      elapsedSeconds: elapsedMs / 1000,
      steps: steps.map((label, index) => ({
        label,
        state: index < completedIndex ? "complete" : index === completedIndex ? "current" : "upcoming",
      })),
    };
  }

  if (hasError) {
    const lastIndex = Math.min(steps.length - 1, 1);
    return {
      visible: true,
      title: t("status.errorTitle"),
      detail: t("status.errorDetail"),
      tone: "error",
      progress: 100,
      elapsedSeconds: elapsedMs / 1000,
      steps: steps.map((label, index) => ({
        label,
        state: index < lastIndex ? "complete" : index === lastIndex ? "current" : "upcoming",
      })),
    };
  }

  if (!resultVm) {
    return {
      visible: false,
      title: t("status.waitingTitle"),
      detail: "",
      tone: "idle",
      progress: 0,
      elapsedSeconds: 0,
      steps: steps.map((label) => ({ label, state: "upcoming" })),
    };
  }

  if (resultVm.clarification.needed) {
    const completedCount = kind === "map" ? 1 : 2;
    return {
      visible: true,
      title: t("status.clarificationTitle"),
      detail: resultVm.clarification.message || t("status.clarificationDetailFallback"),
      tone: "warning",
      progress: Math.round((completedCount / steps.length) * 100),
      elapsedSeconds: elapsedMs / 1000,
      steps: steps.map((label, index) => ({
        label,
        state: index < completedCount ? "complete" : "upcoming",
      })),
    };
  }

  const isSuccess = Boolean(resultVm.weather.ok && resultVm.fashion.headline_advice);
  return {
    visible: true,
    title: isSuccess ? t("status.successTitle") : t("status.errorTitle"),
    detail: resultVm.summary.message || (isSuccess ? t("status.successDetailFallback") : t("status.partialDetailFallback")),
    tone: isSuccess ? "success" : "error",
    progress: 100,
    elapsedSeconds: elapsedMs / 1000,
    steps: steps.map((label) => ({ label, state: "complete" })),
  };
}

export function useQueryProgress(params: {
  isPending: boolean;
  isError: boolean;
  isPaused?: boolean;
  resultVm: ResultViewModel | null;
  requestKind: RequestKind;
}) {
  const { t } = useTranslation();
  const { isPending, isError, isPaused = false, resultVm, requestKind } = params;
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [lastElapsedMs, setLastElapsedMs] = useState(0);
  const steps = (t(`status.steps.${requestKind}`, { returnObjects: true }) as string[]) || [];

  useEffect(() => {
    if (!isPending) {
      if (startedAt !== null) {
        setLastElapsedMs(Date.now() - startedAt);
        setStartedAt(null);
      }
      return;
    }

    const started = Date.now();
    setStartedAt(started);
    setElapsedMs(0);
    const timer = window.setInterval(() => {
      setElapsedMs(Date.now() - started);
    }, 100);
    return () => window.clearInterval(timer);
  }, [isPending]);

  return useMemo(() => {
    if (isPending) {
      return buildPendingState(steps, elapsedMs, t as (key: string) => string);
    }
    return buildSettledState(requestKind, steps, resultVm, isError, isPaused, lastElapsedMs, t as (key: string) => string);
  }, [elapsedMs, isError, isPaused, isPending, lastElapsedMs, requestKind, resultVm, steps, t]);
}
