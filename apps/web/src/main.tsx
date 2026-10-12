import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";
import "./lesson/learning-evidence.css";
import "./shell/version-update.css";
import { VersionUpdateBoundary } from "./shell/VersionUpdateBoundary";
import { installVitePreloadRecovery } from "./shell/vitePreloadRecovery";

installVitePreloadRecovery(window);

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <VersionUpdateBoundary>
      <App />
    </VersionUpdateBoundary>
  </StrictMode>,
);
