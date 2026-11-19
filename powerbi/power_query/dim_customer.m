// ---------------------------------------------------------------------------
// Query name : Dim_Customer   (rename the query to exactly: Dim_Customer)
// Source     : data/processed/customer_segments.csv
//              (written by src/powerbi_export.py -> build_customer_dimension)
// Grain      : ONE row per Customer_ID. Uniqueness is enforced in Python
//              (ValueError on duplicates) and covered by
//              tests/test_powerbi_export.py. That is what makes the
//              Dim_Customer -> Fact_Sales relationship one-to-many.
// ---------------------------------------------------------------------------
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "customer_segments.csv"),
        [Delimiter = ",", Columns = 10, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    TypedColumns = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Customer_ID", type text},
            {"Segment", type text},
            {"R_Score", Int64.Type},
            {"F_Score", Int64.Type},
            {"M_Score", Int64.Type},
            {"RFM_Score", Int64.Type},
            {"Recency_Days", Int64.Type},
            {"Frequency", Int64.Type},
            {"Monetary", type number},
            {"Last_Order_Date", type date}
        },
        "en-US"
    )
in
    TypedColumns
