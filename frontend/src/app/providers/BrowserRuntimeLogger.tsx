import { useEffect } from "react";
import { postClientLogEvent } from "../../shared/api";

const emittedBrowserErrors = new Set<string>();

function emitOnce(signature: string, payload: {
  type: string;
  message: string;
  level?: string;
  payload?: Record<string, unknown>;
}) {
  if (!signature || emittedBrowserErrors.has(signature)) {
    return;
  }
  emittedBrowserErrors.add(signature);
  void postClientLogEvent(payload).catch(() => undefined);
}

export default function BrowserRuntimeLogger() {
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      const message = event.message || "Unhandled browser error";
      const signature = [
        "error",
        message,
        event.filename || "",
        String(event.lineno || 0),
        String(event.colno || 0),
      ].join("|");
      emitOnce(signature, {
        type: "frontend.error",
        message: "Frontend runtime error captured.",
        level: "error",
        payload: {
          message,
          filename: event.filename || "",
          lineno: event.lineno || 0,
          colno: event.colno || 0,
          stack: event.error instanceof Error ? event.error.stack || "" : "",
          path: window.location.pathname,
        },
      });
    };

    const handleRejection = (event: PromiseRejectionEvent) => {
      const reason =
        event.reason instanceof Error
          ? event.reason.message
          : typeof event.reason === "string"
            ? event.reason
            : JSON.stringify(event.reason ?? {});
      const signature = ["rejection", reason].join("|");
      emitOnce(signature, {
        type: "frontend.unhandled_rejection",
        message: "Frontend unhandled promise rejection captured.",
        level: "error",
        payload: {
          reason,
          stack: event.reason instanceof Error ? event.reason.stack || "" : "",
          path: window.location.pathname,
        },
      });
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);
    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, []);

  return null;
}
