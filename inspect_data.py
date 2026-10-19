import os
import zipfile
import pandas as pd

files = os.listdir('.')
print("Files in workspace:", files)

for f in sorted(files):
    filepath = f
    if not (f.endswith('.csv') or f.endswith('.xlsx')):
        continue
    size = os.path.getsize(filepath)
    print(f"\n--- Checking File: {f} (size: {size} bytes) ---")
    
    is_excel = False
    with open(filepath, 'rb') as fp:
        header_bytes = fp.read(4)
        if header_bytes.startswith(b'PK\x03\x04'):
            is_excel = True
            
    try:
        if is_excel or f.endswith('.xlsx'):
            print(f"{f} detected as Excel format.")
            excel_file = pd.ExcelFile(filepath)
            print("Sheet names:", excel_file.sheet_names)
            for s in excel_file.sheet_names[:2]:
                df = pd.read_excel(filepath, sheet_name=s, nrows=3)
                print(f"Sheet '{s}' shape sample cols:", df.columns.tolist())
        else:
            df = pd.read_csv(filepath, nrows=5, encoding_errors='ignore')
            print(f"CSV columns ({len(df.columns)}):", df.columns.tolist())
            print(df.head(2))
    except Exception as e:
        print(f"Error reading {f}: {e}")
