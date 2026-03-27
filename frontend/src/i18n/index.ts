import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import enUS from "./messages/en-US";
import zhCN from "./messages/zh-CN";

export const DEFAULT_LOCALE = "zh-CN";

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    lng: DEFAULT_LOCALE,
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: ["zh-CN", "en-US"],
    resources: {
      "zh-CN": { translation: zhCN },
      "en-US": { translation: enUS },
    },
    interpolation: {
      escapeValue: false,
    },
    returnNull: false,
  });
}

export default i18n;
