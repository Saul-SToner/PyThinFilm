import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("thinfilmDesktop", {
  apiBaseUrl: "http://127.0.0.1:8122",
});
