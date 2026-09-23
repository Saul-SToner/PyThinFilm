import { EngineeringCaseApp } from "../../src/apps/shared/EngineeringCaseApp.js";
import { getEngineeringCaseConfig } from "../../src/apps/shared/engineeringCaseConfigs.js";
import { renderEngineeringShell } from "../../src/apps/shared/engineeringShell.js";
import { QuarterWaveTeachingController } from "./QuarterWaveTeachingController.js";
import "../../src/apps/shared/engineeringApp.css";
import "../../src/teaching/guidedTeaching.css";

const CASE_ID = "quarter_wave_single_layer";

async function startQuarterWaveSingleLayerApp() {
  const root = document.querySelector("#engineering-app");
  renderEngineeringShell(root);
  const app = new EngineeringCaseApp(root, getEngineeringCaseConfig(CASE_ID));
  await app.init();
  const teaching = await QuarterWaveTeachingController.create(root, app);
  teaching.init();
}

startQuarterWaveSingleLayerApp();
