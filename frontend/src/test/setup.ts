import "@testing-library/jest-dom/vitest";

function shouldSilenceI18nPromo(args: unknown[]) {
  const first = args[0];
  return typeof first === "string" && first.includes("i18next is made possible by our own product, Locize");
}

const originalInfo = console.info.bind(console);
const originalLog = console.log.bind(console);
const originalWarn = console.warn.bind(console);

vi.spyOn(console, "info").mockImplementation((...args: unknown[]) => {
  if (shouldSilenceI18nPromo(args)) {
    return;
  }
  originalInfo(...args);
});

vi.spyOn(console, "log").mockImplementation((...args: unknown[]) => {
  if (shouldSilenceI18nPromo(args)) {
    return;
  }
  originalLog(...args);
});

vi.spyOn(console, "warn").mockImplementation((...args: unknown[]) => {
  if (shouldSilenceI18nPromo(args)) {
    return;
  }
  originalWarn(...args);
});

await import("../i18n");
