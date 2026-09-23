import { app, BrowserWindow, dialog } from "electron";
import path from "node:path";
import { ChildProcess, execFile, spawn } from "node:child_process";
import http from "node:http";

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL);

function checkBackendPort(): Promise<void> {
  if (!app.isPackaged || process.platform !== "win32") return Promise.resolve();
  const script = path.join(process.resourcesPath, "port-preflight.ps1");
  return new Promise((resolve, reject) => {
    execFile("powershell.exe", ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script, "-Port", "8122"],
      { windowsHide: true, timeout: 15000 }, (error, stdout, stderr) => {
        if (error) reject(new Error((stderr || stdout || error.message).trim()));
        else resolve();
      });
  });
}

function startBackend(): void {
  if (isDev) {
    return;
  }

  const repoRoot = path.resolve(__dirname, "..", "..");
  const backendDir = path.join(repoRoot, "backend");
  const pythonCommand = process.platform === "win32" ? "python" : "python3";
  const appRoot = app.isPackaged ? process.resourcesPath : repoRoot;
  const outputsDir = app.isPackaged ? path.join(app.getPath("userData"), "outputs") : path.join(backendDir, "outputs");
  const materialsCsv = app.isPackaged
    ? path.join(process.resourcesPath, "materials", "app_materials_metadata.csv")
    : path.join(repoRoot, "frontend", "src", "assets", "materials", "app_materials_metadata.csv");
  const backendCommand =
    app.isPackaged && process.platform === "win32"
      ? path.join(process.resourcesPath, "backend", "thinfilm-backend.exe")
      : pythonCommand;
  const backendArgs = app.isPackaged && process.platform === "win32" ? [] : ["run.py"];
  const backendCwd = app.isPackaged && process.platform === "win32" ? path.dirname(backendCommand) : backendDir;

  backendProcess = spawn(backendCommand, backendArgs, {
    cwd: backendCwd,
    env: {
      ...process.env,
      THINFILM_APP_ROOT: appRoot,
      THINFILM_OUTPUT_DIR: outputsDir,
      THINFILM_MATERIALS_METADATA_CSV: materialsCsv,
      THINFILM_NODE_EXECUTABLE: process.execPath,
      THINFILM_TMMCORE_BRIDGE: path.join(process.resourcesPath, "tmmcore", "tmmcore_bridge.mjs"),
      THINFILM_PYTHINFILM_ROOT: app.isPackaged ? backendCwd : path.resolve(repoRoot, "..", ".."),
      THINFILM_OPTILAND_ROOT: app.isPackaged ? path.join(backendCwd, "optiland") : path.resolve(repoRoot, "..", "..", "optiland"),
      THINFILM_OPTILAND_PYTHON: backendCommand,
    },
    windowsHide: true,
    stdio: "ignore",
  });
}

function waitForBackend(timeoutMs = 120000): Promise<boolean> {
  const startedAt = Date.now();

  return new Promise((resolve) => {
    const check = () => {
      const request = http.get("http://127.0.0.1:8122/health", (response) => {
        response.resume();
        if (response.statusCode === 200) {
          resolve(true);
          return;
        }
        retry();
      });

      request.on("error", retry);
      request.setTimeout(1000, () => {
        request.destroy();
        retry();
      });
    };

    const retry = () => {
      if (Date.now() - startedAt >= timeoutMs) {
        resolve(false);
        return;
      }
      setTimeout(check, 400);
    };

    check();
  });
}

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1040,
    minHeight: 680,
    title: "PythonFilm",
    backgroundColor: "#f8fafc",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev && process.env.VITE_DEV_SERVER_URL) {
    await mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    await mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

app.whenReady().then(async () => {
  try {
    await checkBackendPort();
    startBackend();
    if (!(await waitForBackend())) throw new Error("PythonFilm 后端未能在 120 秒内启动。请检查端口 8122 和安装文件。 ");
  } catch (error) {
    dialog.showErrorBox("PythonFilm 无法启动", error instanceof Error ? error.message : String(error));
    app.quit();
    return;
  }
  await createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      void createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});
