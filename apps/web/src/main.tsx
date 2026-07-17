import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";
import "./version-update.css";
import { VersionUpdateBoundary } from "./VersionUpdateBoundary";
import { installVitePreloadRecovery } from "./vitePreloadRecovery";

installVitePreloadRecovery(window);

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <VersionUpdateBoundary>
      <App />
    </VersionUpdateBoundary>
  </StrictMode>,
);
