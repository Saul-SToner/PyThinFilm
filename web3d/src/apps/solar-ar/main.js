import "./solarAr.css";
import { SolarArApp } from "./SolarArApp.js";

document.addEventListener("DOMContentLoaded", async () => {
  const root = document.querySelector("#solar-ar-app");
  const app = new SolarArApp(root);
  await app.init();
});
