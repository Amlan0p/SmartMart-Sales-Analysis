"""
main.py

Main entry point for the SmartMart Sales Performance Analytics project.

Run with:
    python main.py

Optional flags (each runs only that stage; omitting all flags runs the
full pipeline, same as ``python main.py`` with no arguments):
    --generate-data   Generate the raw synthetic dataset only.
    --analyze         Load, clean and run the analysis only (no charts/reports).
    --report          Run the full pipeline and (re)generate all reports/charts.
    --all             Run the full pipeline (default behaviour).

Orchestrates the pipeline:
    Load Configuration -> Check/Generate Dataset -> Load Data ->
    Validate Data -> Clean Data -> Data Quality Report ->
    Save Processed Data -> Run Analysis (incl. consistency checks) ->
    Generate Charts + Executive Dashboard -> Generate Excel Report ->
    Generate Business Insights -> Export Power BI Dimensions ->
    Print Completion Summary

No business logic lives in this file - it only coordinates calls into
the ``src`` package modules.
"""

from __future__ import annotations

import argparse
import sys

import config
from src import (
    analysis,
    data_loader,
    data_quality,
    excel_report,
    generate_dataset,
    insights,
    powerbi_export,
    preprocessing,
    visualization,
)
from src.utils import configure_file_logging, ensure_directories, format_currency, get_logger

logger = get_logger("main")

TOTAL_STEPS = 9


def _print_banner() -> None:
    print("=" * 60)
    print("SMARTMART SALES PERFORMANCE ANALYTICS")
    print("=" * 60)
    print()


def _print_step(step_number: int, message: str) -> None:
    print(f"[{step_number}/{TOTAL_STEPS}] {message}")


def _ensure_dataset_exists() -> None:
    """Generate the raw synthetic dataset if it doesn't already exist
    on disk."""
    if config.RAW_SALES_DATA_PATH.exists():
        logger.info("Raw dataset already exists at %s. Skipping generation.", config.RAW_SALES_DATA_PATH)
        return

    logger.info("Raw dataset not found. Generating synthetic dataset...")
    dataframe = generate_dataset.generate_raw_dataset()
    generate_dataset.save_raw_dataset(dataframe)


def _prepare_output_dirs() -> None:
    ensure_directories(
        config.RAW_DATA_DIR,
        config.PROCESSED_DATA_DIR,
        config.CHARTS_DIR,
        config.REPORTS_DIR,
        config.RESULTS_DIR,
        config.LOGS_DIR,
    )
    configure_file_logging(config.APPLICATION_LOG_PATH)


def run_pipeline() -> dict:
    """Run the full analytics pipeline end-to-end and return the
    analysis results dictionary (useful for testing)."""
    _print_banner()
    _prepare_output_dirs()

    _print_step(1, "Checking and loading dataset...")
    _ensure_dataset_exists()
    raw_df = data_loader.load_sales_data(config.RAW_SALES_DATA_PATH)

    _print_step(2, "Validating data...")
    data_loader.validate_columns(raw_df)

    _print_step(3, "Cleaning data...")
    cleaned_df = preprocessing.clean_dataset(raw_df)
    preprocessing.save_cleaned_dataset(cleaned_df)

    _print_step(4, "Generating data quality report...")
    data_quality.save_data_quality_report(raw_df, cleaned_df)

    _print_step(5, "Running analysis...")
    results = analysis.run_full_analysis(cleaned_df)
    if results.get("consistency_warnings"):
        print("  WARNING: one or more data consistency checks failed - see application.log.")

    _print_step(6, "Generating visualizations and executive dashboard...")
    visualization.generate_all_charts(results)

    _print_step(7, "Creating Excel report...")
    findings = insights.build_findings(results)
    excel_report.build_excel_report(results, findings=findings)

    _print_step(8, "Generating business insights...")
    insights.save_business_insights(results)

    _print_step(9, "Exporting Power BI dimension tables...")
    powerbi_export.export_powerbi_tables(results)

    _print_completion_summary(results)

    return results


def _print_completion_summary(results: dict) -> None:
    summary = results["summary"]

    print()
    print("=" * 60)
    print("ANALYSIS COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print()
    print(f"Total Revenue    : {format_currency(summary['Total Revenue'])}")
    print(f"Total Orders     : {summary['Total Orders']:,}")
    print(f"Customers        : {summary['Total Customers']:,}")
    print(f"Quantity Sold    : {summary['Total Quantity Sold']:,}")
    print(f"Avg Order Value  : {format_currency(summary['Average Order Value'])}")
    print()
    print("Outputs:")
    print(f"  - Processed dataset   : {config.CLEANED_SALES_DATA_PATH}")
    print(f"  - Charts              : {config.CHARTS_DIR}")
    print(f"  - Executive dashboard : {config.EXECUTIVE_DASHBOARD_PATH}")
    print(f"  - Excel report        : {config.EXCEL_REPORT_PATH}")
    print(f"  - Data quality report : {config.DATA_QUALITY_REPORT_PATH}")
    print(f"  - Business insights   : {config.BUSINESS_INSIGHTS_PATH}")
    print(f"  - Power BI dimensions : {config.CUSTOMER_SEGMENTS_PATH.name}, {config.PRODUCT_CLASSIFICATION_PATH.name}")
    print(f"  - Application log     : {config.APPLICATION_LOG_PATH}")
    print()


def _run_generate_data_only() -> None:
    _print_banner()
    _prepare_output_dirs()
    print("Generating synthetic raw dataset only...")
    dataframe = generate_dataset.generate_raw_dataset()
    path = generate_dataset.save_raw_dataset(dataframe)
    print(f"Raw dataset written to: {path}")


def _run_analyze_only() -> dict:
    _print_banner()
    _prepare_output_dirs()
    print("Running load -> validate -> clean -> analyze only (no charts/reports)...")
    _ensure_dataset_exists()
    raw_df = data_loader.load_sales_data(config.RAW_SALES_DATA_PATH)
    data_loader.validate_columns(raw_df)
    cleaned_df = preprocessing.clean_dataset(raw_df)
    preprocessing.save_cleaned_dataset(cleaned_df)
    results = analysis.run_full_analysis(cleaned_df)
    print(f"Total Revenue: {format_currency(results['summary']['Total Revenue'])}")
    return results


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SmartMart Sales Performance Analytics - run 'python main.py' for the full pipeline."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Run the full pipeline (default).")
    group.add_argument("--generate-data", action="store_true", help="Only (re)generate the raw synthetic dataset.")
    group.add_argument("--analyze", action="store_true", help="Only load, clean and analyze (no charts/reports).")
    group.add_argument("--report", action="store_true", help="Run the full pipeline and regenerate all reports.")
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args()
    try:
        if args.generate_data:
            _run_generate_data_only()
        elif args.analyze:
            _run_analyze_only()
        else:
            # --all, --report, or no flags at all: run the full pipeline.
            run_pipeline()
        return 0
    except (data_loader.DatasetNotFoundError, data_loader.EmptyDatasetError,
            data_loader.MissingColumnsError) as exc:
        logger.error("Data error: %s", exc)
        print(f"\nERROR: {exc}")
        return 1
    except PermissionError as exc:
        logger.error("Permission error while writing output: %s", exc)
        print(f"\nERROR: Permission denied while writing output files: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - top-level safety net for CLI use
        logger.exception("Unexpected error occurred during pipeline execution.")
        print(f"\nUNEXPECTED ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
