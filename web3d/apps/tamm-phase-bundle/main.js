import { EngineeringCaseApp } from "../../src/apps/shared/EngineeringCaseApp.js";
import { getEngineeringCaseConfig } from "../../src/apps/shared/engineeringCaseConfigs.js";
import { renderEngineeringShell } from "../../src/apps/shared/engineeringShell.js";
import { GuidedTeachingController } from "../../src/teaching/GuidedTeachingController.js";
import "../../src/apps/shared/engineeringApp.css";
import "../../src/teaching/guidedTeaching.css";

const CASE_ID = "tamm_phase_bundle";
async function startTammPhaseBundleApp() {
  const root = document.querySelector("#engineering-app");
  renderEngineeringShell(root);
  const app = new EngineeringCaseApp(root, getEngineeringCaseConfig(CASE_ID));
  await app.init();
  const teaching = await GuidedTeachingController.create(root, app, CASE_ID);
  teaching.init();
}

startTammPhaseBundleApp();
