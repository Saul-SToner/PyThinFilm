import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const srcPath = path.resolve(__dirname, '../data/case_registry.json');
const dstPath = path.resolve(__dirname, '../public/data/case_registry.json');

try {
  const dstDir = path.dirname(dstPath);
  if (!fs.existsSync(dstDir)) {
    fs.mkdirSync(dstDir, { recursive: true });
  }

  const content = fs.readFileSync(srcPath, 'utf-8');
  fs.writeFileSync(dstPath, content, 'utf-8');
  console.log(`[sync-registry] Successfully synced ${srcPath} -> ${dstPath}`);
} catch (err) {
  console.error('[sync-registry] Error syncing case registry:', err);
  process.exit(1);
}
