// KisaanRaksha — Round 1 Solution Document generator (Hack4Humanity 2026)
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat,
  PageBreak, Packer, Paragraph, ShadingType, Table, TableCell, TableOfContents,
  TableRow, TextRun, WidthType, PageNumber, VerticalAlign,
} = require("docx");
const fs = require("fs");

const GREEN = "1B5E20", MIDGREEN = "2E7D32", DARK = "212121", GRAY = "616161",
  LIGHT = "E8F5E9", AMBER = "E65100", RED = "B71C1C", HDRBG = "1B5E20";

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 160, before: opts.before ?? 0 },
  alignment: opts.align,
  children: [new TextRun({
    text, bold: opts.bold, italics: opts.italics, size: opts.size ?? 22,
    color: opts.color ?? DARK, font: "Calibri",
  })],
});

const rich = (runs, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 160, before: opts.before ?? 0 },
  alignment: opts.align,
  children: runs.map(r => new TextRun({ font: "Calibri", size: r.size ?? 22, ...r })),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 },
  children: [new TextRun({ text, bold: true, size: 32, color: GREEN, font: "Calibri" })],
});
const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 },
  children: [new TextRun({ text, bold: true, size: 26, color: MIDGREEN, font: "Calibri" })],
});

const bullet = (text, opts = {}) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 100 },
  children: [new TextRun({ text, size: 22, font: "Calibri", bold: opts.bold, color: opts.color ?? DARK })],
});
const bulletRich = (runs) => new Paragraph({
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 100 },
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
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    children: [Array.isArray(content) ? content[0] : cellP(String(content), header
      ? { bold: true, color: "FFFFFF", size: 20 } : {})],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: colWidths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => mkCell(h, i, true)) }),
      ...rows.map((r, ri) => new TableRow({
        children: r.map((c, i) => {
          const cell = mkCell(c, i);
          if (ri % 2 === 1) cell.root[0].root.push(); // zebra handled below instead
          return cell;
        }),
      })),
    ],
  });
}

// simple key stat callout
const stat = (big, label) => new TableCell({
  width: { size: 3120, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
  shading: { type: ShadingType.CLEAR, fill: LIGHT },
  margins: { top: 140, bottom: 140, left: 120, right: 120 },
  children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
      children: [new TextRun({ text: big, bold: true, size: 40, color: GREEN, font: "Calibri" })] }),
    new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: label, size: 18, color: GRAY, font: "Calibri" })] }),
  ],
});

const spacer = (h = 120) => new Paragraph({ spacing: { after: h }, children: [] });

const flowBox = (title, sub) => new TableCell({
  width: { size: 1872, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
  shading: { type: ShadingType.CLEAR, fill: LIGHT },
  margins: { top: 100, bottom: 100, left: 80, right: 80 },
  children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 30 },
      children: [new TextRun({ text: title, bold: true, size: 19, color: GREEN, font: "Calibri" })] }),
    new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: sub, size: 16, color: GRAY, font: "Calibri" })] }),
  ],
});
const arrowCell = () => new TableCell({
  width: { size: 468, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
  margins: { top: 100, bottom: 100 },
  children: [new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "→", bold: true, size: 28, color: MIDGREEN, font: "Calibri" })] })],
});

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 360, hanging: 200 } } } }],
    }],
  },
  styles: {
    default: { document: { run: { font: "Calibri", size: 22, color: DARK } } },
  },
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
          children: [new TextRun({ text: "Team:  Sahil Karande  ·  [Teammate Name]", size: 24, color: DARK, font: "Calibri", bold: true })] }),
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
          { text: "Maharashtra loses a farmer to suicide every 3 hours (2025 state data). In 2024, " },
          { text: "2,706 farmers died in Vidarbha and Marathwada alone", bold: true, color: RED },
          { text: " — and of those cases, only 1,563 were even deemed eligible for government aid." },
        ]),
        p("The system's failure is structural: every rupee of state response is reactive — ex-gratia compensation paid to a family after a death. There is zero predictive infrastructure. Yet the crisis that ends in suicide follows a well-documented, measurable pattern that builds over months:"),
        bullet("A failed monsoon (rainfall deficit) destroys the kharif crop,"),
        bullet("mandi prices fall below MSP just when the farmer must sell,"),
        bullet("and the crop-loan repayment deadline arrives with nothing to pay it."),
        rich([
          { text: "Every one of those signals is publicly observable in real time — rainfall from weather archives, prices from Agmarknet, crop health from satellites, repayment windows from the crop calendar. " },
          { text: "The data to see the crisis coming already exists. Nobody is looking.", bold: true },
        ]),
        h2("1.1  Our north star beneficiary"),
        rich([
          { text: "A cotton farmer in Amravati taluka with 2 acres, a ₹1.2 lakh crop loan, a feature phone running WhatsApp, and Marathi as his only fluent language. ", italics: true },
          { text: "Every design decision in KisaanRaksha traces back to whether it works for him: voice-first (literacy-independent), Marathi-first, WhatsApp (no new app), and offline-tolerant infrastructure on the government side.", italics: true },
        ]),
        spacer(),

        // ===== 2 SOLUTION =====
        h1("2.  The Solution — Predict, Alert, Assist"),
        p("KisaanRaksha is an agentic AI early-warning system with three jobs:", { bold: true }),
        bulletRich([{ text: "PREDICT — ", bold: true, color: GREEN }, { text: "a LightGBM model fuses four live signals into a Financial Stress Index (FSI, 0–100) per district. FSI > 75 = critical." }]),
        bulletRich([{ text: "ALERT — ", bold: true, color: AMBER }, { text: "when FSI crosses critical, the duty agriculture officer receives a WhatsApp alert with the evidence: deficit %, price gap, satellite NDVI, farmers in repayment window — before a crisis, not after a death." }]),
        bulletRich([{ text: "ASSIST — ", bold: true, color: MIDGREEN }, { text: "the farmer talks to the system in Marathi voice notes on WhatsApp; it answers in Marathi with grounded numbers and auto-drafts his PMFBY crop-insurance claim letter, evidence attached." }]),
        spacer(60),
        new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [3120, 3120, 3120],
          rows: [new TableRow({ children: [
            stat("16", "districts covered (Vidarbha + Marathwada)"),
            stat("4", "grounded live signals fused per district"),
            stat("87.9", "FSI raised in live demo → alert + claim fired"),
          ] })] }),
        spacer(),

        // ===== 3 ARCHITECTURE =====
        h1("3.  Architecture — Custom MCP Server, No Bare LLM Calls"),
        p("The system implements the track's reference pattern (onboarding slide 7) end-to-end: every fact the agent states comes from a role-scoped MCP tool grounded in a real dataset — the LLM never answers from its training data."),
        new Table({ width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1872, 468, 1872, 468, 1872, 468, 1872, 468],
          rows: [new TableRow({ children: [
            flowBox("End User", "Farmer — WhatsApp Marathi voice"),
            arrowCell(),
            flowBox("Agent / LLM", "tool-calling loop (Groq Llama-3.3 / Gemini)"),
            arrowCell(),
            flowBox("MCP Server", "FastMCP — 7 role-scoped tools"),
            arrowCell(),
            flowBox("Grounded Data", "Open-Meteo · Agmarknet · NASA MODIS"),
            new TableCell({ width: { size: 468, type: WidthType.DXA }, children: [new Paragraph({ children: [] })] }),
          ] })] }),
        spacer(60),
        p("Inbound: Twilio WhatsApp Sandbox → FastAPI webhook → Whisper large-v3 ASR (Marathi/Hindi auto-detect) → agent. Outbound: Twilio sender for farmer replies, officer alerts, and claim letters. A Streamlit choropleth dashboard gives district officers the live FSI heatmap."),
        h2("3.1  The seven MCP tools"),
        table(["Tool", "One clear job", "Grounding"],
          [
            ["query_weather_signal", "30-day rainfall deficit vs 5-yr baseline → drought signal", "Open-Meteo ERA5 archive"],
            ["query_mandi_prices", "median mandi price vs MSP → price-stress signal", "Agmarknet via data.gov.in"],
            ["query_ndvi_signal", "satellite crop-health → vegetation-stress signal", "NASA MODIS MOD13Q1 (ORNL)"],
            ["compute_fsi", "fuse 4 signals through LightGBM → FSI 0–100", "trained model, held-out validation"],
            ["get_farmer_history", "structured memory across sessions (hashed phone key)", "SQLite — no raw PII"],
            ["send_officer_alert", "WhatsApp alert with evidence when FSI critical", "Twilio"],
            ["draft_pmfby_claim", "Marathi PMFBY letter filled with the actual evidence numbers", "LLM + FSI evidence"],
          ],
          [2340, 4212, 2808]),
        spacer(60),
        p("Each tool has one job (track slide 9: role-scoped agents); the agent's decision chain is fully traceable through logged tool calls; tools are auditable and swappable — another team could reuse this MCP server as-is."),

        // ===== 4 METHODOLOGY =====
        h1("4.  Technical Methodology"),
        h2("4.1  Four signals → Financial Stress Index"),
        table(["Signal", "Source (live API)", "What it measures"],
          [
            ["Drought probability", "Open-Meteo ERA5 (keyless)", "30-day rainfall vs same window averaged over previous 5 years"],
            ["Mandi price deviation", "Agmarknet, data.gov.in", "% gap of median modal price below MSP (2025-26 CACP)"],
            ["NDVI satellite index", "NASA MODIS MOD13Q1 via ORNL", "actual crop canopy health from space, 16-day composites"],
            ["Repayment proximity", "district crop calendar", "nearness to the crop-loan due window — the coincidence amplifier"],
          ],
          [2340, 2808, 4212]),
        spacer(60),
        h2("4.2  The FSI model"),
        rich([
          { text: "A LightGBM regressor maps the four signals plus month/crop/region context to FSI 0–100. It is trained on our custom 13,644-row synthetic-but-grounded dataset (Section 6) and evaluated on " },
          { text: "held-out talukas the model has never seen", bold: true },
          { text: " — the honest test for geographic generalization." },
        ]),
        table(["Metric (held-out talukas)", "Value"],
          [
            ["Mean absolute error (0–100 scale)", "3.75"],
            ["R²", "0.942"],
            ["Critical-alert recall (FSI > 75)", "0.78"],
            ["Critical-alert precision", "0.83"],
          ],
          [5148, 4212]),
        spacer(60),
        p("The label formula encodes the core domain insight: distress spikes when crop failure coincides with the loan-repayment deadline — interaction terms (drought × repayment, price × repayment) amplify the base signal, mirroring the documented Oct–Jan clustering of farmer suicides."),
        h2("4.3  Context engineering (track slide 8, all six elements)"),
        table(["Track requirement", "KisaanRaksha implementation"],
          [
            ["Tool-grounded reasoning", "agent must call MCP tools for every fact; zero bare LLM answers"],
            ["Structured memory", "SQLite farmer history: district, crop, past FSI, claims — recalled every turn"],
            ["Localization-aware context", "Marathi-first replies; Hindi/English auto-detected and matched; MSP in ₹/quintal; correct Devanagari district spellings pinned"],
            ["Retrieval-augmented grounding", "crop calendar, MSP tables, district registry injected as curated context"],
            ["Guardrails & validation", "FSI thresholds decide alerts (not the LLM); simulation mode always labeled; helpline number in critical replies; no promises of money"],
            ["Multi-step planning", "plan → signals → FSI → alert decision → claim draft, state carried across steps"],
          ],
          [3276, 6084]),

        // ===== 5 RESPONSIBLE AI =====
        h1("5.  Responsible AI — §8.3 Compliance & Bias Audit"),
        h2("5.1  Fairlearn bias audit (mandatory for vulnerable-population models)"),
        p("The FSI drives officer attention toward or away from farmers, so we audit the critical-alert decision (FSI > 75) on held-out talukas. The harm metric is the false-negative rate — a missed alert is a missed farmer."),
        table(["Group", "Alert rate", "False-negative rate", "MAE"],
          [
            ["Vidarbha", "0.064", "0.205", "3.74"],
            ["Marathwada", "0.077", "0.229", "3.75"],
            ["Gap (region)", "0.013", "0.024  ✓ < 0.10 gate", "0.015"],
            ["Gap (crop: cotton/soy/tur)", "0.045", "0.074  ✓ < 0.10 gate", "0.23"],
          ],
          [2808, 2106, 2680, 1766]),
        spacer(60),
        p("All fairness gates pass. Full report: model/fairlearn_report.md in the repository, regenerated by model/fairlearn_report.py on every retrain."),
        h2("5.2  Data ethics"),
        bullet("No real farmer PII anywhere: training data is synthetic; live farmers are keyed by hashed WhatsApp numbers."),
        bullet("Every data source cited in README: Open-Meteo (CC-BY 4.0), Agmarknet/data.gov.in, NASA MODIS, CACP MSP, public GeoJSON boundaries."),
        bullet("Demo crisis scenario is always labeled 'SIMULATION' in every message and dashboard view — no fabricated live claims."),
        h2("5.3  Honest limitations"),
        bullet("FSI is trained on synthetic-but-grounded data; a deployment pilot must recalibrate against observed distress outcomes before any resource-allocation use."),
        bullet("District-level signals mask farm-level variance; NDVI at district HQ is a proxy, not a per-field measurement."),
        bullet("The model flags financial stress patterns — it is an officer-attention tool, never an automated eligibility or denial decision."),
        bullet("Mandi price coverage is thin off-season; the pipeline discloses its fallback scope (district → state → national → seasonal baseline) in every response."),

        // ===== 6 DATASET =====
        h1("6.  Custom Dataset — Flagged for IEEE Dataport"),
        rich([
          { text: "maharashtra_ag_stress_dataset.csv", bold: true },
          { text: " — 13,644 rows of (district × taluka × crop × year × month) panels for 16 Vidarbha/Marathwada districts, with the four stress signals and a documented financial-stress label. Fully synthetic (zero PII), fully reproducible (seeded generator script), and grounded in real distributions: IMD regional drought propensity, observed 2024–26 Agmarknet-vs-MSP gaps, MODIS kharif NDVI seasonality, and real CACP MSP values." },
        ]),
        p("Per the bonus pathway (onboarding slide 11), we flag this dataset for organizer-supported publication on IEEE Dataport. Generation methodology: dataset/README.md."),

        // ===== 7 IMPACT =====
        h1("7.  Impact — Accessibility & Scalability"),
        h2("7.1  Accessibility (works within real Indian constraints)"),
        bullet("Zero new app, zero literacy requirement: WhatsApp voice in the farmer's own language (Marathi-first; Hindi/English auto-matched)."),
        bullet("Works on any phone that runs WhatsApp; the farmer-side cost is one voice note."),
        bullet("Offline-first server design: every signal falls back to last-known cached values, so the dashboard and FSI survive connectivity loss (track slide 13)."),
        bullet("Evidence-based problem: 2,706 deaths (2024, Vidarbha+Marathwada), 42% deemed ineligible for aid — cited state data, not a hypothetical persona."),
        h2("7.2  Scalability (1 taluka → state footprint)"),
        bullet("All data sources are pan-India government/public APIs — adding a district is one JSON entry, no new data engineering."),
        bullet("Cost-aware: free-tier LLM inference, keyless weather/satellite APIs, SQLite → the marginal cost per farmer conversation is fractions of a rupee."),
        bullet("Same four-signal pattern generalizes to any rain-fed crop belt (Telangana, Karnataka, Bundelkhand) by swapping the district registry and crop calendar."),
        table(["Deployment metric", "Current build", "State scale-up path"],
          [
            ["Districts monitored", "16 (Vidarbha + Marathwada)", "36 (all Maharashtra) — config only"],
            ["Farmers reachable", "every WhatsApp user in covered districts", "WhatsApp Business API + Krishi Vibhag lists"],
            ["Claim assistance", "PMFBY letter auto-drafted in Marathi", "direct PMFBY portal API integration"],
            ["Officer surface", "WhatsApp alerts + Streamlit heatmap", "integration into existing Mahavedh/Krishi dashboards"],
          ],
          [2808, 3276, 3276]),

        // ===== 8 DEPLOYMENT =====
        h1("8.  Deployment Pathway & Sustainability"),
        p("Designed for month two, not hour twelve (track slide 13):", { bold: true }),
        bullet("Ownership path: handoff to Krishi Vibhag (district agriculture offices) or an NGO operator; the officer alert flow mirrors their existing duty-roster practice."),
        bullet("Low operating cost: one lightweight model file (LightGBM, <1 MB), free-tier inference, no GPU anywhere in the serving path."),
        bullet("Maintainable by someone else: modular repo, one-command dataset regeneration and retraining, every data source documented, bias audit regenerates automatically."),
        bullet("Pilot proposal: one monsoon season (Jun–Jan) across 3 talukas in Amravati district, measuring alert precision against officer-verified ground truth and PMFBY claim completion rates."),

        // ===== 9 DEMO =====
        h1("9.  Live Demo (verified on a real phone)"),
        p("The full loop below has already been executed end-to-end on a physical phone via the Twilio WhatsApp sandbox:"),
        bullet("1.  Farmer sends a Marathi voice note / text on WhatsApp."),
        bullet("2.  Whisper large-v3 transcribes (language auto-detected)."),
        bullet("3.  Agent chains MCP tools: weather → mandi → NDVI → compute_fsi."),
        bullet("4.  Calm day (live data): FSI 20.9 LOW → honest all-clear reply in Marathi, no alert. The system does not cry wolf."),
        bullet("5.  Crisis scenario (labeled simulation of Oct-Nov 2024 pattern): FSI 87.9 CRITICAL → officer WhatsApp alert with evidence + auto-drafted PMFBY claim letter in Marathi delivered back to the farmer."),
        bullet("6.  Streamlit dashboard shows the Maharashtra FSI choropleth updating from the same cache."),
        spacer(60),
        rich([
          { text: "Officer alert as delivered on WhatsApp:  ", bold: true },
          { text: "\"⚠ KisaanRaksha Alert: Amravati (Vidarbha) · FSI = 87.9 (CRITICAL) · Crop: cotton · Rainfall deficit: 57.4% · Market price ₹4,200/qtl (18% below MSP ₹7,710) · NDVI 0.39 · Est. 312 farmers in repayment window · Action: proactive outreach + PMFBY survey recommended.\"", italics: true, color: GRAY },
        ]),

        // ===== 10 TEAM =====
        h1("10.  Team, Repository & Declaration"),
        table(["Item", "Detail"],
          [
            ["Team", "Sahil Karande · [Teammate Name] — 2 members"],
            ["Repository", "github.com/sahilkarande0918-cmd/Kisan-Raksha-project"],
            ["Stack", "Python · FastMCP · FastAPI · LightGBM · Fairlearn · Whisper/AI4Bharat ASR · Twilio WhatsApp · Streamlit · SQLite"],
            ["Custom dataset", "dataset/maharashtra_ag_stress_dataset.csv — flagged for IEEE Dataport"],
            ["Bias audit", "model/fairlearn_report.md — all gates pass"],
            ["Declaration", "All data sources public or synthetic; no real personal data collected; per Code of Conduct §8.3."],
          ],
          [2340, 7020]),
        spacer(),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 300 },
          children: [new TextRun({ text: "Technology must serve humanity — KisaanRaksha points it at the farmer the system forgot.", italics: true, size: 24, color: GREEN, font: "Calibri" })] }),
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("docs/KisaanRaksha_Round1_Solution.docx", buf);
  console.log("written docs/KisaanRaksha_Round1_Solution.docx", buf.length, "bytes");
});
