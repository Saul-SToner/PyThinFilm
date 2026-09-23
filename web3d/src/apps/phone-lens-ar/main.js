import { EngineeringCaseApp } from "../shared/EngineeringCaseApp.js";
import { getEngineeringCaseConfig } from "../shared/engineeringCaseConfigs.js";
import { renderEngineeringShell } from "../shared/engineeringShell.js";
import "../shared/engineeringApp.css";

const root = document.querySelector("#engineering-app");
renderEngineeringShell(root);
const app = new EngineeringCaseApp(root, getEngineeringCaseConfig("app_phone_lens_ar"));
app.init();
