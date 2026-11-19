"""
validate_powerbi_assets.py

STATIC validation of the Power BI source files. Run from the project root:

    python powerbi/verification/validate_powerbi_assets.py

IMPORTANT - what this does and does not prove
---------------------------------------------
There is no DAX or Power Query engine in a plain Python environment, so this
script cannot execute the formulas. It performs *static* checks only:

* DAX  : balanced brackets/quotes, unique measure names, every [Measure]
         reference resolves, every Table[Column] reference exists in the model,
         only an allow-list of DAX functions is used (catches typos), and all
         measures required by the assignment exist.
* M    : balanced brackets, a let/in structure, and - most usefully - the
         column lists and ``Columns = N`` values are compared with the REAL
         header of the CSV files produced by the pipeline.

A pass here means "no static problems found". The formulas still have to be
run in Power BI Desktop (see powerbi/BUILD_GUIDE.md section 12).
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POWERBI_DIR = PROJECT_ROOT / "powerbi"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ALLOWED_FUNCTIONS = {
    "SUM", "DISTINCTCOUNT", "DIVIDE", "CALCULATE", "DATEADD", "SAMEPERIODLASTYEAR",
    "MAX", "MIN", "REMOVEFILTERS", "TOTALYTD", "FILTER", "ALLSELECTED", "CONCATENATEX",
    "TOPN", "RANKX", "MAXX", "MINX", "AVERAGEX", "SUMX", "VALUES", "IF", "ISBLANK",
    "BLANK", "CALENDAR", "DATE", "YEAR", "ADDCOLUMNS", "QUARTER", "MONTH", "FORMAT",
    "WEEKDAY", "ROUND",
}
DAX_KEYWORDS = {"VAR", "RETURN", "ASC", "DESC", "Dense", "MONTH"}

REQUIRED_MEASURES = [
    "Total Revenue", "Total Orders", "Total Customers", "Total Units Sold",
    "Average Order Value", "Average Selling Price", "Revenue Growth %",
    "YoY Revenue Growth %", "Category Revenue Contribution %", "Regional Revenue",
    "Customer Revenue", "Repeat Customers", "Customer Contribution %",
    "Product Contribution %",
]

# CSV file -> table name used in the Power BI model
TABLE_SOURCES = {
    "Fact_Sales": "cleaned_sales_data.csv",
    "Dim_Customer": "customer_segments.csv",
    "Dim_Product": "product_classification.csv",
}
FACT_REMOVED_COLUMNS = ["Year", "Month", "Month_Name", "Quarter", "Category", "Order_Value"]
DIM_DATE_COLUMNS = [
    "Date", "Year", "Quarter Number", "Quarter", "Month Number", "Month Name",
    "Month Short", "Year-Month", "Month Start", "Day of Week Number", "Day of Week",
]

failures: list[str] = []
passes: list[str] = []


def check(condition: bool, message: str) -> None:
    (passes if condition else failures).append(message)


def read_csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def strip_comments(text: str) -> str:
    return re.sub(r"//[^\n]*", "", text)


def parse_measures(path: Path) -> dict[str, str]:
    """Split measures.dax into {name: body}. A measure starts on a line that
    begins at column 0 with 'Name ='."""
    measures: dict[str, str] = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("//") or not line.strip():
            continue
        match = re.match(r"^([A-Za-z][^=\[\]]*?)\s*=\s*(.*)$", line) if not line.startswith(" ") else None
        if match:
            current = match.group(1).strip()
            if current in measures:
                failures.append(f"Duplicate measure name: {current}")
            measures[current] = match.group(2)
        elif current is not None:
            measures[current] += "\n" + line
    return {name: strip_comments(body) for name, body in measures.items()}


def balanced(text: str) -> bool:
    text = re.sub(r'"[^"]*"', '""', text)
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for ch in text:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack and text.count('"') % 2 == 0


def validate_dax() -> None:
    model_columns: dict[str, set[str]] = {}
    for table, csv_name in TABLE_SOURCES.items():
        header = read_csv_header(PROCESSED_DIR / csv_name)
        if table == "Fact_Sales":
            header = [c for c in header if c not in FACT_REMOVED_COLUMNS]
        model_columns[table] = set(header)
    model_columns["Dim_Date"] = set(DIM_DATE_COLUMNS)

    measures = parse_measures(POWERBI_DIR / "dax" / "measures.dax")
    check(len(measures) >= len(REQUIRED_MEASURES), f"measures.dax defines {len(measures)} measures")
    for name in REQUIRED_MEASURES:
        check(name in measures, f"Required measure present: {name}")

    for name, body in measures.items():
        check(balanced(body), f"Balanced brackets/quotes: {name}")
        for table, column in re.findall(r"\b([A-Za-z_]+)\[([^\]]+)\]", body):
            ok = table in model_columns and column in model_columns[table]
            check(ok, f"Column reference resolves: {name} -> {table}[{column}]")
        unqualified = re.findall(r"(?<![A-Za-z0-9_])\[([^\]]+)\]", body)
        for ref in unqualified:
            check(ref in measures, f"Measure reference resolves: {name} -> [{ref}]")
        for function in re.findall(r"\b([A-Z][A-Za-z]+)\s*\(", re.sub(r"\[[^\]]*\]", "", re.sub(r'"[^"]*"', "", body))):
            check(function.upper() in ALLOWED_FUNCTIONS or function in DAX_KEYWORDS,
                  f"Known DAX function: {name} -> {function}")
        check("RETURN" not in body or "VAR" in body, f"VAR/RETURN pairing: {name}")

    date_text = strip_comments((POWERBI_DIR / "dax" / "date_table.dax").read_text(encoding="utf-8"))
    check(balanced(date_text), "Balanced brackets/quotes: Dim_Date table")
    for column in DIM_DATE_COLUMNS[1:]:
        check(f'"{column}"' in date_text, f"Dim_Date defines column: {column}")
    for function in re.findall(r"\b([A-Z][A-Za-z]+)\s*\(", re.sub(r'"[^"]*"', "", date_text)):
        check(function.upper() in ALLOWED_FUNCTIONS, f"Known DAX function: Dim_Date -> {function}")


def validate_power_query() -> None:
    files = {
        "Fact_Sales": "sales_data.m",
        "Dim_Customer": "dim_customer.m",
        "Dim_Product": "dim_product.m",
    }
    for table, filename in files.items():
        text = (POWERBI_DIR / "power_query" / filename).read_text(encoding="utf-8")
        code = strip_comments(text)
        check(balanced(code), f"M brackets balanced: {filename}")
        check(re.search(r"\blet\b", code) and re.search(r"\bin\b", code), f"M has let/in: {filename}")
        header = read_csv_header(PROCESSED_DIR / TABLE_SOURCES[table])
        columns_declared = int(re.search(r"Columns\s*=\s*(\d+)", code).group(1))
        check(columns_declared == len(header),
              f"{filename}: Columns = {columns_declared} matches CSV header ({len(header)})")
        typed = re.search(r"TransformColumnTypes\((.*?)\"en-US\"", code, re.S).group(1)
        typed_names = re.findall(r'\{"([^"]+)",', typed)
        check(typed_names == header, f"{filename}: typed column list equals CSV header order")
        check(f'"{TABLE_SOURCES[table]}"' in code, f"{filename}: references {TABLE_SOURCES[table]}")
        if table == "Fact_Sales":
            removed = re.search(r"RemoveColumns\((.*?)\)\s*in", code, re.S).group(1)
            removed_names = re.findall(r'"([^"]+)"', removed)
            check(set(removed_names) == set(FACT_REMOVED_COLUMNS),
                  "sales_data.m removes exactly the documented duplicate columns")
            check(all(c in header for c in removed_names), "All removed columns exist in the CSV")
    param = strip_comments((POWERBI_DIR / "power_query" / "DataFolderPath.m").read_text(encoding="utf-8"))
    check("IsParameterQuery = true" in param, "DataFolderPath.m declares a Power Query parameter")


def main() -> int:
    try:
        validate_dax()
        validate_power_query()
    except FileNotFoundError as exc:
        print(f"ERROR: required file missing ({exc}). Run `python main.py` first.")
        return 2
    print(f"Static checks passed: {len(passes)}")
    if failures:
        print(f"Static checks FAILED: {len(failures)}")
        for message in failures:
            print("  FAIL:", message)
        return 1
    print("All static checks passed. (Static only - formulas not executed in Power BI.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
