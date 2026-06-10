---
name: officeqa-playbook
description: "USE FOR EVERY OfficeQA / Treasury-Bulletin question. The grounded numeric-reasoning\
  \ playbook that won highest-accuracy in Sentient Arena Cohort 0 — stdlib-only\
  \ computation, corrected statistical formulas, scorer-format discipline, and retrieval/unit/fiscal-year\
  \ traps. EvoSkill improves on top of this."
compatibility: goose
---

# OfficeQA Playbook (Arena Cohort-0 winning baseline)

A grounded reasoning agent for U.S. Treasury Bulletin Q&A. The corpus is ~700
pre-parsed markdown files at the data dir, one per monthly bulletin
(`treasury_bulletin_YYYY_MM.txt`). Answers are scored at **1% numeric tolerance**.

## IRON RULES — violating these scores ZERO

1. **Write the final answer to the answer file in EVERY code block.** A rough answer beats an empty file. End each Python block with `with open(ANSWER_PATH,'w') as f: f.write(str(result))`.
2. **ALL math in Python, STANDARD LIBRARY ONLY** (`import statistics, math`). The eval container has **no numpy / scipy / statsmodels / pandas and no pip** — importing them crashes the run and forces error-prone hand math. Python 3.12 stdlib already has `statistics.geometric_mean / fmean / linear_regression / correlation / pstdev / stdev`.
3. **After writing the final answer, STOP.** Do not re-search or recompute with a different method. Overwriting a correct answer with a "verification" is a top cause of wrong answers. Only reopen a file on a concrete unit/date/cell error.
4. **Cap every tool output.** End every grep with `| head -40`; keep `sed -n 'A,Bp'` windows ≤ 60 lines; NEVER `cat` a whole bulletin or dump a full table. Oversized outputs kill the session before an answer is written — an instant zero.

## STEP BUDGET (sessions die mid-task — answer EARLY)

Budget your steps: ≤ 8 to locate the right table, ≤ 6 to extract, 1–2 to compute + write. Checkpoints:
- **Step 10, table still not found** → STOP free-form grep. Read the bulletin's table-of-contents (first ~80 lines list every table with page numbers), or grep the corpus `index.txt`, then jump straight to the listed table.
- **Step 15** → you MUST have written a best-effort number to the answer file, even from partial data. Improve it afterwards only if you find a concrete error.
- Trying a 4th grep synonym for the same metric = you are in a spiral; switch to TOC navigation immediately.

## WORKFLOW

1. **Parse the question into a checklist** (first code comment): exact metric, exact period, units, rounding, how many values, every exclusion/constraint ("excluding territories/regional aggregates", "not weekly bills", "use Table FFO-3's definition", "reported IN <month year>"). Re-read this checklist once against the final answer.
2. **Pick the right bulletin FIRST** (see PUBLICATION LAG below) — most wrong answers come from the right table in the wrong issue.
3. **Retrieve with grep, never scroll.** `grep -l "metric" <corpus>/treasury_bulletin_YYYY_*.txt` → `grep -n -i "metric" FILE` → `sed -n 'A,Bp' FILE`. For multi-year questions, grep the LATEST year first for a retrospective summary table (one table beats 12 files).
4. **Extract with the bundled extractor — NEVER hand-type rows of numbers.** This skill ships a deterministic parser:
   `python3 ~/.config/goose/skills/officeqa-playbook/tbl.py FILE 'TITLE_REGEX' 'ROW_REGEX'`
   It prints the table's unit line, every column header with its index, and each matching row as cleaned numbers (footnote markers `1/ r p *` stripped, `(x)`→negative, `n.a.`→None) plus a components-vs-total identity check. Hand-transcription of long rows is the #1 source of wrong answers. (If the path is missing, `find ~/.config -name tbl.py`; as a last resort extract by hand with the printed per-value mapping.) Check units in title/header/column/footnote.
5. **Cross-check, compute in stdlib Python, write the answer file** in the same block.

## PUBLICATION LAG — which bulletin holds the data (top silent killer)

A bulletin dated `YYYY_MM` contains data only through roughly month `MM-2` (e.g. the 1982_03 issue's monthly tables end at Jan 1982).

- **December data for year X is NEVER in an X bulletin.** It first appears in X+1 issues (usually `X+1_02` / `X+1_03`).
- **Full calendar-year X series → open bulletin `X+1_02` or `X+1_03` FIRST** — its 13-month window covers Jan X…Jan X+1, i.e. all 12 CY-X months in ONE table. NEVER assemble CY X solely from X-dated issues.
- "reported IN <month year>" pins the exact file; otherwise prefer the latest bulletin that covers the period (revised figures).
- Year-end (Dec 31, X) stock figures: look in X+1 issues too.

## MONTH-COLUMN YEAR MAPPING (top silent killer #2)

Monthly tables show a **rolling 13-month window ending ~2 months before the issue date**, so the header spans **two calendar years**. Example from the Dec 1981 issue: `| Function | Oct. | Nov. | Dec. | Jan. | … | Sept. | Oct..1 |` = Oct 1980 → Oct 1981. A repeated month name suffixed `..1` is the same month ONE YEAR LATER; the year boundary sits at the Dec.→Jan. column transition. Therefore:

1. Before extracting, assign an explicit year to EVERY month column: columns up to and including `Dec.` belong to the earlier year, columns after `Dec.` to the later year. NEVER assume Jan…Dec all equal the bulletin's year.
2. For a calendar-year X request, pick an issue whose window contains all 12 months (X+1_02 / X+1_03); pre-1977 data may instead need two tables (Jan–Jun X plus Jul–Dec X, FY ran Jul–Jun).
3. After extraction print one line per value — `1981-Jan: 57198` — and confirm the 12 months are exactly the requested ones before computing.
4. Do not hand-type a long value list without this printed mapping; transcription misalignment is invisible and fatal.
5. The `Cumulative to date` column is FISCAL-year-to-date — never include it as a month, and use it as a cross-check only when the requested period matches the fiscal window.

## EXTRACTION CROSS-CHECK (mandatory, one shot — this is NOT "re-verification")

- If the table has a **Total / Calendar yr. / Fiscal yr. / Cumulative** row or column, compare your extracted values' sum against it. A mismatch > 2% means your columns are misaligned — re-map, don't shrug.
- **Row-internal OCR check (verified zero-scorer):** the corpus is OCR'd — single cells carry transposed digits (`1417655` printed as `1471655`). When a row shows components AND their total, assert `sum(components) == total` for every row you extract from; if one cell breaks the identity, recover it as `total − other components`. When two issues print the same series with one differing cell, the printed row/column total is the arbiter.
- A series spanning many years is reprinted in several issues — cross-check at least the values that dominate your result (endpoints, extremes) against a second issue before computing.
- Assert `len(found) == expected`; NEVER compute from a partial set — a missing value is a wrong answer.
- A value ~10× off its neighbors is an OCR or column-shift error — re-extract that cell.
- Try synonyms (outlays↔expenditures, receipts↔revenue, defense↔military). Data for year X often appears in the X+1 or X+2 bulletin.
- Sanity-check the result: an absurd magnitude (elasticity of −289, negative duration, CV > 5) means a bad input — fix extraction, not the formula.

## NAMED FORMULAS — corrected, stdlib-only (use exactly these)

```python
import statistics, math
geomean   = statistics.geometric_mean(vals)              # positive LEVELS, not % returns
lr = statistics.linear_regression(x, y); slope, intercept = lr.slope, lr.intercept
pred      = slope * x_target + intercept
corr      = statistics.correlation(x, y)                 # Pearson r
r2        = corr ** 2
var_pop   = statistics.pstdev(vals) ** 2                 # variance: population unless "sample"
zscore    = (x - statistics.fmean(v)) / statistics.pstdev(v)   # stdev(v) if "sample"
cv        = statistics.pstdev(vals) / statistics.fmean(vals)         # population unless "sample"
g         = [math.log(vals[i]/vals[i-1]) for i in range(1, len(vals))]
cv_log    = statistics.pstdev(g) / statistics.fmean(g)              # CV of YoY log growth
log_gr    = math.log(V2/V1)                                         # log growth; /years for cont.-compounded annual
realized_var = sum(x*x for x in g)                                  # realized variance = SUM of squared log returns (vs pstdev(g)**2 = plain variance — read which one is asked)
cagr      = (end/start) ** (1/(end_year - start_year)) - 1          # n = PERIODS, not #points
pct_pt    = new_pct - old_pct                                       # percentage POINTS, not % change
sym       = 2*(V2 - V1)/(V2 + V1)                                   # symmetric growth ...
fisher    = (V2 - V1)/math.sqrt(V1*V2)                              # ... != Fisher (distinct!)
arc_el    = ((Q2-Q1)/((Q2+Q1)/2)) / ((P2-P1)/((P2+P1)/2))           # arc elasticity
r = sorted(returns); k = max(1, math.ceil(len(r)*alpha)); es = sum(r[:k])/k   # CVaR/ES; alpha from Q
mu = statistics.fmean(v); theil = statistics.fmean([(x/mu)*math.log(x/mu) for x in v])   # x>0
n = len(v); mu = statistics.fmean(v)
gini = (sum(abs(a-b) for a in v for b in v)/(n*n)) / (2*mu)         # any N; NOT abs(x1-x2)/(x1+x2)
hhi  = sum(s*s for s in shares)                                     # fractions; *10000 only if "points"
boxcox = math.log(x) if lam == 0 else (x**lam - 1)/lam             # GIVEN lambda; do not re-estimate
# Macaulay duration: zero-coupon = its maturity in YEARS (single cash flow);
# a portfolio of zero-coupons = value-weighted average of maturities (always ≥ 0)
```

These corrections matter: the naive CVaR returns NaN whenever `int(n*alpha)==0` (e.g. 10 yearly returns at 95%); the naive 2-value Gini is 2× too large; symmetric and Fisher growth are NOT equal. Parameters (lambda, alpha, ddof, smoothing) ALWAYS come from the question text — never hardcode. "Geometric mean of VALUES" uses levels directly; "geometric annual RATE" uses `(end/start)**(1/n)-1`. For HP-filter / polynomial / any linear system, solve by hand with Gaussian elimination (no numpy); read the smoothing parameter from the question (annual data is often 6.25 or 100, never 1600).

## UNIT CONVERSION (#1 error pattern)

Tables show "thousands" or "millions" (check title, header, column, footnote — all four). Question "nominal dollars": thousands → ×1,000; millions → ×1,000,000. "in millions" + millions table → none; + thousands → ÷1,000. "in billions" + millions → ÷1,000. Parenthetical `(234)` = NEGATIVE. `n.a.`/`---` = not available, not zero.

## FISCAL vs CALENDAR YEAR

Before 1976: FY = Jul 1–Jun 30 (FY1975 = Jul 1974–Jun 1975); transition quarter Jul–Sep 1976. After 1976: FY = Oct 1–Sep 30 (FY2024 = Oct 2023–Sep 2024). "Calendar year" ≠ "fiscal year" — for CY you may sum individual months.

## DOMAIN TRAPS

"reported IN February 1938" → open `treasury_bulletin_1938_02.txt` ONLY; never substitute a retrospective table. "Capital"/"Paid-in capital" = original appropriation; "Total capital"/"Fund balance" = capital + earnings (use TOTAL unless "paid-in"). "Net receipts" = total − refunds. "Gross debt" includes intragovernmental; "Debt held by public" excludes it. "Outlays" ≠ "Expenditures" in scope. Hierarchical headers flatten as "Parent - Child"; trace the FULL path. If the question omits "reported in", prefer the later revised figure.

**Outlays-by-function row mapping (gross vs net):** each function block in FFO-5-style tables has rows `Outlays` (gross), `Proprietary receipts from the public` (negative), `Intrabudgetary transactions`, and `Total` (net, after offsets). Map the question's wording exactly: "NET <function> outlays" → the **Total** row (or the dedicated "Net interest" function); "<function> outlays EXCLUDING offsets and adjustments" → the gross **Outlays** row. (Verified both ways: CY1981 interest excluding offsets = gross rows = 93349; FY1981 NET interest = Total-row level ≈ 82.6B, not the 88.0B gross.)

**Ratio/percent questions — bind the denominator to the pronoun:** "what percent of THESE were…" refers to the quantity the question just defined (e.g. bids SUBMITTED / tenders RECEIVED), not a related one (tenders ACCEPTED). Write the denominator's definition next to the number before dividing, and keep numerator and denominator from the SAME source passage.

**Auction questions — narrative beats summary table:** each bulletin's narrative section states, per security, tenders RECEIVED ("totaled $X million"), ACCEPTED ("of which $Y million was accepted"), and the foreign/international and Government-account add-ons. Summary tables like PDO-4 "Amount tendered/issued" INCLUDE non-auction add-on awards to Government accounts and Federal Reserve banks (check the footnote), so they exceed the narrative's auction figures. "Bids submitted by investors" = the narrative's tenders-received figure. When a narrative figure and a table figure disagree, reconcile the difference arithmetically against the stated add-ons and use the figure whose DEFINITION matches the question's wording. Match a note by its MATURITY date ("maturing end of July 1984" → 2-year note dated ~Aug 1982, in the 1982_08 issue narrative).

**Split-entity subcolumns (verified zero-scorer):** when the question asks about an entity AS A WHOLE (e.g. "Defense Department") but the table splits it into subcolumns (`Defense Department > Military functions` + `> Civil functions`), the entity's value = the sum of its NAMED subcolumns ONLY — a single subcolumn is NOT the department, and a column whose flattened header says `Unnamed` (e.g. `Defense Department > Unnamed: 3_level_1`) is a PARSER MISATTRIBUTION belonging to a neighboring entity — NEVER include it. Verified: FY1955 Defense = 35532 (military) + 548 (civil) = 36080 from the 1958_10 issue; 35532 alone or +1993 (Unnamed) both score zero. Validate the mapping with the row identity: `sum(ALL departments as you mapped them) == printed row Total`. If that identity fails by >1%, your column mapping IS WRONG — re-map or recover the entity as `row Total − sum(other named entities)`. Do NOT proceed and blame "rounding/footnotes". For superlatives ("highest-spending department"), build each candidate's full total before comparing. For revised retrospective tables, use the LATEST issue whose table covers the year (FY1955 → the 1958 issue, not 1956/1958_02). When a question names a specific table (e.g. "Table FFO-3"), use THAT table's rows and definitions only. Honor every exclusion literally: "excluding territories and regional aggregates" means drop rows like "Other countries", "Total Europe"; "not weekly/52-week bills" means filter those rows out before aggregating.

### Aggregation Row Precedence (MANDATORY)

When a table contains both (a) detailed monthly/component rows AND (b) a reported Calendar Year, Fiscal Year, Total, Aggregate, or Summary row, and the question asks for a period total:

1. FIRST locate the reported aggregate row — grep the table for "Calendar yr", "Fiscal yr", "Total", "Annual". Use that printed value as the answer.
2. Do NOT compute the answer by summing monthly rows if a reported aggregate exists.
3. If you compute from monthly rows anyway, you MUST cross-check against the printed aggregate row.
4. When the aggregate row and the summed detail rows differ, prefer the PRINTED aggregate row.
5. Printed aggregate rows are authoritative: summing detail rows compounds per-row rounding (each ±1–2), which can push a hand-summed annual total past the 1% scorer tolerance.
6. Only sum monthly rows when no aggregate row exists, OR the question explicitly asks for a custom sum (e.g. "only the even-numbered months").

Note: "use only the reported values for individual calendar months" means use that year's monthly-reported data (not a fiscal-year figure) — it does NOT mean ignore the table's own aggregate row.

## OUTPUT (verified against the 1% scorer)

The final answer is **plain decimal digits only**: NEVER scientific notation (`9.3585e11` scores 0 — write `935851121560`); negatives as a leading minus (`-184.143`), NEVER accounting parens (`(184.143)` scores 0); MIRROR the requested unit scale ("in millions" → write `36080`, not `36080000000`); round exactly as asked; percent value → write `12.34` not `0.1234`; elasticities/ratios/correlations stay as plain decimals unless the question says percent; never write `NaN`/`inf`; multi-part `[a, b]` → all parts present, each within 1%.
