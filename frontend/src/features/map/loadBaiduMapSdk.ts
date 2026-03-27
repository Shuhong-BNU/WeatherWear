const BAIDU_READY_TIMEOUT_MS = 8000;
const BAIDU_READY_CALLBACK = "__weatherwearBaiduSdkReady__";

let baiduScriptPromise: Promise<void> | null = null;

declare global {
  interface Window {
    BMapGL?: any;
    __weatherwearBaiduSdkReady__?: () => void;
  }
}

interface LoadCallbacks {
  onScriptRequested?: () => void;
  onScriptLoaded?: () => void;
}

function cleanupBaiduScriptTag() {
  const script = document.querySelector<HTMLScriptElement>('script[data-weatherwear-baidu="1"]');
  if (script) {
    script.remove();
  }
}

function clearReadyCallback() {
  try {
    delete window.__weatherwearBaiduSdkReady__;
  } catch {
    window.__weatherwearBaiduSdkReady__ = undefined;
  }
}

export function loadBaiduMapSdk(ak: string, callbacks?: LoadCallbacks): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("window_unavailable"));
  }
  if (!ak.trim()) {
    return Promise.reject(new Error("missing_baidu_ak"));
  }

  callbacks?.onScriptRequested?.();

  if (window.BMapGL) {
    callbacks?.onScriptLoaded?.();
    return Promise.resolve();
  }

  if (baiduScriptPromise) {
    return baiduScriptPromise;
  }

  baiduScriptPromise = new Promise<void>((resolve, reject) => {
    let settled = false;
    const finishResolve = () => {
      if (settled) {
        return;
      }
      settled = true;
      callbacks?.onScriptLoaded?.();
      clearReadyCallback();
      resolve();
    };
    const finishReject = (error: Error) => {
      if (settled) {
        return;
      }
      settled = true;
      clearReadyCallback();
      cleanupBaiduScriptTag();
      reject(error);
    };

    const timeout = window.setTimeout(() => {
      finishReject(new Error("baidu_sdk_timeout"));
    }, BAIDU_READY_TIMEOUT_MS);

    const clearTimerAndResolve = () => {
      window.clearTimeout(timeout);
      if (!window.BMapGL) {
        finishReject(new Error("baidu_runtime_missing"));
        return;
      }
      finishResolve();
    };

    window.__weatherwearBaiduSdkReady__ = () => {
      clearTimerAndResolve();
    };

    cleanupBaiduScriptTag();

    const script = document.createElement("script");
    script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${encodeURIComponent(ak)}&callback=${BAIDU_READY_CALLBACK}`;
    script.async = false;
    script.defer = false;
    script.dataset.weatherwearBaidu = "1";
    script.addEventListener(
      "load",
      () => {
        if (window.BMapGL) {
          clearTimerAndResolve();
        }
      },
      { once: true },
    );
    script.addEventListener(
      "error",
      () => {
        window.clearTimeout(timeout);
        finishReject(new Error("baidu_sdk_failed"));
      },
      { once: true },
    );
    document.head.appendChild(script);
  }).catch((error) => {
    baiduScriptPromise = null;
    throw error;
  });

  return baiduScriptPromise;
}
