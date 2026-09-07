export interface InfoSection {
  id: string;
  title: string;
  paragraphs: string[];
  steps?: string[];
  example?: string;
  detail?: string;
}

export interface InfoArticleContent {
  title: string;
  intro: string;
  sections: InfoSection[];
}
