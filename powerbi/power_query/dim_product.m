// ---------------------------------------------------------------------------
// Query name : Dim_Product   (rename the query to exactly: Dim_Product)
// Source     : data/processed/product_classification.csv
//              (written by src/powerbi_export.py -> build_product_dimension)
// Grain      : ONE row per Product (each product belongs to exactly one
//              Category in this dataset - verified).
// ---------------------------------------------------------------------------
let
    Source = Csv.Document(
        File.Contents(DataFolderPath & "product_classification.csv"),
        [Delimiter = ",", Columns = 5, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    TypedColumns = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Product", type text},
            {"Category", type text},
            {"Revenue_Rank", Int64.Type},
            {"ABC_Class", type text},
            {"Cumulative_Revenue_Percent", type number}
        },
        "en-US"
    )
in
    TypedColumns
