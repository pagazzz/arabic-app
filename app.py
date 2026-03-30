import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
import plotly.express as px

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Arabic Mentor Ultra", layout="wide")

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def fetch_data():
    try:
        df = conn.read(ttl=0)
        # רשימת עמודות שהקוד חייב כדי לעבוד
        required_cols = {
            'word': "", 'translation': "", 'level': 1, 
            'next_review': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'category': "כללי", 'history': "", 'date_added': pd.Timestamp.now().strftime('%Y-%m-%d')
        }
        # אם עמודה חסרה בגיליון, נוסיף אותה זמנית עם ערך ברירת מחדל
        for col, default in required_cols.items():
            if col not in df.columns:
                df[col] = default
        
        # ניקוי פורמטים
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').fillna(pd.Timestamp.now()).dt.normalize()
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת הנתונים: {e}")
        return pd.DataFrame()

# --- 3. Session State ---
if "master_df" not in st.session_state or st.session_state.master_df.empty:
    st.session_state.master_df = fetch_data()

if "page" not in st.session_state: st.session_state.page = "home"
if "daily_correct" not in st.session_state: st.session_state.daily_correct = 0
if "daily_wrong" not in st.session_state: st.session_state.daily_wrong = 0

level_names = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"FINAL"}

# --- 4. Sidebar ---
with st.sidebar:
    st.title("Arabic Mentor 🧠")
    if st.button("🏠 דף הבית"): st.session_state.page = "home"
    if st.button("🗂️ קבוצות מילים"): st.session_state.page = "groups"
    if st.button("📊 סטטיסטיקה"): st.session_state.page = "stats"
    st.divider()
    if st.button("💾 שמירה לענן", type="primary"):
        df_to_save = st.session_state.master_df.copy()
        df_to_save['next_review'] = df_to_save['next_review'].dt.strftime('%Y-%m-%d')
        conn.update(data=df_to_save)
        st.toast("✅ נשמר בהצלחה!")

# --- 5. דף הבית (תרגול) ---
if st.session_state.page == "home":
    st.title("🏠 תרגול יומי")
    df = st.session_state.master_df
    today = pd.Timestamp.now().normalize()
    
    # סינון מילים לתרגול
    due_words = df[(df['next_review'] <= today) & (df['level'] < 8)]
    
    if due_words.empty:
        st.success("אין מילים לתרגול כרגע! 🎉")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_words.index:
            st.session_state.current_idx = random.choice(due_words.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        st.write(f"**רמה:** {level_names.get(row['level'], 'I')}")
        
        q = row['word']
        a = row['translation']
        
        st.info(f"# {q}")
        if st.toggle("חשוף תשובה"):
            st.success(f"# {a}")
            c1, c2 = st.columns(2)
            if c1.button("✅ הצלחתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = min(8, row['level'] + 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=row['level'])
                st.session_state.daily_correct += 1
                del st.session_state.current_idx
                st.rerun()
            if c2.button("❌ טעיתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = max(1, row['level'] - 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                st.session_state.daily_wrong += 1
                del st.session_state.current_idx
                st.rerun()

# --- 6. דפי ניהול וסטטיסטיקה (מקוצר) ---
elif st.session_state.page == "groups":
    st.title("🗂️ רשימת המילים")
    st.dataframe(st.session_state.master_df[['word', 'translation', 'level', 'next_review']])

elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקה")
    st.metric("סה\"כ מילים", len(st.session_state.master_df))
    level_counts = st.session_state.master_df['level'].value_counts().sort_index().reset_index()
    fig = px.bar(level_counts, x='level', y='count', title="התפלגות רמות")
    st.plotly_chart(fig)