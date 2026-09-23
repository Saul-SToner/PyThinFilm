import { EngineeringCaseApp } from "../../src/apps/shared/EngineeringCaseApp.js";
import { getEngineeringCaseConfig } from "../../src/apps/shared/engineeringCaseConfigs.js";
import { renderEngineeringShell } from "../../src/apps/shared/engineeringShell.js";
import "../../src/apps/shared/engineeringApp.css";

const CASE_ID = "porous_sio2_layer";
const root = document.querySelector("#engineering-app");
renderEngineeringShell(root);
const app = new EngineeringCaseApp(root, getEngineeringCaseConfig(CASE_ID));
app.init();
