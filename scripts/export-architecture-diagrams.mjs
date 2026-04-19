import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "..");

const sourcePath = path.join(repoRoot, "documentation", "ARCHITECTURE_DIAGRAM.md");
const outputDir = path.join(repoRoot, "documentation", "generated");
const htmlPath = path.join(outputDir, "ARCHITECTURE_DIAGRAM.rendered.html");
const pdfPath = path.join(repoRoot, "documentation", "ARCHITECTURE_DIAGRAM.pdf");
const htmlOnly = process.argv.includes("--html-only");

const chromeCandidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function extractDiagrams(markdown) {
  const diagrams = [];
  const lines = markdown.split(/\r?\n/);
  let currentHeading = "Architecture Diagram";
  let inMermaidBlock = false;
  let mermaidLines = [];

  for (const line of lines) {
    const headingMatch = line.match(/^##\s+(.*)$/);
    if (!inMermaidBlock && headingMatch) {
      currentHeading = headingMatch[1].trim();
      continue;
    }

    if (!inMermaidBlock && line.trim() === "```mermaid") {
      inMermaidBlock = true;
      mermaidLines = [];
      continue;
    }

    if (inMermaidBlock && line.trim() === "```") {
      diagrams.push({
        title: currentHeading,
        code: mermaidLines.join("\n").trim(),
      });
      inMermaidBlock = false;
      mermaidLines = [];
      continue;
    }

    if (inMermaidBlock) {
      mermaidLines.push(line);
    }
  }

  return diagrams;
}

function buildHtml(diagrams, mermaidScriptUrl) {
  const diagramSections = diagrams
    .map(
      (diagram, index) => `
        <section class="diagram-page${index === diagrams.length - 1 ? " diagram-page-last" : ""}">
          <header class="diagram-header">
            <p class="diagram-kicker">Talenti Architecture Views</p>
            <h2>${escapeHtml(diagram.title)}</h2>
          </header>
          <pre class="mermaid">${escapeHtml(diagram.code)}</pre>
        </section>
      `,
    )
    .join("\n");

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Talenti Architecture Diagrams</title>
    <style>
      :root {
        color-scheme: light;
        font-family: "Segoe UI", Arial, sans-serif;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        background: #f4f7fb;
        color: #10233b;
      }

      main {
        width: 100%;
        max-width: 1280px;
        margin: 0 auto;
        padding: 24px;
      }

      .diagram-page {
        min-height: 10in;
        padding: 28px;
        margin: 0 0 24px;
        background: #ffffff;
        border: 1px solid #d6dfeb;
        border-radius: 18px;
        box-shadow: 0 20px 60px rgba(16, 35, 59, 0.08);
        break-after: page;
      }

      .diagram-page-last {
        break-after: auto;
      }

      .diagram-header {
        margin-bottom: 20px;
      }

      .diagram-kicker {
        margin: 0 0 8px;
        color: #4c6b8a;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      h2 {
        margin: 0;
        font-size: 28px;
        line-height: 1.2;
      }

      .mermaid {
        display: block;
        width: 100%;
        margin: 0;
        background: #fbfdff;
        border: 1px solid #d6dfeb;
        border-radius: 14px;
        overflow: hidden;
      }

      .mermaid[data-processed="true"] {
        padding: 16px;
      }

      .mermaid svg {
        display: block;
        width: 100% !important;
        height: auto !important;
        max-height: 9.1in;
      }

      @page {
        size: A4 landscape;
        margin: 0.35in;
      }

      @media print {
        body {
          background: #ffffff;
        }

        main {
          max-width: none;
          padding: 0;
        }

        .diagram-page {
          margin: 0;
          border: 0;
          border-radius: 0;
          box-shadow: none;
        }
      }
    </style>
  </head>
  <body>
    <main>
${diagramSections}
    </main>
    <script src="${mermaidScriptUrl}"></script>
    <script>
      const config = {
        startOnLoad: false,
        securityLevel: "loose",
        theme: "neutral",
        flowchart: {
          htmlLabels: true,
          useMaxWidth: true,
        },
      };

      async function renderMermaid() {
        mermaid.initialize(config);
        await mermaid.run({ querySelector: ".mermaid" });
        document.body.setAttribute("data-rendered", "true");
      }

      renderMermaid().catch((error) => {
        console.error(error);
        document.body.setAttribute("data-rendered", "error");
      });
    </script>
  </body>
</html>
`;
}

async function findChrome() {
  for (const candidate of chromeCandidates) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      continue;
    }
  }

  throw new Error(
    "Unable to find Chrome or Edge. Install one of them, or update chromeCandidates in scripts/export-architecture-diagrams.mjs.",
  );
}

async function renderPdf(htmlUrl) {
  const chromePath = await findChrome();
  const args = [
    "--headless=new",
    "--disable-gpu",
    "--allow-file-access-from-files",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=15000",
    "--print-to-pdf-no-header",
    `--print-to-pdf=${pdfPath}`,
    htmlUrl,
  ];

  await execFileAsync(chromePath, args, {
    windowsHide: true,
    maxBuffer: 10 * 1024 * 1024,
  });
}

async function main() {
  const markdown = await fs.readFile(sourcePath, "utf8");
  const diagrams = extractDiagrams(markdown);

  if (diagrams.length === 0) {
    throw new Error(`No Mermaid blocks found in ${sourcePath}`);
  }

  await fs.mkdir(outputDir, { recursive: true });

  const mermaidScriptPath = path.join(repoRoot, "node_modules", "mermaid", "dist", "mermaid.min.js");
  await fs.access(mermaidScriptPath);

  const html = buildHtml(diagrams, pathToFileURL(mermaidScriptPath).href);
  await fs.writeFile(htmlPath, html, "utf8");

  if (!htmlOnly) {
    await renderPdf(pathToFileURL(htmlPath).href);
  }

  const relativeHtmlPath = path.relative(repoRoot, htmlPath);
  console.log(`Rendered ${diagrams.length} Mermaid diagrams to ${relativeHtmlPath}`);

  if (!htmlOnly) {
    const relativePdfPath = path.relative(repoRoot, pdfPath);
    console.log(`Updated ${relativePdfPath}`);
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
