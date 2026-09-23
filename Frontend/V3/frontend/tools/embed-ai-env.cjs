const fs = require("node:fs");
const path = require("node:path");

module.exports = async function embedAiEnv(context) {
  if (process.env.THINFILM_EMBED_AI_ENV !== "1") return;
  const source = path.resolve(__dirname, "../../backend/.env");
  if (!fs.existsSync(source)) throw new Error("缺少 backend/.env，已停止临时 AI 打包。");
  const contents = fs.readFileSync(source, "utf8");
  if (!/^\s*SILICONFLOW_API_KEY\s*=\s*\S+/m.test(contents)) {
    throw new Error("backend/.env 中未填写 SILICONFLOW_API_KEY，已停止临时 AI 打包。");
  }
  const destination = path.join(context.appOutDir, "resources", "backend", ".env");
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(source, destination);
  console.log("已复制 backend/.env 到本次安装包；试用结束后请作废该 API Key。");
};
