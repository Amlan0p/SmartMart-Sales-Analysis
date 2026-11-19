# Power BI layer - SmartMart Sales Performance Analytics

Power BI consumes the CSV files produced by the Python pipeline. It does **not** repeat the cleaning: Python stays the single source of data preparation, KPI logic and insights.

```
python main.py  ->  data/processed/{cleaned_sales_data, customer_segments, product_classification}.csv
                ->  Power Query (3 CSV queries + 1 parameter)  ->  star-schema model
                ->  DAX (calendar + 46 measures)               ->  4 report pages
```

| Folder / file | Purpose |
|---|---|
| `BUILD_GUIDE.md` | **Start here.** Step-by-step instructions to build and verify the report |
| `power_query/` | M code for `Fact_Sales`, `Dim_Customer`, `Dim_Product` and the `DataFolderPath` parameter |
| `dax/date_table.dax`, `dax/measures.dax` | Calendar table and all measures |
| `data_model/model_documentation.md` | Tables, keys, relationships, grain, segmentation method |
| `dashboard_design/` | Specification, requirement traceability, colour theme (`theme/SmartMart_Theme.json`) |
| `verification/` | Static validator, Python-vs-DAX reconciliation script and its generated report |
| `screenshots/` | Place real Power BI screenshots here (empty until you build the dashboard) |

## Status

| | |
|---|---|
| Source files for the model, queries, measures, theme and guide | Ready |
| Static validation and Python-vs-DAX-emulation reconciliation | Run, results in `verification/` |
| `.pbix` dashboard and screenshots | Delivered: `SmartMart_Sales_Dashboard_Final.pbix`, `screenshots/`. Opened and tested in Power BI Desktop by the project team; the audit's static inspection could not read the compressed model |

## Verification commands

```bash
python powerbi/verification/validate_powerbi_assets.py
python powerbi/verification/reconcile_python_vs_dax.py
```
