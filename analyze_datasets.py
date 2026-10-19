import os
import pandas as pd

dfs = []

files = [f for f in os.listdir('.') if f.endswith('.csv') or f.endswith('.xlsx')]

for f in sorted(files):
    if f == 'output_2024SeatMatrix.xlsx':
        continue # empty/corrupted file
    filepath = f
    try:
        is_excel = False
        with open(filepath, 'rb') as fp:
            header_bytes = fp.read(4)
            if header_bytes.startswith(b'PK\x03\x04'):
                is_excel = True
        
        if is_excel or f.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath, encoding_errors='ignore')
            
        print(f"Loaded {f}: shape={df.shape}")
        dfs.append(df)
    except Exception as e:
        print(f"Error loading {f}: {e}")

if dfs:
    full_df = pd.concat(dfs, ignore_index=True)
    print("\n--- Combined Dataset Overview ---")
    print(f"Total Rows: {len(full_df)}")
    print("Columns:", full_df.columns.tolist())
    print("\nDistinct Years:", full_df['Year'].unique())
    print("Distinct CAP Rounds:", full_df['CAP Round'].unique())
    print("Distinct Colleges:", full_df['College Code'].nunique())
    print("Distinct Courses:", full_df['Course Name'].nunique())
    print("Distinct Categories:", full_df['Category'].dropna().unique()[:20])
    print("Distinct Seat Types:", full_df['Seat Type'].dropna().unique()[:20])
    print("Distinct Statuses:", full_df['Status'].dropna().unique()[:10])
    print("\nMissing Values:")
    print(full_df.isnull().sum())
    print("\nSample Rows:")
    print(full_df.head(3))
