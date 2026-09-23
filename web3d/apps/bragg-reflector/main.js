import { EngineeringCaseApp } from "../../src/apps/shared/EngineeringCaseApp.js";
import { getEngineeringCaseConfig } from "../../src/apps/shared/engineeringCaseConfigs.js";
import { renderEngineeringShell } from "../../src/apps/shared/engineeringShell.js";
import { GuidedTeachingController } from "../../src/teaching/GuidedTeachingController.js";
import { BraggVisualStory } from "./BraggVisualStory.js";
import "../../src/apps/shared/engineeringApp.css";
import "../../src/teaching/guidedTeaching.css";
import "./braggVisualStory.css";

const CASE_ID = "bragg_reflector";
async function startBraggReflectorApp() {
  const root = document.querySelector("#engineering-app");
  renderEngineeringShell(root);
  const app = new EngineeringCaseApp(root, getEngineeringCaseConfig(CASE_ID));
  await app.init();
  const teaching = await GuidedTeachingController.create(root, app, CASE_ID);
  teaching.init();
  const visualStory = new BraggVisualStory(root, app, teaching);
  visualStory.init();
  window.addEventListener("pagehide", () => visualStory.dispose(), { once: true });
}

startBraggReflectorApp();
