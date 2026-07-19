// KisaanRaksha — Round 1 Solution Document generator (Hack4Humanity 2026)
// Condensed edition with flow diagrams + embedded live-demo screenshots.
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun, LevelFormat,
  PageBreak, Packer, Paragraph, ShadingType, Table, TableCell, TableOfContents,
  TableRow, TextRun, WidthType, PageNumber, VerticalAlign,
} = require("docx");
const fs = require("fs");

const GREEN = "1B5E20", MIDGREEN = "2E7D32", DARK = "212121", GRAY = "616161",
  LIGHT = "E8F5E9", AMBER = "E65100", RED = "B71C1C", HDRBG = "1B5E20";

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 140, before: opts.before ?? 0 },
  alignment: opts.align,
  children: [new TextRun({
    text, bold: opts.bold, italics: opts.italics, size: opts.size ?? 22,
    color: opts.color ?? DARK, font: "Calibri",
  })],
});

const rich = (runs, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 140, before: opts.before ?? 0 },
  alignment: opts.align,
  children: runs.map(r => new TextRun({ font: "Calibri", size: r.size ?? 22, ...r })),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 160 },
  children: [new TextRun({ text, bold: true, size: 32, color: GREEN, font: "Calibri" })],
});
const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 120 },
  children: [new TextRun({ text, bold: true, size: 26, color: MIDGREEN, font: "Calibri" })],
});

const bullet = (text, opts = {}) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 },
  children: [new TextRun({ text, size: 22, font: "Calibri", bold: opts.bold, color: opts.color ?? DARK })],
});
const bulletRich = (runs) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 80 },
  children: runs.map(r => new TextRun({ font: "Calibri", size: 22, ...r })),
});

const cellP = (text, { bold = false, color = DARK, size = 20, align } = {}) =>
  new Paragraph({ alignment: align, spacing: { after: 40, before: 40 },
    children: [new TextRun({ text, bold, color, size, font: "Calibri" })] });

function table(headers, rows, colWidths) {
  const total = colWidths.reduce((a, b) => a + b, 0);
  const mkCell = (content, i, header = false) => new TableCell({
    width: { size: colWidths[i], type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    shading: header ? { type: ShadingType.CLEAR, fill: HDRBG } : undefined,
    margins: { top: 50, bottom: 50, left: 110, right: 110 },
    children: [Array.isArray(content) ? content[0] : cellP(String(content), header
      ? { bold: true, color: "FFFFFF", size: 20 } : {})],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: colWidths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => mkCell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => mkCell(c, i)) })),
    ],
  });
}

const stat = (big, label) => new TableCell({
  width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
  shading: { type: ShadingType.CLEAR, fill: LIGHT },
  margins: { top: 130, bottom: 130, left: 120, right: 120 },
  children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
      children: [new TextRun({ text: big, bold: true, size: 40, color: GREEN, font: "Calibri" })] }),
    new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: label, size: 18, color: GRAY, font: "Calibri" })] }),
  ],
});

const spacer = (h = 100) => new Paragraph({ spacing: { after: h }, children: [] });

// ---- flow-diagram building blocks ----
const flowBox = (title, sub, w = 1872, fill = LIGHT, tcolor = GREEN) => new TableCell({
  width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
  shading: { type: ShadingType.CLEAR, fill },
  margins: { top: 90, bottom: 90, left: 70, right: 70 },
  children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 24 },
      children: [new TextRun({ text: title, bold: true, size: 18, color: tcolor, font: "Calibri" })] }),
    new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: sub, size: 15, color: GRAY, font: "Calibri" })] }),
  ],
});
const arrowCell = (w = 360, ch = "→") => new TableCell({
  width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
  margins: { top: 90, bottom: 90 },
  children: [new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: ch, bold: true, size: 26, color: MIDGREEN, font: "Calibri" })] })],
});
const flowRow = (cells, widths) => new Table({
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  columnWidths: widths, rows: [new TableRow({ children: cells })],
});

// ---- image embedding (screenshots) with graceful placeholder ----
function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }
function screenshot(path, maxW = 560, maxH = 430) {
  if (fs.existsSync(path)) {
    const buf = fs.readFileSync(path);
    const { w, h } = pngSize(buf);
    let W = maxW, H = Math.round(maxW * h / w);
    if (H > maxH) { H = maxH; W = Math.round(maxH * w / h); }
    return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
      border: { top: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC" },
                bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC" },
                left: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC" },
                right: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC" } },
      children: [new ImageRun({ data: buf, type: "png", transformation: { width: W, height: H } })] });
  }
  // fallback: labelled placeholder box so the doc still builds
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      margins: { top: 400, bottom: 400, left: 200, right: 200 },
      shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
      children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: `[ screenshot pending: ${path} ]`, italics: true, color: GRAY, size: 20, font: "Calibri" })] })],
    })] })] });
}
const caption = (text) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
  children: [new TextRun({ text, italics: true, size: 17, color: GRAY, font: "Calibri" })] });

const CRIT_IMG = "docs/assets/demo_critical.png";
const CALM_IMG = "docs/assets/demo_calm.png";

const doc = new Document({
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET,
    text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 360, hanging: 200 } } } }] }] },
  styles: { default: { document: { run: { font: "Calibri", size: 22, color: DARK } } } },
  features: { updateFields: true },
  sections: [
    // ---------- COVER ----------
    {
      properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      children: [
        spacer(600),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
          children: [new TextRun({ text: "HACK4HUMANITY 2026  ·  ROUND 1 SOLUTION DOCUMENT", size: 20, color: GRAY, font: "Calibri", bold: true })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
          children: [new TextRun({ text: "Track C — AI for Societal Good  |  IEEE JCTS · IEEE SIGHT · BRAIN Foundation, Pune", size: 18, color: GRAY, font: "Calibri" })] }),
        spacer(900),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
          children: [new TextRun({ text: "KisaanRaksha", bold: true, size: 88, color: GREEN, font: "Calibri" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 },
          children: [new TextRun({ text: "किसानरक्षा", size: 40, color: MIDGREEN, font: "Nirmala UI" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
          children: [new TextRun({ text: "Farmer Financial Distress Early Warning System — Maharashtra", bold: true, size: 30, color: DARK, font: "Calibri" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 700 },
          children: [new TextRun({ text: "An AI agent that predicts farmer financial crisis before it happens, alerts officers proactively, and helps farmers file insurance claims in Marathi over WhatsApp voice.", italics: true, size: 24, color: GRAY, font: "Calibri" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 500 },
          children: [new TextRun({ text: "SDG 2 · Zero Hunger      SDG 3 · Good Health & Well-Being      SDG 10 · Reduced Inequalities", bold: true, size: 22, color: MIDGREEN, font: "Calibri" })] }),
        spacer(700),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
          children: [new TextRun({ text: "Team:  Sahil Karande  ·  Pranav Shripannavar", size: 24, color: DARK, font: "Calibri", bold: true })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
          children: [new TextRun({ text: "GitHub: github.com/sahilkarande0918-cmd/Kisan-Raksha-project", size: 22, color: MIDGREEN, font: "Calibri" })] }),
        new Paragraph({ alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "July 2026", size: 20, color: GRAY, font: "Calibri" })] }),
      ],
    },
    // ---------- BODY ----------
    {
      properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      footers: {
        default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "KisaanRaksha — Hack4Humanity 2026 · Page ", size: 16, color: GRAY, font: "Calibri" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GRAY, font: "Calibri" }),
          ] })] }),
      },
      children: [
        h1("Contents"),
        new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
        new Paragraph({ children: [new PageBreak()] }),

        // ===== 1 PROBLEM =====
        h1("1.  The Problem — A Farmer Dies Every 3 Hours"),
        rich([
          { text: "Maharashtra loses a farmer to suicide every 3 hours. In 2024, " },
          { text: "2,706 farmers died in Vidarbha and Marathwada alone", bold: true, color: RED },
          { text: " — only 1,563 were even deemed eligible for aid. State response is entirely reactive: ex-gratia compensation paid after a death, with zero predictive infrastructure." },
        ]),
        p("Yet the crisis follows a measurable pattern that builds over months:"),
        bullet("A failed monsoon (rainfall deficit) destroys the kharif crop;"),
        bullet("mandi prices fall below MSP just when the farmer must sell;"),
        bullet("the crop-loan repayment deadline arrives with nothing to pay it."),
        rich([
          { text: "Each signal is publicly observable in real time — rainfall archives, Agmarknet prices, satellite crop health, the crop calendar. " },
          { text: "The data to see the crisis coming already exists. Nobody is looking.", bold: true },
        ]),
        rich([
          { text: "North-star beneficiary: ", bold: true, color: MIDGREEN },
          { text: "a 2-acre cotton farmer in Amravati with a ₹1.2 lakh crop loan, a WhatsApp feature phone, and Marathi as his only fluent language. Every design choice traces back to him — voice-first, Marathi-first, no new app, offline-tolerant.", italics: true },
        ]),
        spacer(),

        // ===== 2 SOLUTION =====
        h1("2.  The Solution — Predict · Alert · Assist"),
        bulletRich([{ text: "PREDICT — ", bold: true, color: GREEN }, { text: "a LightGBM model fuses four live signals into a Financial Stress Index (FSI 0–100) per district; FSI > 75 = critical." }]),
        bulletRich([{ text: "ALERT — ", bold: true, color: AMBER }, { text: "on a critical FSI the duty officer gets a WhatsApp alert with the evidence — deficit %, price gap, NDVI — before a crisis, not after a death." }]),
        bulletRich([{ text: "ASSIST — ", bold: true, color: MIDGREEN }, { text: "the farmer sends a Marathi voice note (or text) on WhatsApp — no app, no typing, no English — and receives a grounded reply plus an auto-drafted PMFBY insurance-claim letter." }]),
        spacer(60),
        new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [3120, 3120, 3120],
          rows: [new TableRow({ children: [
            stat("16", "districts covered (Vidarbha + Marathwada)"),
            stat("4", "grounded live signals fused per district"),
            stat("87.9", "FSI in labeled crisis simulation → alert + claim fired on a real phone"),
          ] })] }),
        spacer(),

        // ===== 3 ARCHITECTURE =====
        h1("3.  Architecture — Custom MCP Server, No Bare LLM Calls"),
        p("Every fact the agent states comes from a role-scoped MCP tool grounded in a real dataset — the LLM never answers from training data (track slide 7)."),
        flowRow([
          flowBox("Farmer", "WhatsApp Marathi voice"), arrowCell(),
          flowBox("Agent / LLM", "tool-calling loop (Groq / Gemini)"), arrowCell(),
          flowBox("MCP Server", "FastMCP — 7 role-scoped tools"), arrowCell(),
          flowBox("Grounded Data", "Open-Meteo · Agmarknet · NASA MODIS"),
        ], [1872, 360, 1872, 360, 1872, 360, 2064]),
        spacer(60),
        p("Inbound: Twilio WhatsApp → FastAPI webhook → Whisper large-v3 ASR (Marathi/Hindi auto-detect) → agent. Outbound: Twilio for farmer replies, officer alerts and claim PDFs. A Streamlit choropleth gives officers the live FSI heatmap."),
        h2("3.1  The seven MCP tools"),
        table(["Tool", "One clear job", "Grounding"],
          [
            ["query_weather_signal", "30-day rainfall deficit vs 5-yr baseline", "Open-Meteo ERA5"],
            ["query_mandi_prices", "median mandi price vs MSP", "Agmarknet (data.gov.in)"],
            ["query_ndvi_signal", "satellite crop-health stress", "NASA MODIS MOD13Q1"],
            ["compute_fsi", "fuse 4 signals via LightGBM → FSI 0–100", "trained model, held-out"],
            ["get_farmer_history", "session memory (hashed phone key)", "SQLite — no raw PII"],
            ["send_officer_alert", "WhatsApp alert with evidence", "Twilio"],
            ["draft_pmfby_claim", "Marathi PMFBY letter from evidence", "LLM + FSI evidence"],
          ],
          [2340, 4212, 2808]),
        rich([{ text: "One job per tool (slide 9); every decision traceable through logged calls; tools are auditable and reusable as-is by another team.", size: 22 }], { before: 80 }),

        // ===== 4 METHODOLOGY =====
        h1("4.  Technical Methodology"),
        h2("4.1  Four signals → Financial Stress Index"),
        table(["Signal", "Source (live API)", "What it measures"],
          [
            ["Drought probability", "Open-Meteo ERA5 (keyless)", "30-day rainfall vs 5-yr average"],
            ["Mandi price deviation", "Agmarknet, data.gov.in", "% of median modal price below MSP"],
            ["NDVI satellite index", "NASA MODIS MOD13Q1", "crop canopy health from space"],
            ["Repayment proximity", "district crop calendar", "nearness to loan-due window (amplifier)"],
          ],
          [2340, 2808, 4212]),
        spacer(60),
        // signal-fusion diagram
        flowRow([
          new TableCell({ width: { size: 3000, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
            shading: { type: ShadingType.CLEAR, fill: LIGHT }, margins: { top: 70, bottom: 70, left: 90, right: 90 },
            children: ["Drought", "Price gap vs MSP", "NDVI (satellite)", "Repayment proximity"].map((t, i) =>
              new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: i === 3 ? 0 : 24 },
                children: [new TextRun({ text: t, size: 17, color: GREEN, bold: true, font: "Calibri" })] })) }),
          arrowCell(420),
          flowBox("LightGBM", "gradient-boosted fusion", 2400, "DDEBDD", GREEN),
          arrowCell(420),
          flowBox("FSI 0–100", "> 75 = CRITICAL alert", 2760, HDRBG, "FFFFFF"),
        ], [3000, 420, 2400, 420, 2760]),
        spacer(80),
        h2("4.2  The FSI model — what its metrics do and do not mean"),
        rich([
          { text: "A LightGBM regressor maps the four signals plus month/crop/region to FSI 0–100, trained on our 13,644-row synthetic dataset (§6) and evaluated on " },
          { text: "held-out talukas the model has never seen", bold: true }, { text: "." },
        ]),
        table(["Consistency check on synthetic data (held-out talukas)", "Value"],
          [["Mean absolute error (0–100 scale)", "3.75"], ["R²", "0.942"],
           ["Critical-alert recall (FSI > 75)", "0.78"], ["Critical-alert precision", "0.83"]],
          [5148, 4212]),
        spacer(60),
        rich([
          { text: "What these numbers mean, plainly: ", bold: true, color: RED },
          { text: "our synthetic labels come from a domain-logic formula, so the model is recovering a function we designed. The metrics measure " },
          { text: "internal pipeline consistency — not real-world predictive power. ", bold: true },
          { text: "Real validation is the §8 pilot: alert precision vs officer-verified ground truth over one season. Scoping the ML claim honestly is deliberate." },
        ]),
        rich([
          { text: "Threshold FSI > 75 ", bold: true },
          { text: "is a tunable operating point (recall 0.78 / precision 0.83 ≈ one false alert per four), calibrated per district against officer capacity in the pilot. The label's interaction terms (drought × repayment, price × repayment) encode the core insight: distress spikes when crop failure meets the loan deadline — the documented Oct–Jan clustering." },
        ]),
        h2("4.3  Context engineering (track slide 8 — all six elements)"),
        table(["Track requirement", "KisaanRaksha implementation"],
          [
            ["Tool-grounded reasoning", "agent calls MCP tools for every fact; zero bare answers"],
            ["Structured memory", "SQLite history: district, crop, past FSI, claims — recalled each turn"],
            ["Localization-aware", "Marathi-first; Hindi/English auto-matched; ₹/quintal; Devanagari spellings pinned"],
            ["Retrieval grounding", "crop calendar, MSP tables, district registry as curated context"],
            ["Guardrails", "FSI thresholds decide alerts (not the LLM); SIMULATION always labeled; helpline in critical replies"],
            ["Multi-step planning", "plan → signals → FSI → alert → claim, state carried across steps"],
          ],
          [3276, 6084]),

        // ===== 5 RESPONSIBLE AI =====
        h1("5.  Responsible AI — §8.3 Compliance & Bias Audit"),
        p("The FSI directs officer attention, so we audit the critical-alert decision (FSI > 75) on held-out talukas. The gated harm metric is the false-negative rate — a missed alert is a missed farmer."),
        table(["Group", "Alert rate", "False-negative rate", "MAE"],
          [["Vidarbha", "0.064", "0.205", "3.74"], ["Marathwada", "0.077", "0.229", "3.75"],
           ["Gap across regions", "0.013", "0.024", "0.015"], ["Gap across crops", "0.045", "0.074", "0.23"]],
          [2808, 2106, 2680, 1766]),
        spacer(60),
        table(["Fairness gate", "Threshold", "Observed", "Result"],
          [["FNR gap — region", "< 0.10", "0.024", "PASS"], ["FNR gap — crop", "< 0.10", "0.074", "PASS"],
           ["MAE gap — region", "< 2.0 pts", "0.015", "PASS"], ["MAE gap — crop", "< 2.0 pts", "0.23", "PASS"],
           ["Alert-rate gap", "monitored, not gated", "0.013 / 0.045", "—"]],
          [3276, 2340, 2106, 1638]),
        rich([{ text: "FNR gaps are gated at 0.10, MAE gaps at 2.0 points. Alert-rate is monitored not gated — Marathwada's higher rate reflects genuinely higher drought risk; equalizing it would suppress true alerts. Full report: model/fairlearn_report.md.", size: 22 }], { before: 80 }),
        h2("5.2  Data ethics & honest limitations"),
        bullet("No real farmer PII: training data is synthetic; live farmers keyed by hashed WhatsApp numbers."),
        bullet("Every source cited (README): Open-Meteo CC-BY 4.0, Agmarknet, NASA MODIS, CACP MSP, public GeoJSON."),
        bullet("The demo crisis is always labeled 'SIMULATION' — no fabricated live claims."),
        bullet("Metrics show pipeline consistency on synthetic data, not real-world prediction (see §4.2, §8 pilot)."),
        bullet("District-level signals mask farm variance; the FSI is an officer-attention tool, never an automated eligibility or denial decision."),

        // ===== 6 DATASET =====
        h1("6.  Custom Dataset — Flagged for IEEE Dataport"),
        rich([
          { text: "maharashtra_ag_stress_dataset.csv", bold: true },
          { text: " — 13,644 (district × taluka × crop × year × month) rows for 16 districts, with the four signals and a documented stress label. Fully synthetic (zero PII), reproducible from a seeded script, and grounded in real distributions: IMD drought propensity, 2024–26 Agmarknet-vs-MSP gaps, MODIS kharif NDVI seasonality, real CACP MSP. Flagged for IEEE Dataport (slide 11); methodology in dataset/README.md." },
        ]),

        // ===== 7 IMPACT =====
        h1("7.  Impact — Accessibility & Scalability"),
        bulletRich([{ text: "Accessibility: ", bold: true, color: MIDGREEN }, { text: "WhatsApp voice in the farmer's own language — no app, no literacy requirement, any phone; offline-first server with cached fallback for low connectivity." }]),
        bulletRich([{ text: "Scalability: ", bold: true, color: MIDGREEN }, { text: "all sources are pan-India public APIs; adding a district is one JSON entry; free-tier inference means fractions of a rupee per conversation; the four-signal pattern generalizes to any rain-fed belt." }]),
        spacer(60),
        table(["Deployment metric", "Current build", "State scale-up path"],
          [
            ["Districts monitored", "16 (Vidarbha + Marathwada)", "36 (all Maharashtra) — config only"],
            ["Farmers reachable", "every WhatsApp user in coverage", "WhatsApp Business API + Krishi Vibhag lists"],
            ["Claim assistance", "PMFBY letter auto-drafted (Marathi)", "direct PMFBY portal API"],
            ["Officer surface", "WhatsApp alerts + Streamlit heatmap", "integrate into Mahavedh / Krishi dashboards"],
          ],
          [2808, 3276, 3276]),

        // ===== 8 DEPLOYMENT =====
        h1("8.  Deployment Pathway & Sustainability"),
        bullet("Ownership: handoff to Krishi Vibhag (district offices) or an NGO — the alert flow mirrors their duty-roster practice."),
        bullet("Low cost: one <1 MB LightGBM file, free-tier inference, no GPU in the serving path."),
        bullet("Maintainable: modular repo, one-command dataset regen + retrain, bias audit regenerates automatically."),
        bullet("Pilot: one monsoon season across 3 Amravati talukas, measuring alert precision vs officer-verified ground truth and PMFBY completion rates."),

        // ===== 9 DEMO =====
        h1("9.  Live Demo — Verified End-to-End on a Real Phone"),
        rich([
          { text: "Executed on a physical phone via the Twilio WhatsApp sandbox. The farmer can send a " },
          { text: "Marathi voice note or a text message", bold: true },
          { text: " — voice is the primary, literacy-free path; Whisper transcribes it either way. The agent then chains weather → mandi → NDVI → compute_fsi and branches on the score:" },
        ]),
        flowRow([
          flowBox("Marathi voice", "WhatsApp note"), arrowCell(),
          flowBox("Whisper ASR", "→ text"), arrowCell(),
          flowBox("Agent + MCP", "4 signals → FSI"), arrowCell(),
          flowBox("FSI 0–100", "threshold 75"),
        ], [1740, 340, 1560, 340, 1860, 340, 2100]),
        spacer(40),
        flowRow([
          flowBox("FSI < 75 → LOW", "honest all-clear reply, no alert", 4560, "DDEBDD", GREEN),
          new TableCell({ width: { size: 240, type: WidthType.DXA }, children: [new Paragraph({ children: [] })] }),
          flowBox("FSI > 75 → CRITICAL", "officer alert + Marathi PMFBY claim PDF", 4560, "FCE4D6", AMBER),
        ], [4560, 240, 4560]),
        spacer(120),

        rich([{ text: "Crisis path (labeled simulation).", bold: true, color: AMBER, size: 23 }]),
        p("A demo message replaying the Oct–Nov 2024 stress pattern raises FSI to 87.9 CRITICAL. The officer receives a WhatsApp alert with the full evidence; the farmer receives Marathi guidance and an auto-drafted PMFBY claim as a PDF. Every simulated message carries a visible SIMULATION tag.", { after: 80 }),
        screenshot(CRIT_IMG),
        caption("Fig. 1 — Crisis simulation: officer alert (FSI 87.9 CRITICAL, evidence + farmer callback), Marathi guidance with the Kisan helpline, and the auto-drafted PMFBY claim delivered as a PDF."),

        rich([{ text: "Calm path (live data).", bold: true, color: MIDGREEN, size: 23 }]),
        p("On a real, calm day the same pipeline returns FSI 20.9 LOW and replies with an honest all-clear — no alert, no claim. The contrast between the two is the point: the system does not cry wolf.", { after: 80 }),
        screenshot(CALM_IMG),
        caption("Fig. 2 — Calm day on live data: rainfall deficit 10.6%, NDVI 0.77, FSI 20.9 LOW → all-clear Marathi reply, no false alarm."),

        // ===== 10 TEAM =====
        h1("10.  Team, Repository & Declaration"),
        table(["Item", "Detail"],
          [
            ["Team", "Sahil Karande · Pranav Shripannavar — 2 members"],
            ["Repository", "github.com/sahilkarande0918-cmd/Kisan-Raksha-project"],
            ["Stack", "Python · FastMCP · FastAPI · LightGBM · Fairlearn · Whisper/AI4Bharat ASR · Twilio WhatsApp · Streamlit · SQLite"],
            ["Custom dataset", "dataset/maharashtra_ag_stress_dataset.csv — flagged for IEEE Dataport"],
            ["Bias audit", "model/fairlearn_report.md — all gates pass"],
            ["Declaration", "All data public or synthetic; no real personal data collected; per Code of Conduct §8.3."],
          ],
          [2340, 7020]),
        spacer(),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 260 },
          children: [new TextRun({ text: "Technology must serve humanity — KisaanRaksha points it at the farmer the system forgot.", italics: true, size: 24, color: GREEN, font: "Calibri" })] }),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("docs/KisaanRaksha_Round1_Solution.docx", buf);
  const have = fs.existsSync(CRIT_IMG) && fs.existsSync(CALM_IMG);
  console.log("written docs/KisaanRaksha_Round1_Solution.docx", buf.length, "bytes");
  console.log("screenshots embedded:", have ? "YES (both)" :
    `PENDING — save ${CRIT_IMG} and ${CALM_IMG}`);
});
