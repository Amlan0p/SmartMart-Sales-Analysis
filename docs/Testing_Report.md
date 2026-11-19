# SmartMart Testing Report

Prepared: 4 November 2026 (updated the same day after a real pytest run). Everything below was actually executed in the preparation environments (no Power BI Desktop available in either). Items that were **not** done are listed in section 6.

## 1. Summary

| Area | Result |
|---|---|
| Clean-state regeneration (`data/` and `outputs/` deleted, then `python main.py`) | Completed, exit code 0 |
| Regenerated raw and cleaned CSV vs original upload | **Byte-identical** (SHA-256 `20fd4be9140e50a3...` and `8ceccb305fe64d9a...`) |
| Regenerated `business_insights.txt` vs original | Identical |
| Automated tests | **35 passed, 0 failed** (21 original + 14 added); real pytest 9.1.1 |
| Static validation of DAX / Power Query files | 366 checks passed, 0 failed |
| Python vs DAX-equivalent reconciliation | 109 checks: 106 match, 3 expected-by-design differences, 0 unexplained |
| Documentation figures vs real outputs | 39 of 39 key figures found in the rendered PDF |
| Documentation PDF | 45 pages; logo, title header and "Page X of Y" present on all 45 pages |

## 2. How the tests were run (important)

Two runs exist. The first preparation environment had no network, so the unchanged test files were run with a small stand-in runner (`pytest.raises`, `pytest.skip`, `tmp_path` only). In the update session the suite was run with **real pytest 9.1.1** (Python 3.13.18, pandas 3.0.5) on a copy of the project after a clean `python main.py`: **35 passed, 0 failed, 0 skipped** (`pytest -q`, 1.33 s). `outputs/results/test_run_summary.txt` now records the real pytest result. The stand-in run gave the same 35 passes. Running `pytest -q` on the Windows machine is still worth doing once, but is no longer an open item.

## 3. Test inventory

| Module | Tests | Passed | Covers |
|---|---:|---:|---|
| `test_analysis` | 9 | 9 | KPIs and aggregations with hand-computed expectations (original) |
| `test_data_loader` | 5 | 5 | loader exceptions and validation (original) |
| `test_output_integrity` | 8 | 8 | real generated files: dataset, 10 charts, Excel sheets and totals, data-quality report, insights, no notebooks, Power BI files present, dimensions align with sales (new) |
| `test_powerbi_export` | 6 | 6 | dimension tables: unique keys, rejects duplicates, no orphans, files written (new) |
| `test_preprocessing` | 7 | 7 | cleaning, types, derived columns (original) |
| **Total** | **35** | **35** | |

Individual results are in `outputs/results/test_run_summary.txt`.

## 4. Requirement-by-requirement checklist

| # | Required check | Status | Evidence |
|---|---|---|---|
| 1 | Run the complete pipeline from a clean state | Done | Section 1; `python main.py` exit code 0 |
| 2 | Run all existing tests | Done (real pytest 9.1.1) | 21 original tests pass; 35/35 in total |
| 3 | Add tests for new functionality | Done | `test_powerbi_export.py` (6), `test_output_integrity.py` (8) |
| 4 | Verify generated charts | Done | 10 PNGs checked for valid PNG header and size; executive dashboard and other charts also inspected visually (as embedded in the PDF) |
| 5 | Verify Excel workbooks and worksheets | Done | Required sheets present; Summary totals equal values recomputed from the cleaned CSV; data-quality row counts match |
| 6 | Verify business insights | Done | File identical to original; quotes the recomputed total revenue |
| 7 | Verify cleaned dataset integrity | Done | No nulls/duplicates, unique Order_ID, positive values, Sales = Quantity x Unit_Price, dates in range |
| 8 | Validate DAX as far as possible | Done, static only | `validate_powerbi_assets.py`; negative test confirmed the checker detects typos |
| 9 | Validate Power Query M as far as possible | Done, static only | Column lists and `Columns = N` compared with the real CSV headers |
| 10 | Compare KPI definitions across Python and Power BI | Done in pandas emulation | `powerbi/verification/reconciliation_report.md` |
| 11 | Check file paths | Done | All config paths exist after the run; Power Query uses a single parameter `DataFolderPath` (must be set by you) |
| 12 | No notebook files | Done | `test_no_notebook_files_in_project` |
| 13 | No working functionality removed | Done | Only `config.py` and `main.py` differ from the original (additive); the other 14 original `.py` files are identical; all original tests pass; outputs identical |
| 14 | Documentation values match outputs | Done | `docs/verify_documentation_numbers.py`: 39/39 |
| 15 | Inspect documentation PDF page by page | Done at contact-sheet level; selected pages at reading resolution | All 45 pages reviewed in contact sheets; cover, TOC, code pages, table pages, chart pages, wireframe pages and header/footer inspected at reading resolution. Layout defects found (equal-width tables, header/footer tab stops, stranded headings, spill-over lines) were fixed and re-checked |

## 5. Findings made by testing

1. **ABC boundary (Jeans, 95.004%).** Reconciliation showed the first draft of the DAX ABC measure disagreed with Python for one product, because Python rounds the cumulative percentage to 2 decimals before applying the 95% threshold. The DAX measure was aligned and commented; Python was left unchanged.
2. **Repeat customers under filters.** The whole-period Python definition differs from a context-sensitive DAX count by design. Two measures are provided and the difference is documented.
3. **Unreachable 'Occasional' segment.** Found while documenting; left unchanged (existing tested behaviour) and listed as future work.

## 6. NOT done - requires manual work

- (Superseded by section 7.) At the time of this section no `.pbix` existed and the preparers had no Power BI Desktop. The project team has since built, opened and tested the report in Power BI Desktop; see section 7. The Python-side checks in this section (static validation, pandas emulation) are not Power BI runs.
- Re-verified in the update session with real pytest: 35 passed; `validate_powerbi_assets.py` 366 static checks passed; `reconcile_python_vs_dax.py` 106 matched / 3 expected / 0 unexplained; `python main.py` regenerated all three processed CSVs and the raw CSV byte-identical (SHA-256 compared). Still static or pandas-emulated only, never Power BI.
- Word-specific rendering of the DOCX was not checked; the PDF was produced by LibreOffice. If Word shifts a page, right-click the table of contents and choose *Update Field*.

## 7. Final audit of the delivered Power BI report (5 November 2026)

Performed on `powerbi/SmartMart_Sales_Dashboard_Final.pbix` (SHA-256 `5e5decdaac98...a1101a`, byte-identical to the file supplied) and the team's four screenshots. The `.pbix` was only read, never modified.

| Check | Result | How |
|---|---|---|
| Four pages present with the expected names and order | **Pass** | `powerbi/verification/inspect_pbix.py` reads `Report/definition/pages` |
| Five slicers (Date, Region, Category, Product, Payment_Mode) on every page, synchronised | **Pass** | same script; visible on page 1, hidden on pages 2-4 |
| Visual inventory | 13 / 11 / 12 / 12 visuals per page (including 5 slicers each) | same script; report in `powerbi/verification/pbix_inspection_report.md` |
| Figures visible in the screenshots equal Python | **Pass** (10 card values, 6 payment shares, 5 regions + total, 18 product rows, top-15 customer order) | screenshots zoomed and compared with values recomputed from `cleaned_sales_data.csv`; documentation Section 22.6 |
| Top N / Bottom N filters (specification: 5 visuals) | **Fail** - none applied | `inspect_pbix.py` |
| Chronological trend axis | **Fail** - both Year-Month line charts are sorted by value descending | `inspect_pbix.py`, visible in screenshot 01 |
| Custom visual titles and alt text | **Fail** - automatic titles only; no alt text | `inspect_pbix.py` |
| Customer-segmentation visual, Pareto cumulative line, highest/lowest region cards | **Not built** | `inspect_pbix.py` and screenshots |
| Semantic model inside the `.pbix` (measure formulas, relationships, Power Query steps) | **Not independently inspected by the audit** | the `DataModel` part is XPress9-compressed and cannot be read outside Power BI |
| Report opened and tested in Power BI Desktop | **Done by the project team** (manual testing) | all four pages load and display their visuals correctly; the team checked dashboard functionality and slicer interactions. Reported by the team; the audit did not reproduce the session and records no further test details |

