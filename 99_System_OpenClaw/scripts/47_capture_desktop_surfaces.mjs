#!/usr/bin/env node

import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { isAbsolute, join, resolve } from "node:path";
import { spawn } from "node:child_process";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const ROOT = resolve(import.meta.dirname, "../..");
const DEFAULT_RUN_ROOT = join(
  ROOT,
  "agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-Z1/acceptance/visual-fidelity/runs",
);
const DEFAULT_BASELINE_ROOT = join(
  ROOT,
  "agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-Z1/acceptance/visual-fidelity/baselines",
);

const surfaces = [
  ["login", "/login"],
  ["setup", "/setup"],
  ["dashboard", "/app/home"],
  ["organizer", "/app/inbox"],
  ["library", "/app/library"],
  ["project", "/app/project/capture-project"],
  ["settings", "/app/settings"],
  ["cloud", "/cloud/tasks"],
];
const viewports = [
  ["desktop", 1440, 900],
  ["mobile", 390, 844],
];

function parseArgs(argv) {
  const values = {
    baseUrl: "http://127.0.0.1:8765",
    output: join(DEFAULT_RUN_ROOT, new Date().toISOString().replaceAll(":", "-").replace(".", "-")),
    baselineRoot: DEFAULT_BASELINE_ROOT,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const name = argv[index];
    const value = argv[index + 1];
    if (name === "--base-url" && value) values.baseUrl = value.replace(/\/$/, "");
    else if (name === "--output" && value) values.output = isAbsolute(value) ? value : resolve(ROOT, value);
    else if (name === "--baseline-root" && value) values.baselineRoot = isAbsolute(value) ? value : resolve(ROOT, value);
    else continue;
    index += 1;
  }
  return values;
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

const delay = milliseconds => new Promise(resolveDelay => setTimeout(resolveDelay, milliseconds));

async function captureScreenshot({ outputPath, profilePath, url, width, height }) {
  const child = spawn(
    CHROME,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--run-all-compositor-stages-before-draw",
      "--virtual-time-budget=2500",
      `--user-data-dir=${profilePath}`,
      `--window-size=${width},${height}`,
      `--screenshot=${outputPath}`,
      url,
    ],
    { detached: true, stdio: "ignore" },
  );
  let stableSize = 0;
  let stablePolls = 0;
  for (let poll = 0; poll < 100; poll += 1) {
    await delay(100);
    const size = existsSync(outputPath) ? statSync(outputPath).size : 0;
    stablePolls = size > 0 && size === stableSize ? stablePolls + 1 : 0;
    stableSize = size;
    if (stablePolls >= 2) break;
  }
  try {
    process.kill(-child.pid, "SIGKILL");
  } catch (error) {
    if (error.code !== "ESRCH") throw error;
  }
  if (stablePolls < 2) {
    throw new Error(`Chrome did not produce a stable screenshot for ${url}`);
  }
}

const options = parseArgs(process.argv.slice(2));
const health = await fetch(`${options.baseUrl}/api/health`).catch(() => null);
if (!health?.ok) {
  throw new Error(`Desktop server is not ready at ${options.baseUrl}; start it before capture.`);
}

mkdirSync(options.output, { recursive: true });
const profileRoot = mkdtempSync(join(tmpdir(), "openclaw-media-capture-"));
const captures = [];
try {
  for (const [surface, route] of surfaces) {
    for (const [viewport, width, height] of viewports) {
      const filename = `${surface}-${viewport}-${width}x${height}.png`;
      const outputPath = join(options.output, filename);
      const url = `${options.baseUrl}${route}`;
      const captureProfile = mkdtempSync(join(profileRoot, `${surface}-${viewport}-`));
      await captureScreenshot({ outputPath, profilePath: captureProfile, url, width, height });
      const screenshotReady = existsSync(outputPath) && statSync(outputPath).size > 0;
      if (!screenshotReady) throw new Error(`Chrome capture failed for ${surface}/${viewport}`);
      captures.push({
        captureId: `CAP-${surface.toUpperCase()}-${viewport.toUpperCase()}`,
        surface,
        route,
        viewport: `${width}x${height}`,
        url,
        file: filename,
        sha256: sha256(outputPath),
        chromeExit: "bounded-after-write",
      });
    }
  }
} finally {
  rmSync(profileRoot, { recursive: true, force: true });
}

const manifest = {
  schemaVersion: 1,
  candidateBaseUrl: options.baseUrl,
  baselineRoot: options.baselineRoot,
  captureCount: captures.length,
  expectedCaptureCount: surfaces.length * viewports.length,
  captures,
};
writeFileSync(join(options.output, "capture-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify({ output: options.output, captureCount: captures.length })}\n`);
