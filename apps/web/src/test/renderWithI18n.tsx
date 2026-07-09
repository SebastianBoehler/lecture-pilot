import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";

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
