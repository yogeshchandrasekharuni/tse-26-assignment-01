"""Build an evidence-bound twelve-page PDF; a draft cannot be mistaken for final results."""

import argparse
import json
from fractions import Fraction
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import pymupdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from housing.identity import ROOT, sha256_bytes, write_json
from housing.tools.exact import serial

INK = colors.HexColor("#182b45")
BLUE = colors.HexColor("#344cb7")
MUTED = colors.HexColor("#4f5d70")
LINE = colors.HexColor("#d9dfe8")
PALE = colors.HexColor("#f3f5fa")
AMBER = colors.HexColor("#77541c")
PAGE_W, PAGE_H = A4
MARGIN = 44
WIDTH = PAGE_W - 2 * MARGIN
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10.3, leading=14.3, textColor=INK)
INTRO = ParagraphStyle("intro", parent=BODY, fontSize=11.4, leading=15.6, textColor=MUTED)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.1, leading=11.2, textColor=MUTED)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.1, leading=10.6)
HEADING = ParagraphStyle("heading", parent=BODY, fontName="Helvetica-Bold", fontSize=12, leading=15)
TITLE = ParagraphStyle("title", parent=BODY, fontName="Helvetica-Bold", fontSize=25, leading=28)


def load(path: Path) -> Any:
    return json.loads(path.read_bytes())


def percent(value: str | None) -> str:
    if value is None:
        return "unavailable"
    return str(serial(Fraction(value) * 100, digits=2)) + "%"


class Page:
    def __init__(self, canvas: Canvas, number: int, title: str, draft: bool):
        self.canvas = canvas
        self.y = PAGE_H - 78
        canvas.setFillColor(BLUE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(MARGIN, PAGE_H - 35, "HOUSING EVIDENCE / TSE")
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 35, "Synthetic observations | 16 October 2026")
        canvas.setStrokeColor(LINE)
        canvas.line(MARGIN, PAGE_H - 46, PAGE_W - MARGIN, PAGE_H - 46)
        canvas.line(MARGIN, 45, PAGE_W - MARGIN, 45)
        canvas.setFont("Helvetica", 7.6)
        canvas.setFillColor(AMBER if draft else MUTED)
        canvas.drawString(
            MARGIN,
            30,
            "WORKING DRAFT - headline evidence pending"
            if draft
            else "Frozen workload | nominal base-level uncertainty",
        )
        canvas.drawRightString(PAGE_W - MARGIN, 30, f"{number} / 12")
        self.text(title, TITLE, gap=13)

    def text(self, value: str, style: ParagraphStyle = BODY, gap: float = 10, *, raw: bool = False) -> None:
        paragraph = Paragraph(value if raw else escape(value), style)
        _, height = paragraph.wrap(WIDTH, PAGE_H)
        if self.y - height < 61:
            raise ValueError(f"Report page overflow: {value[:75]}")
        paragraph.drawOn(self.canvas, MARGIN, self.y - height)
        self.y -= height + gap

    def block(self, heading: str, value: str) -> None:
        self.y -= 5
        self.text(heading, HEADING, gap=6)
        self.text(value)

    def table(self, rows: list[list[str]], widths: list[float] | None = None) -> None:
        table = Table([[Paragraph(escape(cell), CELL) for cell in row] for row in rows], colWidths=widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PALE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.45, LINE),
                ]
            )
        )
        _, height = table.wrap(WIDTH, PAGE_H)
        if self.y - height < 61:
            raise ValueError("Report table exceeds its page")
        table.drawOn(self.canvas, MARGIN, self.y - height)
        self.y -= height + 14

    def topology(self) -> None:
        """Authored vector dependency diagram; numerical data never computed here."""
        c = self.canvas
        height = 195
        self.y -= height
        c.saveState()
        c.translate(MARGIN, self.y)
        c.setFillColor(PALE)
        c.roundRect(0, 0, WIDTH, height, 9, fill=1, stroke=0)
        positions = {
            "Orchestrator": (65, 95),
            "Price": (195, 140),
            "Supply": (195, 95),
            "Region*": (195, 50),
            "Aggregate": (310, 95),
            "Reviewer": (430, 95),
            "Composer": (430, 35),
        }
        c.setStrokeColor(MUTED)
        c.setLineWidth(1)
        for a, b in [
            ("Orchestrator", "Price"),
            ("Orchestrator", "Supply"),
            ("Orchestrator", "Region*"),
            ("Price", "Aggregate"),
            ("Supply", "Aggregate"),
            ("Region*", "Aggregate"),
            ("Aggregate", "Reviewer"),
            ("Reviewer", "Composer"),
        ]:
            x1, y1 = positions[a]
            x2, y2 = positions[b]
            c.line(x1, y1, x2, y2)
        c.setStrokeColor(AMBER)
        c.lines([(430, 105, 430, 177), (430, 177, 65, 177), (65, 177, 65, 108)])
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(255, 181, "REFINE: new scan strategy / conditional Region")
        c.setStrokeColor(MUTED)
        c.lines([(430, 25, 430, 12), (430, 12, 25, 12), (25, 12, 25, 95), (25, 95, 54, 95)])
        for name, (x, y) in positions.items():
            c.setFillColor(colors.white)
            c.setStrokeColor(BLUE if name != "Aggregate" else MUTED)
            c.circle(x, y, 9, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(x, y - 23 if name != "Composer" else y + 16, name)
        c.restoreState()
        self.y -= 10
        self.text(
            "Figure 1. All model roles are inside the parent boundary. Region* is conditional; Aggregate is deterministic Python. Every child result returns to the parent. The amber cycle changes actual work.",
            SMALL,
        )


def completed_reference(draft: bool) -> tuple[Path, list[dict[str, Any]] | None, Path | None]:
    campaign = ROOT / "artifacts/campaigns/headline-live-v1"
    rows = load(campaign / "headline.json") if (campaign / "headline.json").exists() else None
    complete = rows is not None and len(rows) == 10 and all(row["complete"] for row in rows)
    reproductions = []
    for path in sorted((ROOT / "artifacts/reproductions").glob("*/reproduction-comparison.json")):
        item = load(path)
        if (
            item["status"] == "matched"
            and item["logical_comparisons"] == 900
            and item["live_reference"] == str(campaign.relative_to(ROOT))
        ):
            reproductions.append(path.parent)
    reproduction = reproductions[-1] if reproductions else None
    if not draft:
        if not complete or reproduction is None:
            raise ValueError(
                "Final report requires ten complete live rows and a matched full offline reproduction"
            )
        for path in (ROOT / "reports/data/diagnosis.json", ROOT / "reports/data/clean-checkout.json"):
            if not path.exists() or load(path).get("status") != "verified":
                raise ValueError(f"Final report requires verified evidence: {path.relative_to(ROOT)}")
        for name, expected in load(campaign / "artifact_hashes.json").items():
            path = (campaign / name).resolve()
            if not path.is_relative_to(campaign) or sha256_bytes(path.read_bytes()) != expected:
                raise ValueError(f"Changed campaign artifact: {name}")
    return campaign, rows if complete else None, reproduction


def report(draft: bool) -> Path:
    content = load(ROOT / "reports/content.json")
    sources = load(ROOT / "reports/sources.json")
    campaign, rows, reproduction = completed_reference(draft)
    destination = ROOT / "output/pdf" / ("housing-report-draft.pdf" if draft else "housing-report.pdf")
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(destination), pagesize=A4, pageCompression=1, invariant=1)
    canvas.setTitle(content["title"] + ": " + content["subtitle"])
    canvas.setSubject("IIIT Hyderabad TSE assignment; generated synthetic data")
    canvas.setAuthor("Author identities not supplied")
    for number, section in enumerate(content["pages"], 1):
        page = Page(canvas, number, section["title"], draft)
        if number == 1:
            page.text(content["title"], ParagraphStyle("cover", parent=TITLE, fontSize=36, leading=40), gap=6)
            page.text(content["subtitle"], INTRO, gap=21)
        page.text(section["intro"], INTRO, gap=17)
        if number == 1:
            page.table(
                [
                    ["Frozen feed", "Evaluation design", "Public agent boundary"],
                    [
                        "34,560 observations\n12 ZIPs / 24 months",
                        "10 relations x 30 bases\n3 paired seeds per base",
                        "Orchestrator\n5 internal child roles",
                    ],
                ],
                [WIDTH / 3] * 3,
            )
        if number == 2:
            page.text(
                "Snapshot SHA-256: bb0e9f3ed47a65eabbaab4e0a4de192ca7918a61eee111e273a70e145f87692b", SMALL
            )
        if number == 3:
            page.topology()
        if number == 4:
            page.table(
                [
                    ["Recorded step", "Actual action / evidence"],
                    ["Indexed scan", "Price + Supply; 2 visible qualifying observations"],
                    ["Reviewer / pass 1", "REFINE: INDEX_COVERAGE_MISMATCH + SPARSE_SLICE"],
                    ["Parent replan", "full_csv; Price + Supply + Region; criteria unchanged"],
                    ["Fresh scans / review", "3 observations; ACCEPT_LIMITED / CONFIRMED_SPARSE"],
                    ["Compose / parent return", "Grounded facts and sparse caveat; 16 model decisions"],
                ],
                [120, WIDTH - 120],
            )
            page.text(
                "Trace: artifacts/traces/20261001T144318Z-82736e984f/trace.jsonl. Auxiliary injected index omission; excluded from headline results.",
                SMALL,
            )
        if number == 7:
            cohort = load(ROOT / "configs/headline-cohort-v1.json")
            page.text(
                "Frozen preflight: "
                + str(cohort["frozen_at_utc"])
                + ". Exact cohort and witnesses: configs/headline-cohort-v1.json.",
                SMALL,
            )
        if number == 8:
            if rows:
                table = [["MR / family", "n", "x/n", "Rate", "Nominal 95% CI", "Pairs*", "Inv.", "Err."]]
                for row in rows:
                    table.append(
                        [
                            row["mr_id"] + " / " + row["family"][0].upper(),
                            str(row["completed_bases"]),
                            f"{row['violating_bases']}/{row['completed_bases']}",
                            percent(row["base_rate"]),
                            percent(row["ci95_low"]) + " - " + percent(row["ci95_high"]),
                            f"{row['seed_pair_violations']}/{row['seed_pairs_completed']}",
                            str(row["invalid_candidates"]),
                            str(row["execution_errors"]),
                        ]
                    )
                page.table(table, [70, 24, 35, 48, 137, 57, 43, WIDTH - 414])
                page.text(
                    "I=invariance; M=monotonic; D=directional. *Violating/completed paired-seed comparisons. Source: headline-live-v1/headline.json; every completed row uses seeds 104729, 130363, 155921.",
                    SMALL,
                )
                runtime = load(campaign / "runtime.json")
                page.text(
                    f"Measured execution: {runtime['logical_comparisons']} logical comparisons; {runtime['physical_analysis_attempts']} physical attempts; {sum(runtime['model_calls_by_role'].values())} model decisions; {runtime['refinements']} refinements; {runtime['schema_repairs']} repairs.",
                    SMALL,
                )
            else:
                page.block(
                    "Headline evidence pending",
                    "The 900-comparison live campaign is still executing. No final rate, interval or root-cause ranking is claimed in this draft. Final report creation fails until the complete campaign and full offline reproduction exist.",
                )
                pilot = load(ROOT / "artifacts/campaigns/pilot-live-v1/headline.json")[0]
                page.block(
                    "Completed pilot - separate evidence",
                    f"MR01 only: 9 paired comparisons across 3 distinct bases; {pilot['violating_bases']}/3 violating bases; nominal 95% Wilson {percent(pilot['ci95_low'])} - {percent(pilot['ci95_high'])}. All nine recomputed case semantics and the pilot table matched offline. This pilot does not satisfy the thirty-base headline requirement.",
                )
        if number == 9:
            diagnosis_path = ROOT / "reports/data/diagnosis.json"
            if diagnosis_path.exists():
                diagnosis = load(diagnosis_path)
                page.block("Observed diagnosis", diagnosis["summary"])
            else:
                page.block(
                    "Diagnosis awaits completed outcomes",
                    "No final top-three ranking is available yet. The frozen selection rule and evidence requirements below will be applied to the completed headline table; historical integration bugs are not relabeled as natural headline violations.",
                )
        for heading, text in section["blocks"]:
            page.block(heading, text)
        if number == 2:
            page.table(
                [
                    ["Hand-calculated example", "Price (USD)", "Size (sq ft)", "Individual ratio"],
                    ["Observation A", "100", "100", "1"],
                    ["Observation B", "300", "50", "6"],
                ],
                [WIDTH - 280, 90, 90, 100],
            )
            page.text(
                "Median of individual ratios = (1 + 6) / 2 = 3.5. Ratio of medians = 200 / 75 = 8/3. The contract uses 3.5. This is a mathematical example, not market data or a campaign result.",
                SMALL,
            )
        if number == 7:
            page.table(
                [
                    ["Wilson score interval on bases", "Formula"],
                    ["Denominator", "d = 1 + z^2/n; p = x/n"],
                    ["Centre", "c = (p + z^2/(2n)) / d"],
                    ["Half-width", "h = z/d * sqrt(p(1-p)/n + z^2/(4n^2))"],
                    ["Limits", "[max(0,c-h), min(1,c+h)]; n=0 gives no interval"],
                ],
                [150, WIDTH - 150],
            )
        if number == 10 and reproduction:
            page.text(
                "Full offline evidence: "
                + str(reproduction.relative_to(ROOT))
                + "/reproduction-comparison.json",
                SMALL,
            )
        if number == 12:
            page.text("References", HEADING, gap=9)
            for index, source in enumerate(sources, 1):
                text = f"[{index}] {source['authors']}. {source['title']}. " + source.get("publication", "")
                if source.get("doi"):
                    text += " DOI: " + source["doi"] + "."
                if source.get("url"):
                    url = escape(source["url"])
                    text = escape(text) + f' <link href="{url}" color="#344cb7">Primary source</link>.'
                else:
                    text = escape(text + " Repository original, pp.1-4.")
                page.text(text, SMALL, gap=7, raw=True)
        canvas.showPage()
    canvas.save()
    with pymupdf.open(destination) as document:
        if len(document) != 12:
            raise ValueError("Report page count differs from twelve")
    inputs = [ROOT / "reports/content.json", ROOT / "reports/sources.json", Path(__file__)]
    if rows:
        inputs.append(campaign / "headline.json")
    if reproduction:
        inputs.append(reproduction / "reproduction-comparison.json")
    write_json(
        destination.with_suffix(".manifest.json"),
        {
            "status": "draft" if draft else "built_requires_visual_inspection",
            "pdf_sha256": sha256_bytes(destination.read_bytes()),
            "pages": 12,
            "headline_campaign": str(campaign.relative_to(ROOT)),
            "full_reproduction": str(reproduction.relative_to(ROOT)) if reproduction else None,
            "inputs": {str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes()) for p in inputs},
        },
    )
    print(
        f"Built {destination.relative_to(ROOT)} (12 pages; {'DRAFT' if draft else 'render and inspect before delivery'})"
    )
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true")
    try:
        report(parser.parse_args().draft)
    except ValueError as error:
        raise SystemExit(str(error)) from error
