# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px
from predictor_model import MhtCetPredictor, TOP_20_MAHARASHTRA_COLLEGES

# Page Configuration
st.set_page_config(
    page_title="MHT CET Predictor | Top 20 Maharashtra Colleges",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS Styling (Glassmorphism + Dark Mode Vibrant Accents)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .hero-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00C6FF 0%, #0072FF 50%, #7F00FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    
    .hero-sub {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    .top20-banner {
        background: linear-gradient(135deg, rgba(255,215,0,0.15) 0%, rgba(255,140,0,0.08) 100%);
        border: 1px solid rgba(255,215,0,0.3);
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        backdrop-filter: blur(8px);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #38BDF8;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .badge-top20 {
        background-color: #f59e0b;
        color: #000;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
    }
    .badge-safe {
        background-color: #10b981;
        color: white;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
    }
    .badge-target {
        background-color: #f59e0b;
        color: white;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
    }
    .badge-dream {
        background-color: #ef4444;
        color: white;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
    }

    /* Streamlit Button Tweaks */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_predictor():
    return MhtCetPredictor()

predictor = load_predictor()
options = predictor.get_filter_options()

# --- SIDEBAR: STUDENT PROFILE & PREFERENCES ---
st.sidebar.image("https://img.icons8.com/isometric-folders/100/graduation-cap.png", width=65)
st.sidebar.title("🎯 Student Profile")

input_mode = st.sidebar.radio("Input Type", ["MHT CET Percentile (%)", "State Merit Rank"], index=0)

if input_mode == "MHT CET Percentile (%)":
    user_percentile = st.sidebar.number_input("MHT CET Percentile", min_value=0.0, max_value=100.0, value=92.5, step=0.1, format="%.2f")
    est_rank = predictor.convert_percentile_to_rank(user_percentile)
    st.sidebar.info(f"📊 Estimated State Rank: **{est_rank:,}**")
    user_rank = None
else:
    user_rank = st.sidebar.number_input("State Merit Rank", min_value=1, max_value=250000, value=15000, step=100)
    user_percentile = predictor.convert_rank_to_percentile(user_rank)
    st.sidebar.info(f"📊 Estimated Percentile: **{user_percentile:.2f}%**")

st.sidebar.markdown("---")

# Quick Action Presets
st.sidebar.subheader("🏆 College Priorities")
top_20_only_flag = st.sidebar.checkbox("🏆 Show Top 20 Maharashtra Colleges Only", value=False, help="Filters results exclusively to Maharashtra's Top 20 engineering institutes")
prioritize_top_20_flag = st.sidebar.checkbox("⭐ Prioritize Top 20 Colleges at Top", value=True, help="Ranks Top 20 Colleges first in search & preference lists")

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Category & Seat Filters", expanded=True):
    cat_mode = st.radio("Category Type", ["Category Group", "Specific Seat Category Code"], index=0)
    if cat_mode == "Category Group":
        default_cat_idx = options['category_groups'].index('OPEN') + 1 if 'OPEN' in options['category_groups'] else 0
        selected_cat_group = st.selectbox("Category Group", ["ALL"] + options['category_groups'], index=default_cat_idx)
        selected_spec_cat = None
    else:
        selected_cat_group = 'ALL'
        selected_spec_cat = st.selectbox("Seat Category Code", options['categories'])

with st.sidebar.expander("📍 Location & Branch Preferences", expanded=False):
    # District Selection
    selected_districts = st.multiselect("Districts / Cities", ["ALL"] + options['districts'], default=["ALL"])
    if "ALL" in selected_districts or not selected_districts:
        selected_districts = ["ALL"]
        
    # Branch Selection
    default_branches = [b for b in options['courses'] if any(k in b for k in ['Computer', 'Information', 'Artificial'])]
    selected_branches = st.multiselect("Engineering Branches", ["ALL"] + options['courses'], default=["ALL"])
    if "ALL" in selected_branches or not selected_branches:
        selected_branches = ["ALL"]

    selected_statuses = st.multiselect("Institution Status", ["ALL"] + options['status_groups'], default=["ALL"])
    if "ALL" in selected_statuses or not selected_statuses:
        selected_statuses = ["ALL"]

    selected_round = st.selectbox("CAP Round", ["ALL", "1", "2", "3", "4"], index=0)
    prob_threshold = st.slider("Min Admission Chance (%)", 0, 100, 0, step=5)


# --- MAIN HEADER ---
st.markdown('<div class="hero-header">🎓 MHT CET College Predictor & Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Get direct admission predictions for Maharashtra\'s <b>Top 20 Engineering Colleges</b>, analyze 3-year cutoff trends (2023-2025), and generate official DTE CAP Choice Forms.</div>', unsafe_allow_html=True)

    # pyrefly: ignore [parse-error]
    selected_gender = st.selectbox("Gender Quota", options.get('gender_quotas', ['All']), index=0)
    selected_univ = st.selectbox("University Quota", options.get('university_quotas', ['All']), index=0)

# Run Prediction Engine
with st.spinner("Analyzing historical cutoff records..."):
    df_results, calc_percentile, calc_rank = predictor.predict_colleges(
        percentile=user_percentile,
        rank=user_rank,
        category_group=selected_cat_group,
        specific_category=selected_spec_cat,
        gender_quota=selected_gender,
        university_quota=selected_univ,
        branches=selected_branches,
        districts=selected_districts,
        status_groups=selected_statuses,
        cap_round=selected_round,
        min_probability=prob_threshold,
        top_20_only=top_20_only_flag,
        prioritize_top_20=prioritize_top_20_flag
    )

# Quick KPI Metrics
col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
top20_count = len(df_results[df_results['Is Top 20'] == True]) if len(df_results) > 0 else 0
safe_count = len(df_results[df_results['Chance Tag'].str.contains('High')]) if len(df_results) > 0 else 0
target_count = len(df_results[df_results['Chance Tag'].str.contains('Moderate')]) if len(df_results) > 0 else 0
dream_count = len(df_results[df_results['Chance Tag'].str.contains('Low')]) if len(df_results) > 0 else 0

with col_kpi1:
    st.markdown(f'<div class="metric-card"><div class="metric-val">{user_percentile:.2f}%</div><div class="metric-lbl">Your Percentile</div></div>', unsafe_allow_html=True)
with col_kpi2:
    st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#f59e0b;">🏆 {top20_count}</div><div class="metric-lbl">Top 20 Options</div></div>', unsafe_allow_html=True)
with col_kpi3:
    st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#10b981;">🟢 {safe_count}</div><div class="metric-lbl">Safe Options (>85%)</div></div>', unsafe_allow_html=True)
with col_kpi4:
    st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#f59e0b;">🟡 {target_count}</div><div class="metric-lbl">Target Options (50-85%)</div></div>', unsafe_allow_html=True)
with col_kpi5:
    st.markdown(f'<div class="metric-card"><div class="metric-val" style="color:#ef4444;">🔴 {dream_count}</div><div class="metric-lbl">Dream Options (<50%)</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_top20, tab_predict, tab_option_form, tab_trends, tab_compare = st.tabs([
    "🏆 Top 20 Maharashtra Showcase",
    "🎯 All College Predictions", 
    "📋 DTE Option Form Generator", 
    "📈 Multi-Year Cutoff Analytics", 
    "⚖️ College Comparator"
])

# ==============================================================================
# TAB 1: TOP 20 MAHARASHTRA SHOWCASE
# ==============================================================================
with tab_top20:
    st.markdown("### 🏆 Top 20 Engineering Colleges in Maharashtra")
    st.markdown("Complete priority list of Maharashtra's premier engineering institutions, curated by academic reputation, DTE cutoffs, and NIRF standings.")

    df_top20_summary = predictor.get_top_20_analytics(percentile=user_percentile, category_group=selected_cat_group)
    
    # Filter controls inside Top 20 tab
    c_t1, c_t2 = st.columns([2, 1])
    with c_t1:
        top20_search = st.text_input("🔍 Quick Search Top 20 Colleges (Name/City/Code):", "", key="top20_search")
    with c_t2:
        chance_filter = st.selectbox("Filter Admission Chance:", ["ALL", "🟢 High Chance", "🟡 Moderate Chance", "🔴 Low Chance"])
        
    display_top20 = df_top20_summary.copy()
    if top20_search:
        display_top20 = display_top20[
            display_top20['Full Name'].str.contains(top20_search, case=False, na=False) |
            display_top20['Short Name'].str.contains(top20_search, case=False, na=False) |
            display_top20['City / District'].str.contains(top20_search, case=False, na=False) |
            display_top20['Code'].astype(str).str.contains(top20_search)
        ]
    if chance_filter != "ALL":
        display_top20 = display_top20[display_top20['Your Admission Chance (CSE)'].str.contains(chance_filter[:2])]

    st.dataframe(
        display_top20,
        column_config={
            "Rank": st.column_config.NumberColumn("State Rank", format="#%d"),
            "Code": st.column_config.NumberColumn("DTE Code", format="%d"),
            "Short Name": st.column_config.TextColumn("College", width="small"),
            "Full Name": st.column_config.TextColumn("Full Institute Name", width="large"),
            "City / District": st.column_config.TextColumn("Location", width="small"),
            "CSE Cutoff (%ile)": st.column_config.NumberColumn("CSE Cutoff %", format="%.2f%%"),
            "IT Cutoff (%ile)": st.column_config.NumberColumn("IT Cutoff %", format="%.2f%%"),
            "Overall Highest %ile": st.column_config.NumberColumn("Peak Cutoff %", format="%.2f%%"),
            "Your Admission Chance (CSE)": st.column_config.TextColumn("Admission Chance (CSE/IT)"),
        },
        hide_index=True,
        use_container_width=True,
        height=520
    )

    st.markdown("---")
    st.subheader("🏛️ Direct Top 20 Options Matching Your Profile")
    top20_user_matches = df_results[df_results['Is Top 20'] == True]
    
    if len(top20_user_matches) > 0:
        st.dataframe(
            top20_user_matches[[
                'Top 20 Tag', 'College Name', 'Course', 'Category', 'District',
                'Admission Probability', 'Chance Tag', 'Latest Cutoff Percentile'
            ]],
            column_config={
                "Top 20 Tag": st.column_config.TextColumn("Tier & Rank", width="medium"),
                "College Name": st.column_config.TextColumn("College Name", width="large"),
                "Admission Probability": st.column_config.ProgressColumn("Admission Prob (%)", format="%.1f%%", min_value=0, max_value=100),
                "Latest Cutoff Percentile": st.column_config.NumberColumn("Latest Cutoff %", format="%.2f%%"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No options directly found in Top 20 matching your exact branch/district filters. Try selecting 'ALL' branches in the sidebar.")


# ==============================================================================
# TAB 2: ALL COLLEGE PREDICTIONS
# ==============================================================================
with tab_predict:
    if len(df_results) == 0:
        st.warning("⚠️ No colleges found matching the selected criteria. Try expanding your location or branch filters.")
    else:
        st.markdown("### 🏛️ Predicted Colleges & Admission Probabilities")
        
        # Search & Quick Filters Bar
        col_s1, col_s2, col_s3 = st.columns([3, 2, 2])
        with col_s1:
            search_kw = st.text_input("🔍 Search College Name, Code, or City:", "", key="pred_search")
        with col_s2:
            tier_filter = st.selectbox("College Tier Filter:", ["ALL Tiers", "🏆 Top 20 Maharashtra Only", "Govt / Autonomous", "Standard State College"])
        with col_s3:
            chance_type_filter = st.selectbox("Chance Level:", ["ALL Chances", "High / Safe", "Moderate / Target", "Low / Dream"])
        
        display_df = df_results.copy()
        
        if search_kw:
            display_df = display_df[
                display_df['College Name'].str.contains(search_kw, case=False, na=False) |
                display_df['College Code'].astype(str).str.contains(search_kw) |
                display_df['District'].str.contains(search_kw, case=False, na=False) |
                display_df['Course'].str.contains(search_kw, case=False, na=False)
            ]
        if tier_filter != "ALL Tiers":
            if "Top 20" in tier_filter:
                display_df = display_df[display_df['Is Top 20'] == True]
            else:
                display_df = display_df[display_df['College Tier'].str.contains(tier_filter, case=False, na=False)]
                
        if chance_type_filter != "ALL Chances":
            display_df = display_df[display_df['Chance Tag'].str.contains(chance_type_filter, case=False, na=False)]

        styled_df = display_df[[
            'College Tier', 'College Code', 'College Name', 'Course', 'Category', 'District', 'Status',
            'Admission Probability', 'Chance Tag', 'Latest Cutoff Percentile', 'Latest Cutoff Rank',
            '2025 Cutoff (%/Rank)', '2024 Cutoff (%/Rank)', '2023 Cutoff (%/Rank)', 'Trend'
        ]].copy()

        st.dataframe(
            styled_df,
            column_config={
                "College Tier": st.column_config.TextColumn("Tier Priority", width="medium"),
                "College Code": st.column_config.NumberColumn("Code", format="%d"),
                "College Name": st.column_config.TextColumn("College Name", width="large"),
                "Course": st.column_config.TextColumn("Course / Branch", width="medium"),
                "Admission Probability": st.column_config.ProgressColumn("Admission Prob (%)", format="%.1f%%", min_value=0, max_value=100),
                "Chance Tag": st.column_config.TextColumn("Admission Tag"),
                "Latest Cutoff Percentile": st.column_config.NumberColumn("Latest Cutoff %", format="%.2f%%"),
                "Latest Cutoff Rank": st.column_config.NumberColumn("Latest Cutoff Rank", format="%d"),
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )

        st.markdown("---")
        c_dl1, c_dl2 = st.columns([1, 4])
        with c_dl1:
            csv_data = styled_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Results (CSV)", data=csv_data, file_name=f"MHTCET_Predictions_{user_percentile}pct.csv", mime="text/csv")


# ==============================================================================
# TAB 3: DTE OPTION FORM GENERATOR
# ==============================================================================
with tab_option_form:
    st.markdown("### 📋 Official DTE CAP Preference List Generator")
    st.write("Generates an optimized DTE Choice Form preference list. Top 20 colleges and premier cutoffs are positioned at the top for maximum CAP round allocation efficiency.")

    if len(df_results) > 0:
        pref_order_mode = st.radio("Preference Ordering Logic:", ["🏆 Prioritize Top 20 Maharashtra Colleges First", "📉 Strict Historical Cutoff Percentile Order"], index=0)
        
        if "Top 20" in pref_order_mode:
            opt_df = df_results.sort_values(by=["Is Top 20", "Top 20 Rank", "Weighted Cutoff Percentile"], ascending=[False, True, False]).reset_index(drop=True)
        else:
            opt_df = df_results.sort_values(by="Weighted Cutoff Percentile", ascending=False).reset_index(drop=True)
            
        opt_df['Preference No'] = opt_df.index + 1
        
        display_opt = opt_df[['Preference No', 'College Tier', 'College Code', 'College Name', 'Course', 'Category', 'District', 'Status', 'Weighted Cutoff Percentile', 'Chance Tag']].copy()
        
        st.dataframe(
            display_opt,
            column_config={
                "Preference No": st.column_config.NumberColumn("Pref #", format="%d"),
                "College Tier": st.column_config.TextColumn("Tier Priority", width="medium"),
                "College Code": st.column_config.NumberColumn("Code", format="%d"),
                "Weighted Cutoff Percentile": st.column_config.NumberColumn("Hist. Cutoff %", format="%.2f%%"),
            },
            hide_index=True,
            use_container_width=True,
            height=480
        )
        
        opt_csv = display_opt.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Official DTE Preference List (CSV)", data=opt_csv, file_name=f"DTE_Option_Form_{user_percentile}pct.csv", mime="text/csv")
    else:
        st.info("No options available. Run predictions first.")


# ==============================================================================
# TAB 4: MULTI-YEAR CUTOFF ANALYTICS
# ==============================================================================
with tab_trends:
    st.markdown("### 📈 College & Branch Multi-Year Cutoff Trends (2023 - 2025)")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        college_options = df_results['College Name'].unique() if len(df_results) > 0 else ["No colleges"]
        trend_college = st.selectbox("Select College for Trend Analysis", options=college_options)
    with col_t2:
        available_courses = df_results[df_results['College Name'] == trend_college]['Course'].unique() if len(df_results) > 0 else []
        trend_course = st.selectbox("Select Branch", options=available_courses if len(available_courses) > 0 else ["N/A"])
    with col_t3:
        available_cats = df_results[(df_results['College Name'] == trend_college) & (df_results['Course'] == trend_course)]['Category'].unique() if len(df_results) > 0 else []
        trend_cat = st.selectbox("Select Seat Category", options=available_cats if len(available_cats) > 0 else ["N/A"])

    if trend_college and trend_course and trend_cat and trend_college != "No colleges":
        sel_col_code = df_results[df_results['College Name'] == trend_college]['College Code'].iloc[0]
        df_trend = predictor.get_college_trend(sel_col_code, trend_course, trend_cat)
        
        if len(df_trend) > 0:
            df_trend['Year-Round'] = df_trend['Year'].astype(str) + " CAP " + df_trend['CAP Round'].astype(str)
            
            fig = px.line(
                df_trend,
                x='Year-Round',
                y='Cutoff Percentile',
                markers=True,
                title=f"Cutoff Percentile Trend: {trend_college} ({trend_course} - {trend_cat})",
                labels={'Cutoff Percentile': 'Cutoff Percentile (%)', 'Year-Round': 'CAP Admission Round'},
                color_discrete_sequence=['#38BDF8']
            )
            fig.add_hline(y=user_percentile, line_dash="dash", line_color="#10b981", annotation_text=f"Your Percentile ({user_percentile}%)")
            fig.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_trend[['Year', 'CAP Round', 'Cutoff Rank', 'Cutoff Percentile']], hide_index=True)
        else:
            st.warning("No specific round trend records found for this combination.")


# ==============================================================================
# TAB 5: COLLEGE COMPARATOR
# ==============================================================================
with tab_compare:
    st.markdown("### ⚖️ Side-by-Side College Comparator")
    
    if len(df_results) > 0:
        col_list = df_results['College Name'].unique().tolist()
        # Default select top 2 colleges
        comp_colleges = st.multiselect("Select up to 4 colleges to compare:", col_list, default=col_list[:min(3, len(col_list))])
        
        if comp_colleges:
            comp_df = df_results[df_results['College Name'].isin(comp_colleges)]
            
            st.subheader("Comparison Summary Table")
            st.dataframe(
                comp_df[['College Tier', 'College Name', 'Course', 'Category', 'District', 'Status', 'Latest Cutoff Percentile', 'Admission Probability', 'Chance Tag']],
                hide_index=True,
                use_container_width=True
            )
            
            fig_comp = px.bar(
                comp_df,
                x='College Name',
                y='Admission Probability',
                color='Chance Tag',
                hover_data=['Course', 'Latest Cutoff Percentile'],
                title="Admission Probability Comparison across Selected Colleges",
                barmode='group',
                color_discrete_map={
                    "High / Safe": "#10b981",
                    "Moderate / Target": "#f59e0b",
                    "Low / Dream": "#ef4444"
                }
            )
            fig_comp.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Run predictions first to compare colleges.")

st.markdown("---")
st.caption("ℹ️ MHT CET College Predictor & Analytics System | Prioritized for Maharashtra Top 20 Engineering Colleges | Data compiled from DTE CAP Rounds (2023 - 2025).")
