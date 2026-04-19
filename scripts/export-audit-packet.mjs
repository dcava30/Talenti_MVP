import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";

import { marked } from "marked";

const execFileAsync = promisify(execFile);

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "..");

const outputDir = path.join(repoRoot, "documentation", "generated");
const htmlPath = path.join(outputDir, "AUDIT_PACKET_AS_BUILT.rendered.html");
const pdfPath = path.join(repoRoot, "documentation", "AUDIT_PACKET_AS_BUILT.pdf");
const htmlOnly = process.argv.includes("--html-only");

const chromeCandidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

const sourceDocs = [
  {
    id: "architecture-overview",
    title: "Platform Architecture Overview",
    path: "documentation/ARCHITECTURE_OVERVIEW.md",
    purpose:
      "Primary audit-ready architecture reference describing the system as built, including controls, deployment design, evidence, risks, and gap register items.",
  },
  {
    id: "architecture-diagrams",
    title: "Architecture Diagrams",
    path: "documentation/ARCHITECTURE_DIAGRAM.md",
    purpose:
      "Rendered visual appendix covering system design, runtime topology, environment layout, and the delivery and promotion model.",
  },
  {
    id: "release-pipeline",
    title: "Release Pipeline",
    path: "documentation/RELEASE_PIPELINE.md",
    purpose:
      "Detailed CI/CD control reference for branching, PR quality gates, release manifests, promotion rules, artifact integrity, and rollback mechanics.",
  },
  {
    id: "deployment-dev",
    title: "Deployment Runbook",
    path: "documentation/DEPLOYMENT_DEV_V2.md",
    purpose:
      "Hands-on deployment topology and environment configuration reference for the DEV estate and promotion-aligned release candidate flow.",
  },
  {
    id: "monitoring",
    title: "Monitoring and Observability",
    path: "documentation/MONITORING.md",
    purpose:
      "Operational monitoring baseline covering health, alerting, logs, troubleshooting, and incident support expectations.",
  },
  {
    id: "api-reference",
    title: "API Reference",
    path: "documentation/API_REFERENCE.md",
    purpose:
      "Endpoint inventory for auditors who need to inspect exposed capabilities, authentication boundaries, audit-log endpoints, and platform surface area.",
  },
  {
    id: "database-schema",
    title: "Database Schema",
    path: "documentation/DATABASE_SCHEMA.md",
    purpose:
      "Core data architecture reference covering entity relationships, compliance-related records, access control notes, retention flows, and audit logging.",
  },
  {
    id: "architecture-decisions",
    title: "Architecture Decisions",
    path: "documentation/ARCHITECTURE_DECISIONS.md",
    purpose:
      "ADR history preserving the rationale behind the core structural choices reflected in the implemented platform.",
  },
  {
    id: "frontend-guide",
    title: "Frontend Architecture Guide",
    path: "documentation/FRONTEND_GUIDE.md",
    purpose:
      "Frontend implementation and browser-side architecture reference covering routing, state patterns, forms, API integration, and UI structure.",
  },
  {
    id: "user-guide",
    title: "User and Operational Workflows",
    path: "documentation/USER_GUIDE.md",
    purpose:
      "User-facing flows for candidates, recruiters, and administrators, including audit log access, reporting, privacy handling, and support-oriented operations.",
  },
];

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "section";
}

function normalizeMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");

  if (lines[0]?.startsWith("# ")) {
    lines.shift();
  }

  while (lines[0]?.trim() === "") {
    lines.shift();
  }

  const output = [];
  let skippingTableOfContents = false;

  for (const line of lines) {
    if (!skippingTableOfContents && /^##\s+Table of Contents\b/.test(line)) {
      skippingTableOfContents = true;
      continue;
    }

    if (skippingTableOfContents && /^##\s+/.test(line)) {
      skippingTableOfContents = false;
    }

    if (!skippingTableOfContents) {
      output.push(line);
    }
  }

  return output.join("\n").trim();
}

function renderMarkdownBlock(markdown, docId) {
  if (!markdown.trim()) {
    return "";
  }

  let headingCount = 0;
  const renderer = new marked.Renderer();

  renderer.heading = function heading(token) {
    headingCount += 1;
    const level = Math.min(token.depth + 1, 6);
    const text = token.text;
    const id = `${docId}-${slugify(text)}-${headingCount}`;
    return `<h${level} id="${id}">${this.parser.parseInline(token.tokens)}</h${level}>`;
  };

  renderer.code = (token) => {
    const languageClass = token.lang ? ` class="language-${escapeHtml(token.lang)}"` : "";
    return `<pre class="code-block"><code${languageClass}>${escapeHtml(token.text)}</code></pre>`;
  };

  renderer.table = function table(token) {
    const rows = token.rows;
    const headerHtml = token.header
      .map((cell) => `<th>${this.parser.parseInline(cell.tokens)}</th>`)
      .join("");
    const bodyHtml = rows
      .map(
        (row) =>
          `<tr>${row.map((cell) => `<td>${this.parser.parseInline(cell.tokens)}</td>`).join("")}</tr>`,
      )
      .join("");

    return `
      <div class="table-wrap">
        <table>
          <thead><tr>${headerHtml}</tr></thead>
          <tbody>${bodyHtml}</tbody>
        </table>
      </div>
    `;
  };

  return marked.parse(markdown, {
    gfm: true,
    breaks: false,
    renderer,
  });
}

function splitIntoSegments(markdown, defaultHeading) {
  const segments = [];
  const buffer = [];
  const lines = markdown.split("\n");
  let currentHeading = defaultHeading;
  let inRegularFence = false;

  function flushBuffer() {
    const content = buffer.join("\n").trim();
    if (content) {
      segments.push({
        type: "markdown",
        content,
      });
    }
    buffer.length = 0;
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];

    if (!inRegularFence && line.trim() === "```mermaid") {
      flushBuffer();
      const mermaidLines = [];
      index += 1;

      while (index < lines.length && lines[index].trim() !== "```") {
        mermaidLines.push(lines[index]);
        index += 1;
      }

      segments.push({
        type: "mermaid",
        title: currentHeading,
        code: mermaidLines.join("\n").trim(),
      });
      continue;
    }

    const fenceMatch = line.match(/^```([^`]*)$/);
    if (fenceMatch) {
      buffer.push(line);
      if (inRegularFence) {
        inRegularFence = false;
      } else if ((fenceMatch[1] || "").trim() !== "mermaid") {
        inRegularFence = true;
      }
      continue;
    }

    if (!inRegularFence) {
      const headingMatch = line.match(/^##+\s+(.*)$/);
      if (headingMatch) {
        currentHeading = headingMatch[1].trim();
      }
    }

    buffer.push(line);
  }

  flushBuffer();
  return segments;
}

function renderDocumentSection(doc, markdown) {
  const segments = splitIntoSegments(markdown, doc.title);
  const renderedSegments = segments
    .map((segment, index) => {
      if (segment.type === "markdown") {
        return `<section class="document-fragment">${renderMarkdownBlock(segment.content, `${doc.id}-${index}`)}</section>`;
      }

      return `
        <section class="diagram-sheet">
          <div class="diagram-sheet__header">
            <p class="diagram-sheet__eyebrow">${escapeHtml(doc.title)}</p>
            <h2>${escapeHtml(segment.title)}</h2>
            <p class="diagram-sheet__source">${escapeHtml(doc.path)}</p>
          </div>
          <div class="diagram-sheet__canvas">
            <pre class="mermaid">${escapeHtml(segment.code)}</pre>
          </div>
        </section>
      `;
    })
    .join("\n");

  return `
    <article class="source-document" id="${doc.id}">
      <header class="source-document__cover">
        <p class="source-document__kicker">Compiled Source Document</p>
        <h1>${escapeHtml(doc.title)}</h1>
        <p class="source-document__path">${escapeHtml(doc.path)}</p>
        <p class="source-document__purpose">${escapeHtml(doc.purpose)}</p>
      </header>
      ${renderedSegments}
    </article>
  `;
}

function buildHtml(documentSections, documentManifest, generatedDateLabel, mermaidScriptUrl) {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Talenti Audit Packet As-Built</title>
    <style>
      :root {
        color-scheme: light;
        --ink: #10233b;
        --muted: #5a7187;
        --line: #d8e0ea;
        --panel: #ffffff;
        --page: #f3f6fb;
        --accent: #0b6b8f;
        --accent-soft: #dff1f8;
        --mono: "Cascadia Code", "Consolas", monospace;
        --sans: "Segoe UI", "Aptos", Arial, sans-serif;
      }

      * {
        box-sizing: border-box;
      }

      html {
        font-size: 12px;
      }

      body {
        margin: 0;
        background: var(--page);
        color: var(--ink);
        font-family: var(--sans);
        line-height: 1.55;
      }

      .packet {
        width: 100%;
      }

      .page-shell {
        width: 100%;
        max-width: 190mm;
        margin: 0 auto;
        padding: 16mm 0;
      }

      .cover-page {
        min-height: calc(297mm - 28mm);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: linear-gradient(180deg, #ffffff 0%, #edf5fb 100%);
        border: 1px solid var(--line);
        border-radius: 7mm;
        padding: 18mm;
        box-shadow: 0 18px 60px rgba(16, 35, 59, 0.08);
      }

      .cover-page__kicker,
      .source-document__kicker,
      .diagram-sheet__eyebrow {
        margin: 0 0 8px;
        color: var(--accent);
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }

      .cover-page h1,
      .source-document__cover h1 {
        margin: 0 0 10px;
        font-size: 2.4rem;
        line-height: 1.1;
      }

      .cover-page__subtitle {
        max-width: 145mm;
        font-size: 1.1rem;
        color: var(--muted);
      }

      .cover-page__meta {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px 18px;
        margin-top: 16px;
      }

      .meta-card {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid var(--line);
        border-radius: 4mm;
        padding: 10px 12px;
      }

      .meta-card strong {
        display: block;
        margin-bottom: 4px;
      }

      .toc-page,
      .source-document__cover,
      .document-fragment {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 6mm;
        box-shadow: 0 14px 44px rgba(16, 35, 59, 0.06);
      }

      .toc-page {
        break-before: page;
        padding: 16mm;
      }

      .toc-page h2 {
        margin-top: 0;
        font-size: 1.7rem;
      }

      .toc-list {
        margin: 0;
        padding-left: 18px;
      }

      .toc-list li {
        margin: 0 0 10px;
      }

      .toc-list strong {
        display: block;
        color: var(--ink);
      }

      .toc-list span {
        color: var(--muted);
      }

      .source-document {
        break-before: page;
      }

      .source-document__cover {
        padding: 15mm 16mm;
        margin: 0 auto 10mm;
        max-width: 190mm;
      }

      .source-document__path {
        margin: 0 0 10px;
        color: var(--muted);
        font-family: var(--mono);
        font-size: 0.92rem;
      }

      .source-document__purpose {
        margin: 0;
        font-size: 1.02rem;
      }

      .document-fragment {
        margin: 0 auto 10mm;
        max-width: 190mm;
        padding: 10mm 12mm;
      }

      .document-fragment > :first-child {
        margin-top: 0;
      }

      .document-fragment > :last-child {
        margin-bottom: 0;
      }

      h2,
      h3,
      h4,
      h5,
      h6 {
        color: var(--ink);
        line-height: 1.25;
        break-after: avoid-page;
      }

      h2 {
        margin-top: 1.8rem;
        font-size: 1.7rem;
      }

      h3 {
        margin-top: 1.4rem;
        font-size: 1.3rem;
      }

      h4 {
        margin-top: 1.2rem;
        font-size: 1.1rem;
      }

      p,
      ul,
      ol,
      blockquote,
      .table-wrap,
      .code-block {
        break-inside: avoid-page;
      }

      a {
        color: var(--accent);
        text-decoration: none;
      }

      blockquote {
        margin: 1rem 0;
        padding: 0.8rem 1rem;
        border-left: 4px solid var(--accent);
        background: #f7fbfd;
        color: #27455f;
      }

      .table-wrap {
        width: 100%;
        overflow-x: auto;
        margin: 1rem 0;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.92rem;
      }

      th,
      td {
        border: 1px solid var(--line);
        padding: 8px 10px;
        text-align: left;
        vertical-align: top;
      }

      th {
        background: #eef5fb;
      }

      tr {
        break-inside: avoid-page;
      }

      code {
        font-family: var(--mono);
        font-size: 0.92em;
        background: #f1f5f9;
        border-radius: 4px;
        padding: 0.12rem 0.35rem;
      }

      .code-block {
        overflow-x: auto;
        padding: 0.9rem 1rem;
        border: 1px solid var(--line);
        border-radius: 4mm;
        background: #f8fbfe;
      }

      .code-block code {
        background: transparent;
        padding: 0;
        white-space: pre;
      }

      hr {
        border: 0;
        border-top: 1px solid var(--line);
        margin: 1.6rem 0;
      }

      .diagram-sheet {
        page: diagram;
        break-before: page;
        break-after: page;
        break-inside: avoid-page;
        height: calc(210mm - 20mm);
        padding: 9mm 10mm 7mm;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        background: #ffffff;
      }

      .diagram-sheet__header {
        margin-bottom: 6mm;
      }

      .diagram-sheet__header h2 {
        margin: 0 0 4px;
        font-size: 1.55rem;
      }

      .diagram-sheet__source {
        margin: 0;
        color: var(--muted);
        font-family: var(--mono);
        font-size: 0.84rem;
      }

      .diagram-sheet__canvas {
        flex: 1;
        min-width: 0;
        min-height: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 4mm;
        border: 1px solid var(--line);
        border-radius: 4mm;
        background: linear-gradient(180deg, #fafdff 0%, #ffffff 100%);
      }

      .diagram-sheet .mermaid {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        min-width: 0;
        min-height: 0;
        margin: 0;
        overflow: hidden;
      }

      .diagram-sheet .mermaid[data-processed="true"] {
        padding: 0;
      }

      .diagram-sheet .mermaid svg {
        display: block;
        max-width: 100% !important;
        max-height: 100% !important;
        width: auto !important;
        height: auto !important;
      }

      @page {
        size: A4 portrait;
        margin: 10mm;
      }

      @page diagram {
        size: A4 landscape;
        margin: 10mm;
      }

      @media print {
        body {
          background: #ffffff;
        }

        .page-shell {
          max-width: none;
          padding: 0;
        }

        .cover-page,
        .toc-page,
        .source-document__cover,
        .document-fragment {
          box-shadow: none;
        }

        .cover-page,
        .toc-page,
        .source-document__cover,
        .document-fragment {
          border-radius: 0;
        }
      }
    </style>
  </head>
  <body>
    <main class="packet">
      <section class="page-shell">
        <section class="cover-page">
          <div>
            <p class="cover-page__kicker">Talenti Audit Packet</p>
            <h1>As-Built Audit Packet</h1>
            <p class="cover-page__subtitle">
              This consolidated packet compiles the current architecture, deployment, operational, data, API, frontend,
              user workflow, and decision-record documentation into a single auditor-ready PDF. Mermaid diagrams are
              rendered into the document and placed on dedicated pages for print readability.
            </p>
            <div class="cover-page__meta">
              <div class="meta-card">
                <strong>Generated</strong>
                <span>${escapeHtml(generatedDateLabel)}</span>
              </div>
              <div class="meta-card">
                <strong>Document Count</strong>
                <span>${sourceDocs.length} compiled source documents</span>
              </div>
              <div class="meta-card">
                <strong>Rendering Model</strong>
                <span>A4 packet with dedicated rendered diagram pages</span>
              </div>
              <div class="meta-card">
                <strong>Purpose</strong>
                <span>All-in-one as-built audit and architecture evidence packet</span>
              </div>
            </div>
          </div>
          <div>
            <p>
              The packet is assembled from repository documentation and preserves the source language of each
              contributing document while presenting it as a single printable artifact.
            </p>
          </div>
        </section>
      </section>

      <section class="page-shell">
        <section class="toc-page">
          <h2>Included Source Documents</h2>
          <ol class="toc-list">
            ${documentManifest}
          </ol>
        </section>
      </section>

      ${documentSections}
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
        er: {
          useMaxWidth: true,
        },
      };

      function fitDiagramSheets() {
        document.querySelectorAll(".diagram-sheet").forEach((sheet) => {
          const canvas = sheet.querySelector(".diagram-sheet__canvas");
          const mermaidBlock = sheet.querySelector(".mermaid");
          const svg = mermaidBlock?.querySelector("svg");

          if (!canvas || !mermaidBlock || !svg) {
            return;
          }

          const viewBox = svg.viewBox?.baseVal;
          const intrinsicWidth =
            (viewBox && viewBox.width) ||
            Number.parseFloat(svg.getAttribute("width")) ||
            svg.getBoundingClientRect().width;
          const intrinsicHeight =
            (viewBox && viewBox.height) ||
            Number.parseFloat(svg.getAttribute("height")) ||
            svg.getBoundingClientRect().height;
          const availableWidth = canvas.clientWidth;
          const availableHeight = canvas.clientHeight;

          if (!intrinsicWidth || !intrinsicHeight || !availableWidth || !availableHeight) {
            return;
          }

          const scale = Math.min(
            1,
            availableWidth / intrinsicWidth,
            availableHeight / intrinsicHeight,
          );
          const fittedWidth = intrinsicWidth * scale;
          const fittedHeight = intrinsicHeight * scale;

          mermaidBlock.style.width = fittedWidth + "px";
          mermaidBlock.style.height = fittedHeight + "px";
          svg.style.width = fittedWidth + "px";
          svg.style.height = fittedHeight + "px";
          svg.style.maxWidth = "none";
          svg.style.maxHeight = "none";
        });
      }

      async function renderMermaid() {
        mermaid.initialize(config);
        await mermaid.run({ querySelector: ".mermaid" });
        if (document.fonts?.ready) {
          await document.fonts.ready;
        }
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        fitDiagramSheets();
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
    "Unable to find Chrome or Edge. Install one of them, or update chromeCandidates in scripts/export-audit-packet.mjs.",
  );
}

async function renderPdf(htmlUrl) {
  const chromePath = await findChrome();
  const args = [
    "--headless=new",
    "--disable-gpu",
    "--allow-file-access-from-files",
    "--run-all-compositor-stages-before-draw",
    "--virtual-time-budget=60000",
    "--print-to-pdf-no-header",
    "--no-pdf-header-footer",
    `--print-to-pdf=${pdfPath}`,
    htmlUrl,
  ];

  await execFileAsync(chromePath, args, {
    windowsHide: true,
    maxBuffer: 10 * 1024 * 1024,
  });
}

async function main() {
  marked.setOptions({
    gfm: true,
    breaks: false,
  });

  const documents = await Promise.all(
    sourceDocs.map(async (doc) => {
      const absolutePath = path.join(repoRoot, doc.path);
      const content = await fs.readFile(absolutePath, "utf8");
      return {
        ...doc,
        markdown: normalizeMarkdown(content),
      };
    }),
  );

  const documentSections = documents.map((doc) => renderDocumentSection(doc, doc.markdown)).join("\n");
  const documentManifest = documents
    .map(
      (doc) => `
        <li>
          <strong>${escapeHtml(doc.title)}</strong>
          <span>${escapeHtml(doc.path)} — ${escapeHtml(doc.purpose)}</span>
        </li>
      `,
    )
    .join("\n");

  await fs.mkdir(outputDir, { recursive: true });

  const mermaidScriptPath = path.join(repoRoot, "node_modules", "mermaid", "dist", "mermaid.min.js");
  await fs.access(mermaidScriptPath);

  const generatedDateLabel = new Date().toLocaleString("en-AU", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Australia/Sydney",
  });

  const html = buildHtml(
    documentSections,
    documentManifest,
    generatedDateLabel,
    pathToFileURL(mermaidScriptPath).href,
  );

  await fs.writeFile(htmlPath, html, "utf8");

  if (!htmlOnly) {
    await renderPdf(pathToFileURL(htmlPath).href);
  }

  console.log(`Compiled ${documents.length} source documents to ${path.relative(repoRoot, htmlPath)}`);

  if (!htmlOnly) {
    console.log(`Updated ${path.relative(repoRoot, pdfPath)}`);
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
