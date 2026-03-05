import pandas as pd
import os

filepath = r'd:\deleviry-crm420-main\deleviry-crm420-main\uploads\SalesReport_2026-01-26.xlsx'
if os.path.exists(filepath):
    df = pd.read_excel(filepath)
    print(f"Columns in {os.path.basename(filepath)}:")
    print(df.columns.tolist())
    print("\nFirst 3 rows:")
    print(df.head(3))
else:
    print(f"File not found: {filepath}")
