// ---------------------------------------------------------------------------
// Query name  : DataFolderPath          (Power Query PARAMETER, type Text)
// Purpose     : Single place that stores the folder holding the three CSVs
//               exported by the Python pipeline (data/processed/).
// How to use  : Home > Transform data > Manage Parameters > New Parameter
//               Name = DataFolderPath, Type = Text, Required = Yes,
//               Current Value = full path ENDING WITH A BACKSLASH, e.g.
//               C:\Projects\SmartMart-Sales-Analytics\data\processed\
// If you create it through the Advanced Editor instead, paste the single
// line below into a blank query named DataFolderPath (edit the path first):
// ---------------------------------------------------------------------------
"C:\Projects\SmartMart-Sales-Analytics\data\processed\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
