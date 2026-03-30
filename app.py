import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
import plotly.express as px

# --- 1. הגדרות דף ועיצוב ---
st.set_page_config(page_title="Arabic Mentor Ultra", layout="wide")

# עיצוב מותאם לנייד ויישור לימין (RTL) במידת האפשר
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { border-radius: 8px; height: 3.5em; font-weight: bold; width: 100%; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    div[data-testid="stExpander"] div[role="button"] p { font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def fetch_data():
    try:
        df = conn.read(ttl=0)
        # וידוא עמודות קריטיות לפי הגיליון שלך
        required_cols = {
            'word': "", 'translation': "", 'level': 1, 
            'next_review': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'category': "כללי", 'history': "", 'date_added': pd.Timestamp.now().strftime('%Y-%m-%d')
        }
        for col, default in required_cols.items():
            if col not in df.columns:
                df[col] = default
        
        # ניקוי נתונים
        df = df.dropna(subset=['word', 'translation'])
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').dt.normalize()
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת הנתונים: {e}")
        return pd.DataFrame()

# --- 3. ניהול Session State ---
if "master_df" not in st.session_state or st.session_state.master_df.empty:
    st.session_state.master_df = fetch_data()

defaults = {
    "page": "home", "daily_correct": 0, "daily_wrong": 0, 
    "total_session_correct": 0, "list_view": "today"
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

level_names = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"FINAL"}

# --- 4. פונקציות עזר ---
def save_to_cloud():
    try:
        df_to_save = st.session_state.master_df.copy()
        df_to_save['next_review'] = df_to_save['next_review'].dt.strftime('%Y-%m-%d')
        conn.update(data=df_to_save)
        st.cache_data.clear()
        st.toast("✅ הנתונים נשמרו ב-Google Sheets!")
    except Exception as e:
        st.error(f"שגיאה בשמירה: {e}")

motivational_quotes = [
    "כל הכבוד! חביבי אתה אש!", "המוח שלך כרגע: 🧠🔥", 
    "יפה! הערבית שלך משתפרת מרגע לרגע.", "10/10! מלך העולם!"
]

# --- 5. Sidebar (ניווט) ---
with st.sidebar:
    st.title("Arabic Mentor 🧠")
    if st.button("🏠 דף הבית"): st.session_state.page = "home"
    if st.button("🗂️ קבוצות מילים"): st.session_state.page = "groups"
    if st.button("📊 סטטיסטיקה"): st.session_state.page = "stats"
    st.divider()
    if st.button("💾 שמירה לענן", type="primary"):
        save_to_cloud()

# --- 6. דף הבית: תרגול ---
if st.session_state.page == "home":
    st.title("🏠 תרגול יומי")
    
    # הוספת מילה
    with st.expander("➕ הוספת מילה חדשה"):
        with st.form("add_word_form", clear_on_submit=True):
            new_word = st.text_input("מילה בערבית")
            new_trans = st.text_input("תרגום לעברית")
            new_cat = st.text_input("קבוצה", value="כללי")
            if st.form_submit_button("הוסף למערכת"):
                new_row = pd.DataFrame([{
                    'word': new_word, 'translation': new_trans, 'level': 1,
                    'category': new_cat, 'next_review': pd.Timestamp.now().normalize(),
                    'history': "", 'date_added': pd.Timestamp.now().normalize()
                }])
                st.session_state.master_df = pd.concat([st.session_state.master_df, new_row], ignore_index=True)
                st.success("נוסף בהצלחה!")

    # מד הצלחה
    total_daily = st.session_state.daily_correct + st.session_state.daily_wrong
    if total_daily > 0:
        c_pct = (st.session_state.daily_correct / total_daily) * 100
        st.write(f"הצלחה יומית: {int(c_pct)}%")
        st.progress(c_pct / 100)

    # לוגיקת תרגול
    df = st.session_state.master_df
    today = pd.Timestamp.now().normalize()
    due_words = df[(df['next_review'] <= today) & (df['level'] < 8)]
    
    if due_words.empty:
        st.success("סיימת הכל להיום! 🎉")
        if st.button("תרגל מילים מהעתיד בכל זאת"):
            st.session_state.master_df['next_review'] = today # איפוס זמני לתרגול
            st.rerun()
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_words.index:
            st.session_state.current_idx = random.choice(due_words.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        st.info(f"רמה: {level_names.get(row['level'], 'I')} | קבוצה: {row['category']}")
        
        mode = st.radio("כיוון:", ["ערבית ⬅️ עברית", "עברית ⬅️ ערבית"], horizontal=True)
        q = row['word'] if "ערבית" in mode else row['translation']
        a = row['translation'] if "ערבית" in mode else row['word']
        
        st.markdown(f"<h1 style='text-align:center;'>{q}</h1>", unsafe_allow_html=True)
        
        if st.toggle("חשוף תשובה", key=f"ans_{st.session_state.current_idx}"):
            st.markdown(f"<h2 style='text-align:center; color:#00dc82;'>{a}</h2>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ הצלחתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "W-"
                new_lvl = min(8, row['level'] + 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = new_lvl
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=new_lvl)
                st.session_state.daily_correct += 1
                st.session_state.total_session_correct += 1
                del st.session_state.current_idx
                st.rerun()
            if c2.button("❌ טעיתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "L-"
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = max(1, row['level'] - 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                st.session_state.daily_wrong += 1
                del st.session_state.current_idx
                st.rerun()

# --- 7. דף קבוצות ---
elif st.session_state.page == "groups":
    st.title("🗂️ ניהול רשימות")
    df = st.session_state.master_df
    
    c1, c2 = st.columns(2)
    if c1.button("🎯 לתרגול היום"): st.session_state.list_view = "today"
    if c2.button("🔍 כל הרשימה"): st.session_state.list_view = "all"
    
    view = st.session_state.list_view
    if view == "today":
        today = pd.Timestamp.now().normalize()
        target_df = df[(df['next_review'] <= today) & (df['level'] < 8)]
    else:
        target_df = df
        
    st.dataframe(target_df[['word', 'translation', 'level', 'category']], use_container_width=True)

# --- 8. דף סטטיסטיקה ---
elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקה")
    df = st.session_state.master_df
    
    c1, c2 = st.columns(2)
    c1.metric("סה\"כ מילים", len(df))
    c2.metric("רמת FINAL", len(df[df['level'] == 8]))
    
    level_counts = df['level'].value_counts().sort_index().reset_index()
    level_counts.columns = ['Level', 'Count']
    fig = px.bar(level_counts, x='Level', y='Count', color='Count', color_continuous_scale='Greens')
    st.plotly_chart(fig, use_container_width=True)