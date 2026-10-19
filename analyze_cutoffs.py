import os
import pandas as pd

cutoff_files = [f for f in os.listdir('.') if f.startswith('temp_cutoff_')]

dfs = []
for f in sorted(cutoff_files):
    filepath = f
    is_excel = False
    with open(filepath, 'rb') as fp:
        if fp.read(4).startswith(b'PK\x03\x04'):
            is_excel = True
    
    if is_excel:
        df = pd.read_excel(filepath)
    else:
        df = pd.read_csv(filepath, encoding_errors='ignore')
    
    print(f"{f}: shape={df.shape}, nulls_percentile={df['Cutoff Percentile'].isnull().sum()}, nulls_college={df['College Name'].isnull().sum()}")
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)
print("\n=== CLEAN CUTOFF DATASET SUMMARY ===")
print("Total records:", len(df_all))
print("Columns:", df_all.columns.tolist())
print("Years:", df_all['Year'].value_counts(dropna=False).to_dict())
print("CAP Rounds:", df_all['CAP Round'].value_counts(dropna=False).to_dict())
print("Number of Unique Colleges:", df_all['College Code'].nunique())
print("Number of Unique Choice Codes:", df_all['Choice Code'].nunique())
print("Number of Unique Courses:", df_all['Course Name'].nunique())
print("Sample Course Names:\n", df_all['Course Name'].value_counts().head(10))
print("Sample Categories:\n", df_all['Category'].value_counts().head(15))
print("Sample Seat Types:\n", df_all['Seat Type'].value_counts().head(15))
print("Sample Statuses:\n", df_all['Status'].value_counts().head(10))
print("Cutoff Rank Range:", df_all['Cutoff Rank'].min(), "to", df_all['Cutoff Rank'].max())
print("Cutoff Percentile Range:", df_all['Cutoff Percentile'].min(), "to", df_all['Cutoff Percentile'].max())
print("\nSample records:")
print(df_all[['Year', 'CAP Round', 'College Code', 'College Name', 'Course Name', 'Category', 'Cutoff Rank', 'Cutoff Percentile']].head(5))
