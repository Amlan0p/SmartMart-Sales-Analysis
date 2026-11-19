// ---------------------------------------------------------------------------
// Query name : Fact_Sales   (rename the query to exactly: Fact_Sales)
// Source     : data/processed/cleaned_sales_data.csv  (written by main.py)
// Grain      : one row = one order line. Order_ID is unique in the cleaned
//              file (verified: 14,970 rows = 14,970 distinct Order_ID).
// Principle  : Python already cleaned the data. This query only imports,
//              types and trims columns - it does NOT re-clean or re-derive.
// Refresh    : run `python main.py`, then Home > Refresh in Power BI.
// ---------------------------------------------------------------------------
let
    // 1. Read the CSV (UTF-8, comma delimited, 17 columns written by pandas)
    Source = Csv.Document(
        File.Contents(DataFolderPath & "cleaned_sales_data.csv"),
        [Delimiter = ",", Columns = 17, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),

    // 2. First row contains the column names
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // 3. Explicit data types. The "en-US" culture makes the decimal point and
    //    the ISO yyyy-mm-dd dates parse identically on every regional setting.
    TypedColumns = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Order_ID", type text},
            {"Order_Date", type date},
            {"Customer_ID", type text},
            {"Product", type text},
            {"Category", type text},
            {"Quantity", Int64.Type},
            {"Unit_Price", type number},
            {"Sales", type number},
            {"Region", type text},
            {"City", type text},
            {"Payment_Mode", type text},
            {"Year", Int64.Type},
            {"Month", Int64.Type},
            {"Month_Name", type text},
            {"Quarter", Int64.Type},
            {"Order_Value", type number},
            {"Customer_Type", type text}
        },
        "en-US"
    ),

    // 4. Remove columns that duplicate information supplied by other model
    //    tables, so there is ONE source of truth for each attribute:
    //    - Year/Month/Month_Name/Quarter -> come from Dim_Date
    //    - Category                      -> comes from Dim_Product
    //    - Order_Value                   -> identical to Sales (see Python
    //                                       preprocessing.add_derived_columns)
    RemovedDuplicateColumns = Table.RemoveColumns(
        TypedColumns,
        {"Year", "Month", "Month_Name", "Quarter", "Category", "Order_Value"}
    )
in
    RemovedDuplicateColumns
