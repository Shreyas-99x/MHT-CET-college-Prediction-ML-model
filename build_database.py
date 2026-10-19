import os
import re
import sqlite3
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

print("--- Starting Enhanced MHT CET Database Build & Normalization ---")

cutoff_files = [f for f in os.listdir('.') if f.startswith('temp_cutoff_')]
print(f"Found {len(cutoff_files)} cutoff dataset files: {cutoff_files}")

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
        df = pd.read_csv(filepath, encoding_errors='ignore', engine='python')
    
    # Strip whitespace & embedded newlines from all object/string columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(r'[\r\n]+', ' ', regex=True).str.strip()

    # Extract year/cap from filename if missing or nan
    year_match = re.search(r'202[3-5]', f)
    cap_match = re.search(r'cap_(\d)', f)
    if year_match and 'Year' in df.columns:
        df['Year'] = df['Year'].fillna(int(year_match.group(0)))
    if cap_match and 'CAP Round' in df.columns:
        df['CAP Round'] = df['CAP Round'].fillna(int(cap_match.group(1)))
        
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)
print(f"Loaded total raw records: {len(df_all)}")

# Coerce numeric columns
df_all['Year'] = pd.to_numeric(df_all['Year'], errors='coerce')
df_all['CAP Round'] = pd.to_numeric(df_all['CAP Round'], errors='coerce')
df_all['College Code'] = pd.to_numeric(df_all['College Code'], errors='coerce')
df_all['Cutoff Rank'] = pd.to_numeric(df_all['Cutoff Rank'], errors='coerce')
df_all['Cutoff Percentile'] = pd.to_numeric(df_all['Cutoff Percentile'], errors='coerce')

# Drop missing critical columns
df_all = df_all.dropna(subset=['College Code', 'Course Name', 'Cutoff Percentile', 'Cutoff Rank', 'Year', 'CAP Round'])

df_all['Year'] = df_all['Year'].astype(int)
df_all['CAP Round'] = df_all['CAP Round'].astype(int)
df_all['College Code'] = df_all['College Code'].astype(int)
df_all['Cutoff Rank'] = df_all['Cutoff Rank'].astype(int)
df_all['Cutoff Percentile'] = df_all['Cutoff Percentile'].astype(float).round(4)

# 1. Course Name Standardization
course_mapping = {
    "Artificial Intelligence (AI) and Data Science": "Artificial Intelligence & Data Science",
    "Artificial Intelligence and Data Science": "Artificial Intelligence & Data Science",
    "Computer Science and Engineering(Artificial Intelligence and Machine Learning)": "Computer Science & Engineering (AI & ML)",
    "Computer Science and Engineering (Artificial Intelligence and Machine Learning)": "Computer Science & Engineering (AI & ML)",
    "Computer Science and Engineering(Data Science)": "Computer Science & Engineering (Data Science)",
    "Computer Science and Engineering (Data Science)": "Computer Science & Engineering (Data Science)",
    "Computer Science and Engineering": "Computer Science & Engineering",
    "Computer Engineering": "Computer Engineering",
    "Information Technology": "Information Technology",
    "Electronics and Telecommunication Engg": "Electronics & Telecommunication Engineering",
    "Electronics and Telecommunication Engineering": "Electronics & Telecommunication Engineering",
    "Mechanical Engineering": "Mechanical Engineering",
    "Civil Engineering": "Civil Engineering",
    "Electrical Engineering": "Electrical Engineering",
    "Chemical Engineering": "Chemical Engineering",
    "Robotics and Automation": "Robotics & Automation",
    "Automation and Robotics": "Robotics & Automation"
}

df_all['Course Name Clean'] = df_all['Course Name'].map(lambda x: course_mapping.get(str(x).strip(), str(x).strip()))

# 2. Extract District / Region / City from College Name
def extract_region(name):
    name_upper = str(name).upper()
    cities = [
        "PUNE", "MUMBAI", "THANE", "NAVI MUMBAI", "NAGPUR", "NASHIK", 
        "AURANGABAD", "CHHATRAPATI SAMBHAJINAGAR", "KOLHAPUR", "SOLAPUR", 
        "SANGLI", "AMRAVATI", "NANDED", "JALGAON", "AHMEDNAGAR", "RATNAGIRI", 
        "SATARA", "LAKHANDUR", "LATOR", "LATUR", "KARAD", "AKOLA", "CHANDRAPUR",
        "WARDHA", "BHANDARA", "GONDIYA", "YAVATMAL", "DHULE", "SHIRPUR", "BARAMATI",
        "PANVEL", "VASAI", "PALGHAR", "LONAVALA"
    ]
    for city in cities:
        if city in name_upper:
            if city in ["AURANGABAD", "CHHATRAPATI SAMBHAJINAGAR"]:
                return "Chhatrapati Sambhajinagar"
            if city in ["LATUR", "LATOR"]:
                return "Latur"
            return city.title()
    return "Other / Maharashtra"

df_all['District'] = df_all['College Name'].apply(extract_region)

# 3. Categorization & Fine-Grained Quota Parsing
def map_category_group(cat):
    cat_str = str(cat).upper().replace(' ', '')
    if any(k in cat_str for k in ['GOPEN', 'LOPEN', 'AI']):
        return 'OPEN'
    elif 'OBC' in cat_str:
        return 'OBC'
    elif 'SC' in cat_str and 'DEF' not in cat_str:
        return 'SC'
    elif 'ST' in cat_str:
        return 'ST'
    elif any(vj in cat_str for vj in ['VJ', 'NT1', 'NT2', 'NT3', 'NT']):
        return 'VJ / NT'
    elif 'EWS' in cat_str:
        return 'EWS'
    elif 'TFWS' in cat_str:
        return 'TFWS'
    elif 'PWD' in cat_str:
        return 'PWD'
    elif 'DEF' in cat_str:
        return 'DEFENCE'
    elif 'MINORITY' in cat_str or 'MI' in cat_str:
        return 'MINORITY'
    return 'OTHER'

def parse_gender_quota(cat):
    cat_str = str(cat).upper().replace(' ', '')
    if cat_str.startswith('L'):
        return 'Ladies'
    elif cat_str.startswith('G'):
        return 'General'
    return 'All'

def parse_university_quota(cat):
    cat_str = str(cat).upper().replace(' ', '')
    if cat_str.endswith('H'):
        return 'Home University'
    elif cat_str.endswith('O'):
        return 'Other than Home University'
    elif cat_str.endswith('S'):
        return 'State Level'
    elif 'AI' in cat_str:
        return 'All India'
    return 'All'

df_all['Category Group'] = df_all['Category'].apply(map_category_group)
df_all['Gender Quota'] = df_all['Category'].apply(parse_gender_quota)
df_all['University Quota'] = df_all['Category'].apply(parse_university_quota)

# 4. Status Grouping
def map_status_group(status):
    st_upper = str(status).upper()
    if 'GOVERNMENT' in st_upper:
        if 'AUTONOMOUS' in st_upper:
            return 'Government Autonomous'
        return 'Government'
    elif 'UNIVERSITY' in st_upper:
        return 'University Dept'
    elif 'AUTONOMOUS' in st_upper:
        return 'Private Autonomous'
    return 'Private / Un-Aided'

df_all['Status Group'] = df_all['Status'].apply(map_status_group)

# 5. Extract seat intake data from Seat Matrix files if present
seat_dict = {}
seat_files = [f for f in ['output_2023SeatMatrix.xlsx', 'output_2025SeatMatrix.xlsx'] if os.path.exists(f)]
for sf in seat_files:
    try:
        xl = pd.ExcelFile(sf)
        df_seat = xl.parse(xl.sheet_names[0])
        if 'College Code' in df_seat.columns and 'Course Name' in df_seat.columns:
            # Count seats per college code + course
            grp = df_seat.groupby(['College Code', 'Course Name']).size().reset_index(name='Intake')
            for _, r in grp.iterrows():
                key = (int(r['College Code']), str(r['Course Name']).strip())
                seat_dict[key] = int(r['Intake'])
    except Exception as e:
        print(f"Warning parsing seat matrix {sf}: {e}")

def get_intake(row):
    key = (row['College Code'], str(row['Course Name']).strip())
    return seat_dict.get(key, None)

df_all['Seat Intake'] = df_all.apply(get_intake, axis=1)

# Build Empirical Rank-Percentile Table
percentiles_grid = np.linspace(0.0, 100.0, 1001) # 0.1 step
rank_points = []
df_valid = df_all[(df_all['Cutoff Percentile'] >= 0) & (df_all['Cutoff Percentile'] <= 100) & (df_all['Cutoff Rank'] > 0)]

for p in percentiles_grid:
    sub = df_valid[np.abs(df_valid['Cutoff Percentile'] - p) <= 0.25]
    if len(sub) > 0:
        med_r = int(sub['Cutoff Rank'].median())
    else:
        # Fallback linear approximation if empty
        med_r = max(1, int((100.0 - p) * 1800))
    rank_points.append({"percentile": round(float(p), 2), "estimated_rank": med_r})

df_rank_map = pd.DataFrame(rank_points)

# Save to SQLite DB
db_file = "mht_cet_cutoffs.db"
if os.path.exists(db_file):
    try:
        os.remove(db_file)
    except Exception as e:
        print(f"Warning removing old DB: {e}")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

df_all.to_sql("cutoffs", conn, if_exists="replace", index=False)
df_rank_map.to_sql("rank_map", conn, if_exists="replace", index=False)

# Create indexes for performance
cursor.execute("CREATE INDEX IF NOT EXISTS idx_percentile ON cutoffs (`Cutoff Percentile`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_rank ON cutoffs (`Cutoff Rank`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_college ON cutoffs (`College Code`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_course ON cutoffs (`Course Name Clean`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_year ON cutoffs (`Year`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_cap ON cutoffs (`CAP Round`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_cat_group ON cutoffs (`Category Group`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_district ON cutoffs (`District`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_gender ON cutoffs (`Gender Quota`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_univ ON cutoffs (`University Quota`);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_rank_map_p ON rank_map (`percentile`);")

cursor.execute("DROP TABLE IF EXISTS colleges;")
cursor.execute("""
CREATE TABLE colleges AS 
SELECT DISTINCT `College Code`, `College Name`, `District`, `Status Group`, `Status` 
FROM cutoffs ORDER BY `College Code`;
""")

cursor.execute("DROP TABLE IF EXISTS courses;")
cursor.execute("""
CREATE TABLE courses AS 
SELECT `Course Name Clean` AS course_name, COUNT(*) as cutoff_count 
FROM cutoffs GROUP BY `Course Name Clean` ORDER BY cutoff_count DESC;
""")

cursor.execute("DROP TABLE IF EXISTS metadata;")
cursor.execute("""
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
""")
cursor.execute("INSERT INTO metadata VALUES ('model_version', '2.0.0');")
cursor.execute("INSERT INTO metadata VALUES ('dataset_records', ?);", (len(df_all),))
cursor.execute("INSERT INTO metadata VALUES ('build_timestamp', '2026-09-29');")

conn.commit()
conn.close()

print(f"SUCCESS: Built SQLite Database '{db_file}' with {len(df_all)} indexed rows and rank mapping table.")
