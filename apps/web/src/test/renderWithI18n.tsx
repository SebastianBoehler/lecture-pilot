import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

import { I18nProvider, type Locale } from "../i18n";

type I18nRenderOptions = RenderOptions & {
  locale?: Locale;
};

export function renderWithI18n(
  ui: ReactElement,
  { locale = "en", ...options }: I18nRenderOptions = {},
) {
  return render(
    <I18nProvider locale={locale} setLocale={() => undefined}>
      {ui}
    </I18nProvider>,
    options,
  );
}

/** `wrapper` for renderHook when a hook reads translations. */
export function I18nWrapper({ children }: { children: ReactNode }) {
  return (
    <I18nProvider locale="en" setLocale={() => undefined}>
      {children}
    </I18nProvider>
  );
}
