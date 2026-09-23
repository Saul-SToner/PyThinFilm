import { EvidenceCaseApp } from "../../src/apps/evidence/EvidenceCaseApp.js";
import "../../src/apps/evidence/evidenceApp.css";

const CASE_ID = "tamm_phase_candidates";
const root = document.querySelector("#evidence-app");
const app = new EvidenceCaseApp(root, CASE_ID);
app.init();
