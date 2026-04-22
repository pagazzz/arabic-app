import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
from datetime import datetime

# --- 1. הגדרות דף ועיצוב CSS ---
st.set_page_config(page_title="Arabic Mentor Ultra v5", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 10px; height: 3.5em; font-weight: bold; width: 100%; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .category-tag { background-color: #e3f2fd; color: #0d47a1; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 1em; border: 1px solid #bbdefb; }
    .hard-word-tag { color: #d32f2f; font-weight: bold; border: 2px solid #d32f2f; padding: 3px 10px; border-radius: 5px; background-color: #ffebee; }
    .stats-card { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1 { color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ופונקציות טעינה ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_and_initialize_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame()
        
        # וידוא קיום כל העמודות שדיברנו עליהן
        columns_specs = {
            'word': "", 
            'translation': "", 
            'level': 1, 
            'next_review': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'category': "כללי", 
            'history': "", 
            'date_added': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'last_seen': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'punished': 0
        }
        
        for col, default in columns_specs.items():
            if col not in df.columns:
                df[col] = default
        
        # ניקוי וסידור סוגי נתונים
        df['history'] = df['history'].astype(str).replace(['nan', 'None', 'NaN'], '')
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').dt.normalize()
        df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce').dt.normalize()
        df['date_added'] = pd.to_datetime(df['date_added'], errors='coerce').dt.normalize()
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        df['punished'] = pd.to_numeric(df['punished'], errors='coerce').fillna(0).astype(int)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- 3. לוגיקת עונשים (Punishment System) ---
def process_punishments(df):
    today = pd.Timestamp.now().normalize()
    # מילה שמועד התרגול שלה עבר (לפני היום) והיא לא ברמה סופית
    overdue_condition = (df['next_review'] < today) & (df['level'] < 8)
    
    indices_to_punish = df[overdue_condition].index
    
    for idx in indices_to_punish:
        # עונש 1: המילה מופיעה היום לתרגול
        df.at[idx, 'next_review'] = today
        # עונש 2: 50% סיכוי לירידת רמה
        if random.random() < 0.5:
            current_lvl = df.at[idx, 'level']
            if current_lvl > 1:
                df.at[idx, 'level'] = current_lvl - 1
                df.at[idx, 'punished'] += 1
                
    return df

# --- 4. ניהול Session State ---
if "master_df" not in st.session_state:
    raw_data = load_and_initialize_data()
    st.session_state.master_df = process_punishments(raw_data)

if "today_mistakes" not in st.session_state:
    st.session_state.today_mistakes = []

# ערכי ברירת מחדל למשתני ניווט
state_keys = {
    "page": "home",
    "daily_correct": 0,
    "daily_wrong": 0,
    "practice_direction": "ערבית ⬅️ עברית",
    "list_view_filter": "all"
}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

level_map = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"FINAL"}

# --- 5. פונקציות עזר לשמירה וזיהוי ---
def save_data_to_sheets():
    df_to_save = st.session_state.master_df.copy()
    # המרת תאריכים לטקסט לפני שמירה
    date_cols = ['next_review', 'last_seen', 'date_added']
    for col in date_cols:
        df_to_save[col] = df_to_save[col].dt.strftime('%Y-%m-%d')
    
    conn.update(data=df_to_save)
    st.cache_data.clear()
    st.toast("✅ הנתונים נשמרו בגיליון בהצלחה!")

def check_if_hard(history):
    return history.endswith("L-L-L-")

# --- 6. Sidebar ---
with st.sidebar:
    st.title("Arabic Mentor Ultra 🧠")
    st.markdown("---")
    if st.button("🏠 דף הבית (תרגול)", use_container_width=True): st.session_state.page = "home"
    if st.button("🗂️ ניהול רשימות", use_container_width=True): st.session_state.page = "groups"
    if st.button("📊 סטטיסטיקה", use_container_width=True): st.session_state.page = "stats"
    
    st.markdown("---")
    st.session_state.practice_direction = st.radio("כיוון תרגול:", ["ערבית ⬅️ עברית", "עברית ⬅️ ערבית"])
    
    st.markdown("---")
    if st.button("💾 שמירה סופית לענן", type="primary", use_container_width=True):
        save_data_to_sheets()
    
    # מונה הצלחות קטן בצד
    st.write(f"הצלחות היום: {st.session_state.daily_correct}")
    st.write(f"טעויות היום: {st.session_state.daily_wrong}")

# --- 7. דף הבית (תרגול והוספה) ---
if st.session_state.page == "home":
    st.title("🏠 תרגול יומי")
    
    # מנגנון הוספת מילה חדשה
    with st.expander("➕ הוספת מילה חדשה למערכת"):
        with st.form("new_word_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            w_arb = c1.text_input("מילה בערבית")
            w_heb = c2.text_input("תרגום לעברית")
            w_cat = c3.text_input("קבוצה", value="כללי")
            if st.form_submit_button("הוסף לגיליון"):
                new_entry = pd.DataFrame([{
                    'word': w_arb, 'translation': w_heb, 'level': 1, 'category': w_cat,
                    'next_review': pd.Timestamp.now().normalize(), 'history': '',
                    'date_added': pd.Timestamp.now().normalize(), 'last_seen': pd.Timestamp.now().normalize(),
                    'punished': 0
                }])
                st.session_state.master_df = pd.concat([st.session_state.master_df, new_entry], ignore_index=True)
                st.success(f"המילה '{w_arb}' נוספה!")

    # לוגיקת תרגול
    today = pd.Timestamp.now().normalize()
    df = st.session_state.master_df
    # מילים לתרגול: רמה מתחת ל-8 ותאריך היום או לפני
    due_today = df[(df['next_review'] <= today) & (df['level'] < 8)]
    
    st.subheader(f"נשארו לך עוד **{len(due_today)}** מילים לתרגל היום")

    if due_today.empty:
        st.balloons()
        st.success("כל הכבוד! סיימת את כל המילים להיום. 🎉")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_today.index:
            st.session_state.current_idx = random.choice(due_today.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        
        # עדכון פעם אחרונה שנראה
        st.session_state.master_df.at[st.session_state.current_idx, 'last_seen'] = today

        # תצוגת קבוצה וסימון מילה קשה
        st.markdown(f"<span class='category-tag'>📁 קבוצה: {row['category']}</span>", unsafe_allow_html=True)
        if check_if_hard(row['history']):
            st.markdown("<span class='hard-word-tag'>🔥 מילה קשה</span>", unsafe_allow_html=True)

        # בחירת שאלה ותשובה לפי הכיוון
        if st.session_state.practice_direction == "ערבית ⬅️ עברית":
            question, answer = row['word'], row['translation']
        else:
            question, answer = row['translation'], row['word']

        st.markdown(f"<h1 style='text-align: center; font-size: 90px; padding: 40px;'>{question}</h1>", unsafe_allow_html=True)
        
        if st.toggle("חשוף תשובה", key=f"toggle_{st.session_state.current_idx}"):
            st.markdown(f"<h2 style='text-align: center; color: #2e7d32; font-size: 50px;'>{answer}</h2>", unsafe_allow_html=True)
            
            b1, b2 = st.columns(2)
            if b1.button("✅ ידעתי"):
                # הצלחה: רמה עולה, תאריך תרגול זז קדימה
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "W-"
                new_lvl = min(8, row['level'] + 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = new_lvl
                # מרווח תרגול לפי הרמה (למשל: רמה 3 = עוד 6 ימים)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=new_lvl * 2)
                st.session_state.daily_correct += 1
                del st.session_state.current_idx
                st.rerun()
                
            if b2.button("❌ טעיתי"):
                # טעות: רמה יורדת ב-100%, תרגול חוזר מחר
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "L-"
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = max(1, row['level'] - 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                st.session_state.daily_wrong += 1
                # הוספה לרשימת הטעויות היומית לתרגול חוזר
                if st.session_state.current_idx not in st.session_state.today_mistakes:
                    st.session_state.today_mistakes.append(st.session_state.current_idx)
                del st.session_state.current_idx
                st.rerun()

# --- 8. דף ניהול רשימות (הממשק המורחב עם הכפתורים) ---
elif st.session_state.page == "groups":
    st.title("🗂️ ניהול רשימות וסינונים")
    
    # שורת כפתורי ניווט מהירים
    st.subheader("סינונים מיוחדים:")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🌐 כל המילים"): st.session_state.list_view_filter = "all"
    if c2.button("🔥 מילים קשות (L-L-L)"): st.session_state.list_view_filter = "hard"
    if c3.button("⚠️ טעויות מהיום"): st.session_state.list_view_filter = "mistakes"
    if c4.button("🏆 רמה FINAL"): st.session_state.list_view_filter = 8

    st.subheader("סינון לפי רמה:")
    lvl_cols = st.columns(7)
    for i in range(1, 8):
        if lvl_cols[i-1].button(f"רמה {level_map[i]}"):
            st.session_state.list_view_filter = i

    st.divider()

    # לוגיקת הצגת הטבלה
    view = st.session_state.list_view_filter
    df_display = st.session_state.master_df
    
    if view == "hard":
        df_display = df_display[df_display['history'].str.endswith("L-L-L-")]
    elif view == "mistakes":
        df_display = df_display.loc[st.session_state.today_mistakes]
    elif isinstance(view, int):
        df_display = df_display[df_display['level'] == view]

    # כפתור תרגול ממוקד (Sandbox)
    if view in ["hard", "mistakes"] and not df_display.empty:
        st.warning(f"מציג {len(df_display)} מילים. תרגול זה אינו משפיע על הרמות בגיליון.")
        if st.button(f"🚀 התחל תרגול ממוקד: {view}", type="primary"):
            st.session_state.page = "special_practice"
            st.session_state.special_list_indices = df_display.index.tolist()
            st.rerun()

    st.dataframe(df_display[['word', 'translation', 'level', 'category', 'punished', 'last_seen']], use_container_width=True)

# --- 9. דף תרגול מיוחד (Special Practice / Sandbox) ---
elif st.session_state.page == "special_practice":
    st.title("🎯 תרגול ממוקד (מצב Sandbox)")
    if st.button("🔙 חזרה לניהול רשימות"): st.session_state.page = "groups"; st.rerun()
    
    indices = st.session_state.get("special_list_indices", [])
    if not indices:
        st.info("אין מילים לתרגול בסינון זה.")
    else:
        if "spec_idx" not in st.session_state or st.session_state.spec_idx not in indices:
            st.session_state.spec_idx = random.choice(indices)
        
        row = st.session_state.master_df.loc[st.session_state.spec_idx]
        st.markdown(f"<h1 style='text-align: center; font-size: 70px;'>{row['word']}</h1>", unsafe_allow_html=True)
        
        if st.toggle("חשוף תשובה", key="spec_toggle"):
            st.write(f"### {row['translation']}")
            if st.button("המילה הבאה ➡️"):
                del st.session_state.spec_idx
                st.rerun()

# --- 10. דף סטטיסטיקה ---
elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקה וביצועים")
    df = st.session_state.master_df
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("סה\"כ מילים במערכת", len(df))
    with col2:
        st.metric("מילים שסיימו (FINAL)", len(df[df['level'] == 8]))
    with col3:
        st.metric("סה\"כ עונשים שחולקו 🍎", df['punished'].sum())

    st.divider()
    st.subheader("התפלגות רמות הלמידה")
    # יצירת גרף התפלגות רמות
    lvl_counts = df['level'].value_counts().sort_index().reset_index()
    lvl_counts.columns = ['Level', 'Count']
    import plotly.express as px
    fig = px.bar(lvl_counts, x='Level', y='Count', color='Count', color_continuous_scale='Blues')
    st.plotly_chart(fig, use_container_width=True)
