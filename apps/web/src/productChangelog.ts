import changelogSource from "./productChangelog.json";
import type { Locale } from "./i18n";

type LocalizedText = Record<Locale, string>;

export type ProductChange = {
  title: LocalizedText;
  description: LocalizedText;
  feedbackDriven?: boolean;
};

export type ProductRelease = {
  version: string;
  date: string;
  title: LocalizedText;
  summary: LocalizedText;
  changes: ProductChange[];
};

type ProductChangelog = {
  repositoryUrl: string;
  releases: ProductRelease[];
};

export const productChangelog = changelogSource as ProductChangelog;

export function releaseUrl(version: string) {
  return `${productChangelog.repositoryUrl}/releases/tag/v${version}`;
}
