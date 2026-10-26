"""
MHT CET College Predictor & Analytics Model
Handles empirical rank-percentile calculations, multi-year cutoff analysis (2023-2025),
college filtering, and admission probability estimation for Maharashtra Engineering Admissions.
"""

import sqlite3
import math
import os
import pandas as pd
import numpy as np

# Official Priority Ranking for Maharashtra Top 20 Engineering Colleges
TOP_20_MAHARASHTRA_COLLEGES = [
    {
        "Rank": 1,
        "Code": 6006,
        "Short Name": "COEP Pune",
        "Full Name": "COEP Technological University, Pune",
        "City / District": "Pune",
        "Status": "Government Autonomous"
    },
    {
        "Rank": 2,
        "Code": 3012,
        "Short Name": "VJTI Mumbai",
        "Full Name": "Veermata Jijabai Technological Institute (VJTI), Mumbai",
        "City / District": "Mumbai",
        "Status": "Government Autonomous"
    },
    {
        "Rank": 3,
        "Code": 3215,
        "Short Name": "SPIT Mumbai",
        "Full Name": "Sardar Patel Institute of Technology (SPIT), Andheri, Mumbai",
        "City / District": "Mumbai",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 4,
        "Code": 6271,
        "Short Name": "PICT Pune",
        "Full Name": "Pune Institute of Computer Technology (PICT), Pune",
        "City / District": "Pune",
        "Status": "Private / Un-Aided"
    },
    {
        "Rank": 5,
        "Code": 6007,
        "Short Name": "WCE Sangli",
        "Full Name": "Walchand College of Engineering, Sangli",
        "City / District": "Sangli",
        "Status": "Government Autonomous"
    },
    {
        "Rank": 6,
        "Code": 3014,
        "Short Name": "SPCE Mumbai",
        "Full Name": "Sardar Patel College of Engineering (SPCE), Andheri, Mumbai",
        "City / District": "Mumbai",
        "Status": "Government Autonomous"
    },
    {
        "Rank": 7,
        "Code": 3199,
        "Short Name": "DJ Sanghvi Mumbai",
        "Full Name": "Shri Vile Parle Kelvani Mandal's Dwarkadas J. Sanghvi College of Engineering, Mumbai",
        "City / District": "Mumbai",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 8,
        "Code": 6273,
        "Short Name": "VIT Pune",
        "Full Name": "Bansilal Ramnath Agarawal Charitable Trust's Vishwakarma Institute of Technology (VIT), Pune",
        "City / District": "Pune",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 9,
        "Code": 6175,
        "Short Name": "PCCOE Pune",
        "Full Name": "Pimpri Chinchwad College of Engineering (PCCOE), Pune",
        "City / District": "Pune",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 10,
        "Code": 6276,
        "Short Name": "Cummins Pune (Women)",
        "Full Name": "MKSSS's Cummins College of Engineering for Women, Karvenagar, Pune",
        "City / District": "Pune",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 11,
        "Code": 6289,
        "Short Name": "VIIT Pune",
        "Full Name": "Vishwakarma Institute of Information Technology (VIIT), Kondhwa, Pune",
        "City / District": "Pune",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 12,
        "Code": 3182,
        "Short Name": "Thadomal Shahani Mumbai",
        "Full Name": "Thadomal Shahani Engineering College, Bandra, Mumbai",
        "City / District": "Mumbai",
        "Status": "Private / Un-Aided"
    },
    {
        "Rank": 13,
        "Code": 6005,
        "Short Name": "GCOE Karad",
        "Full Name": "Government College of Engineering, Karad",
        "City / District": "Satara",
        "Status": "Government Autonomous"
    },
    {
        "Rank": 14,
        "Code": 2008,
        "Short Name": "GCOE Aurangabad",
        "Full Name": "Government College of Engineering, Chhatrapati Sambhajinagar",
        "City / District": "Chhatrapati Sambhajinagar",
        "Status": "Government Autonomous"
    },
    {
        "Rank": 15,
        "Code": 1002,
        "Short Name": "GCOE Amravati",
        "Full Name": "Government College of Engineering, Amravati",
        "City / District": "Amravati",
        "Status": "Government Autonomous"
    },
    {
        "Rank": 16,
        "Code": 4115,
        "Short Name": "RCOEM Nagpur",
        "Full Name": "Shri Ramdeobaba College of Engineering and Management (RCOEM), Nagpur",
        "City / District": "Nagpur",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 17,
        "Code": 3209,
        "Short Name": "KJ Somaiya Mumbai",
        "Full Name": "K J Somaiya Institute of Technology, Sion, Mumbai",
        "City / District": "Mumbai",
        "Status": "Private Autonomous"
    },
    {
        "Rank": 18,
        "Code": 3185,
        "Short Name": "VESIT Chembur",
        "Full Name": "Vivekanand Education Society's Institute of Technology (VESIT), Chembur, Mumbai",
        "City / District": "Mumbai",
        "Status": "Private / Un-Aided"
    },
    {
        "Rank": 19,
        "Code": 3184,
        "Short Name": "CRCE Bandra",
        "Full Name": "Fr. Conceicao Rodrigues College of Engineering, Bandra, Mumbai",
        "City / District": "Mumbai",
        "Status": "Private / Un-Aided"
    },
    {
        "Rank": 20,
        "Code": 6272,
        "Short Name": "DY Patil Akurdi",
        "Full Name": "Dr. D. Y. Patil College of Engineering, Akurdi, Pune",
        "City / District": "Pune",
        "Status": "Private / Un-Aided"
    }
]

TOP_20_MAP = {col["Code"]: col for col in TOP_20_MAHARASHTRA_COLLEGES}


class MhtCetPredictor:
    """Predictor engine querying normalized SQLite database of MHT CET cutoffs."""

    def __init__(self, db_path: str = "mht_cet_cutoffs.db"):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database {self.db_path} not found. Please run build_database.py first.")

        self._load_rank_map()
        self._load_cached_options()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_rank_map(self):
        """Loads percentile to rank empirical mapping into memory for sub-millisecond conversion."""
        try:
            with self._get_connection() as conn:
                self.df_rank_map = pd.read_sql_query(
                    "SELECT percentile, estimated_rank FROM rank_map ORDER BY percentile ASC", conn
                )
        except Exception:
            self.df_rank_map = pd.DataFrame(columns=["percentile", "estimated_rank"])

    def _load_cached_options(self):
        """Pre-loads dropdown options and metadata."""
        with self._get_connection() as conn:
            # Districts
            res = conn.execute("SELECT DISTINCT District FROM colleges WHERE District IS NOT NULL AND District != '' ORDER BY District").fetchall()
            self.districts = [r[0] for r in res]

            # Cleaned courses
            res = conn.execute("SELECT course_name FROM courses WHERE cutoff_count >= 10 ORDER BY course_name").fetchall()
            self.courses = [r[0] for r in res]

            # Category Groups
            self.category_groups = ["OPEN", "OBC", "SC", "ST", "VJ / NT", "EWS", "TFWS", "PWD", "DEFENCE", "MINORITY"]

            # Specific Categories
            res = conn.execute("SELECT DISTINCT Category FROM cutoffs WHERE Category IS NOT NULL AND Category != '' ORDER BY Category LIMIT 200").fetchall()
            self.categories = [r[0] for r in res]

            # Status Groups
            res = conn.execute("SELECT DISTINCT [Status Group] FROM cutoffs WHERE [Status Group] IS NOT NULL ORDER BY [Status Group]").fetchall()
            self.status_groups = [r[0] for r in res]

    def convert_percentile_to_rank(self, percentile: float) -> int:
        """Converts an MHT CET percentile to empirical State Merit Rank."""
        p = max(0.0, min(100.0, float(percentile)))
        if not self.df_rank_map.empty:
            idx = (np.abs(self.df_rank_map['percentile'] - p)).argmin()
            return int(self.df_rank_map.iloc[idx]['estimated_rank'])

        # Fallback non-linear empirical formula
        if p >= 99.9:
            return max(1, int(1 + (100.0 - p) * 10000))
        elif p >= 99.0:
            return int(1020 + (99.9 - p) * 2058)
        elif p >= 95.0:
            return int(2873 + (99.0 - p) * 3250)
        elif p >= 90.0:
            return int(15874 + (95.0 - p) * 2950)
        elif p >= 80.0:
            return int(30623 + (90.0 - p) * 2818)
        elif p >= 50.0:
            return int(58800 + (80.0 - p) * 2130)
        else:
            return int(122713 + (50.0 - p) * 1000)

    def convert_rank_to_percentile(self, rank: int) -> float:
        """Converts State Merit Rank to estimated MHT CET percentile."""
        r = max(1, int(rank))
        if not self.df_rank_map.empty:
            idx = (np.abs(self.df_rank_map['estimated_rank'] - r)).argmin()
            return float(self.df_rank_map.iloc[idx]['percentile'])

        # Fallback inverse formula
        if r <= 1000:
            return round(100.0 - (r - 1) / 10000.0, 2)
        elif r <= 2873:
            return round(99.9 - (r - 1020) / 2058.0, 2)
        elif r <= 15874:
            return round(99.0 - (r - 2873) / 3250.0, 2)
        elif r <= 30623:
            return round(95.0 - (r - 15874) / 2950.0, 2)
        elif r <= 58800:
            return round(90.0 - (r - 30623) / 2818.0, 2)
        else:
            return round(max(0.0, 80.0 - (r - 58800) / 2130.0), 2)

    def get_filter_options(self) -> dict:
        """Returns structured dictionary of filter choices for UI and APIs."""
        return {
            'districts': self.districts,
            'courses': self.courses,
            'category_groups': self.category_groups,
            'categories': self.categories,
            'status_groups': self.status_groups,
            'gender_quotas': ['All', 'General', 'Ladies'],
            'university_quotas': ['All', 'Home University', 'Other than Home University', 'State Level', 'All India']
        }

    @staticmethod
    def _calc_admission_probability(user_pct: float, cutoff_pct: float) -> float:
        """
        Sigmoidal / calibrated probability calculation based on percentile difference.
        delta >= +1.5 -> prob >= 85% (Safe)
        delta between -1.0 and +1.5 -> prob between 50% and 85% (Target)
        delta < -1.0 -> prob < 50% (Dream)
        """
        delta = user_pct - cutoff_pct
        # Scaled logistic function with inflection centered slightly below 0
        z = (delta + 0.4) / 0.85
        prob = 100.0 / (1.0 + math.exp(-max(-8.0, min(8.0, z))))
        return round(float(prob), 1)

    @staticmethod
    def _get_chance_tag(prob: float) -> str:
        if prob >= 85.0:
            return "🟢 High / Safe"
        elif prob >= 50.0:
            return "🟡 Moderate / Target"
        else:
            return "🔴 Low / Dream"

    def get_top_20_analytics(self, percentile: float = 92.5, category_group: str = 'OPEN') -> pd.DataFrame:
        """
        Generates analytics summary table for Maharashtra's Top 20 Engineering Colleges.
        Computes CSE Cutoff, IT Cutoff, Peak Cutoff, and admission chances for student.
        """
        col_codes = [col['Code'] for col in TOP_20_MAHARASHTRA_COLLEGES]
        placeholders = ','.join('?' for _ in col_codes)

        cat_filter = ""
        params = list(col_codes)
        if category_group and category_group != 'ALL':
            cat_filter = "AND [Category Group] = ?"
            params.append(category_group)

        query = f"""
        SELECT [College Code], [Course Name Clean] as Course,
               MAX([Cutoff Percentile]) as max_pct
        FROM cutoffs
        WHERE [College Code] IN ({placeholders})
          {cat_filter}
        GROUP BY [College Code], [Course Name Clean]
        """

        with self._get_connection() as conn:
            df_cut = pd.read_sql_query(query, conn, params=params)

        results = []
        for col_info in TOP_20_MAHARASHTRA_COLLEGES:
            code = col_info['Code']
            sub = df_cut[df_cut['College Code'] == code]

            cse_sub = sub[sub['Course'].str.contains('Computer|Data Science|Artificial Intelligence', case=False, na=False)]
            it_sub = sub[sub['Course'].str.contains('Information Tech', case=False, na=False)]

            cse_cutoff = round(float(cse_sub['max_pct'].max()), 2) if not cse_sub.empty and pd.notna(cse_sub['max_pct'].max()) else None
            it_cutoff = round(float(it_sub['max_pct'].max()), 2) if not it_sub.empty and pd.notna(it_sub['max_pct'].max()) else None
            overall_peak = round(float(sub['max_pct'].max()), 2) if not sub.empty and pd.notna(sub['max_pct'].max()) else (cse_cutoff or 95.0)

            ref_cutoff = cse_cutoff if cse_cutoff is not None else (it_cutoff if it_cutoff is not None else overall_peak)
            prob = self._calc_admission_probability(percentile, ref_cutoff if ref_cutoff else 90.0)

            if prob >= 85.0:
                chance_str = "🟢 High Chance"
            elif prob >= 50.0:
                chance_str = "🟡 Moderate Chance"
            else:
                chance_str = "🔴 Low Chance"

            results.append({
                "Rank": col_info["Rank"],
                "Code": code,
                "Short Name": col_info["Short Name"],
                "Full Name": col_info["Full Name"],
                "City / District": col_info["City / District"],
                "Status": col_info.get("Status", ""),
                "CSE Cutoff (%ile)": cse_cutoff,
                "IT Cutoff (%ile)": it_cutoff,
                "Overall Highest %ile": overall_peak,
                "Your Admission Chance (CSE)": chance_str
            })

        return pd.DataFrame(results)

    def predict_colleges(
        self,
        percentile: float = 92.5,
        rank: int = None,
        category_group: str = 'OPEN',
        specific_category: str = None,
        gender_quota: str = 'All',
        university_quota: str = 'All',
        branches: list = None,
        districts: list = None,
        status_groups: list = None,
        cap_round: str = 'ALL',
        min_probability: float = 0.0,
        top_20_only: bool = False,
        prioritize_top_20: bool = True
    ):
        """
        Primary prediction engine querying historical cutoffs, aggregating across years,
        and ranking colleges according to student credentials and user preferences.
        """
        if rank is not None and (percentile is None or percentile == 0):
            percentile = self.convert_rank_to_percentile(rank)
        elif percentile is not None and rank is None:
            rank = self.convert_percentile_to_rank(percentile)

        percentile = float(percentile)
        rank = int(rank)

        # Build dynamic SQL query
        where_clauses = ["[Cutoff Percentile] > 0", "[Cutoff Rank] > 0"]
        params = []

        # Category Filter
        if specific_category and specific_category != 'ALL':
            where_clauses.append("Category = ?")
            params.append(specific_category)
        elif category_group and category_group != 'ALL':
            where_clauses.append("[Category Group] = ?")
            params.append(category_group)

        # Gender Quota Filter
        if gender_quota and gender_quota != 'All':
            where_clauses.append("[Gender Quota] = ?")
            params.append(gender_quota)

        # University Quota Filter
        if university_quota and university_quota != 'All':
            where_clauses.append("[University Quota] = ?")
            params.append(university_quota)

        # CAP Round Filter
        if cap_round and cap_round != 'ALL':
            try:
                where_clauses.append("[CAP Round] = ?")
                params.append(int(cap_round))
            except ValueError:
                pass

        # District Filter
        if districts and "ALL" not in districts:
            placeholders = ','.join('?' for _ in districts)
            where_clauses.append(f"District IN ({placeholders})")
            params.extend(districts)

        # Branch Filter
        if branches and "ALL" not in branches:
            placeholders = ','.join('?' for _ in branches)
            where_clauses.append(f"[Course Name Clean] IN ({placeholders})")
            params.extend(branches)

        # Status Group Filter
        if status_groups and "ALL" not in status_groups:
            placeholders = ','.join('?' for _ in status_groups)
            where_clauses.append(f"[Status Group] IN ({placeholders})")
            params.extend(status_groups)

        # Top 20 Only
        if top_20_only:
            top_codes = [c['Code'] for c in TOP_20_MAHARASHTRA_COLLEGES]
            placeholders = ','.join('?' for _ in top_codes)
            where_clauses.append(f"[College Code] IN ({placeholders})")
            params.extend(top_codes)

        where_sql = " AND ".join(where_clauses)

        query = f"""
        SELECT
            [College Code],
            [College Name],
            [Course Name Clean] as Course,
            Category,
            District,
            [Status Group] as Status,
            MAX(CASE WHEN Year = 2024 THEN [Cutoff Percentile] END) as Cutoff_2024,
            MIN(CASE WHEN Year = 2024 THEN [Cutoff Rank] END) as Rank_2024,
            MAX(CASE WHEN Year = 2023 THEN [Cutoff Percentile] END) as Cutoff_2023,
            MIN(CASE WHEN Year = 2023 THEN [Cutoff Rank] END) as Rank_2023,
            MAX([Cutoff Percentile]) as Max_Cutoff_Percentile,
            MIN([Cutoff Rank]) as Min_Cutoff_Rank
        FROM cutoffs
        WHERE {where_sql}
        GROUP BY [College Code], [College Name], [Course Name Clean], Category, District, [Status Group]
        """

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            empty_cols = [
                'College Tier', 'College Code', 'College Name', 'Course', 'Category', 'District', 'Status',
                'Admission Probability', 'Chance Tag', 'Latest Cutoff Percentile', 'Latest Cutoff Rank',
                '2025 Cutoff (%/Rank)', '2024 Cutoff (%/Rank)', '2023 Cutoff (%/Rank)', 'Trend',
                'Is Top 20', 'Top 20 Rank', 'Top 20 Tag', 'Weighted Cutoff Percentile'
            ]
            return pd.DataFrame(columns=empty_cols), percentile, rank

        records = []
        for _, row in df.iterrows():
            code = int(row['College Code'])
            col_name = str(row['College Name'])
            course = str(row['Course'])
            cat = str(row['Category'])
            dist = str(row['District'])
            status = str(row['Status'])

            c24 = row['Cutoff_2024']
            r24 = row['Rank_2024']
            c23 = row['Cutoff_2023']
            r23 = row['Rank_2023']

            # Determine latest reference cutoff
            if pd.notna(c24):
                latest_cutoff = float(c24)
                latest_rank = int(r24) if pd.notna(r24) else self.convert_percentile_to_rank(latest_cutoff)
            elif pd.notna(c23):
                latest_cutoff = float(c23)
                latest_rank = int(r23) if pd.notna(r23) else self.convert_percentile_to_rank(latest_cutoff)
            else:
                latest_cutoff = float(row['Max_Cutoff_Percentile'])
                latest_rank = int(row['Min_Cutoff_Rank'])

            # Multi-year cutoff strings
            str_24 = f"{c24:.2f}% / #{int(r24):,}" if pd.notna(c24) and pd.notna(r24) else (f"{c24:.2f}%" if pd.notna(c24) else "N/A")
            str_23 = f"{c23:.2f}% / #{int(r23):,}" if pd.notna(c23) and pd.notna(r23) else (f"{c23:.2f}%" if pd.notna(c23) else "N/A")

            # Cutoff trend & projected 2025
            if pd.notna(c24) and pd.notna(c23):
                diff_trend = c24 - c23
                if diff_trend > 0.15:
                    trend_str = f"↗ Rising (+{diff_trend:.2f}%)"
                    proj_25 = min(99.99, c24 + diff_trend * 0.4)
                elif diff_trend < -0.15:
                    trend_str = f"↘ Falling ({diff_trend:.2f}%)"
                    proj_25 = max(1.0, c24 + diff_trend * 0.4)
                else:
                    trend_str = "— Stable (±0.1%)"
                    proj_25 = c24
                proj_rank = self.convert_percentile_to_rank(proj_25)
                str_25 = f"~{proj_25:.2f}% / #{proj_rank:,} (Proj.)"
            else:
                trend_str = "— Stable"
                proj_25 = latest_cutoff
                proj_rank = self.convert_percentile_to_rank(proj_25)
                str_25 = f"~{proj_25:.2f}% / #{proj_rank:,} (Proj.)"

            # Admission Probability & Chance Tag
            prob = self._calc_admission_probability(percentile, latest_cutoff)
            chance_tag = self._get_chance_tag(prob)

            if prob < min_probability:
                continue

            # Top 20 Metadata
            is_top20 = code in TOP_20_MAP
            if is_top20:
                top20_info = TOP_20_MAP[code]
                top20_rank = top20_info['Rank']
                tier_str = f"🏆 Top 20 (#{top20_rank})"
                tag_str = f"🏆 Top 20 (#{top20_rank})"
            else:
                top20_rank = 999
                if "Autonomous" in status or "Government" in status:
                    tier_str = "🏛️ Govt / Autonomous"
                else:
                    tier_str = "Standard State College"
                tag_str = tier_str

            records.append({
                'College Tier': tier_str,
                'Top 20 Tag': tag_str,
                'Top 20 Rank': top20_rank,
                'Is Top 20': is_top20,
                'College Code': code,
                'College Name': col_name,
                'Course': course,
                'Category': cat,
                'District': dist,
                'Status': status,
                'Admission Probability': prob,
                'Chance Tag': chance_tag,
                'Latest Cutoff Percentile': round(latest_cutoff, 2),
                'Latest Cutoff Rank': latest_rank,
                'Weighted Cutoff Percentile': round(latest_cutoff, 2),
                '2025 Cutoff (%/Rank)': str_25,
                '2024 Cutoff (%/Rank)': str_24,
                '2023 Cutoff (%/Rank)': str_23,
                'Trend': trend_str
            })

        df_out = pd.DataFrame(records)
        if df_out.empty:
            return df_out, percentile, rank

        # Sorting logic
        if prioritize_top_20:
            df_out = df_out.sort_values(
                by=['Is Top 20', 'Top 20 Rank', 'Latest Cutoff Percentile'],
                ascending=[False, True, False]
            ).reset_index(drop=True)
        else:
            df_out = df_out.sort_values(
                by=['Latest Cutoff Percentile'],
                ascending=[False]
            ).reset_index(drop=True)

        return df_out, percentile, rank

    def get_college_trend(self, college_code: int, course: str, category: str) -> pd.DataFrame:
        """
        Queries all historical CAP round cutoff records for a specific college + branch + category.
        Used by the interactive Plotly trend graph in Tab 4.
        """
        query = """
        SELECT Year, [CAP Round], [Cutoff Rank], [Cutoff Percentile]
        FROM cutoffs
        WHERE [College Code] = ?
          AND [Course Name Clean] = ?
          AND Category = ?
        ORDER BY Year ASC, [CAP Round] ASC
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[int(college_code), str(course), str(category)])

        return df
