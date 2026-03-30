import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
import plotly.express as px
from datetime import datetime, timedelta

# --- הגדרות דף ---
st.set_page_config(page_title="Arabic Mentor Ultra", layout="wide")

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def fetch_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        # השלמת עמודות קריטיות
        cols = ['word', 'translation', 'level', 'next_review', 'category', 'date_added']
        for col in cols:
            if col not in df.columns: df[col] = "כללי" if col == 'category' else ""
        
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').fillna(pd.Timestamp.now()).dt.normalize()
        df['date_added'] = pd.to_datetime(df['date_added'], errors='coerce').fillna(pd.Timestamp.now()).dt.normalize()
        return df
    except: return pd.DataFrame()

# --- Session State ---
if "master_df" not in st.session_state: st.session_state.master_df = fetch_data()
if "page" not in st.session_state: st.session_state.page = "home"
if "daily_correct" not in st.session_state: st.session_state.daily_correct = 0
if "daily_wrong" not in st.session_state: st.session_state.daily_wrong = 0

# --- פונקציות עזר ---
def save_to_cloud():
    df_save = st.session_state.master_df.copy()
    df_save['next_review'] = df_save['next_review'].dt.strftime('%Y-%m-%d')
    df_save['date_added'] = df_save['date_added'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.toast("הנתונים נשמרו בענן! ☁️")

# --- Sidebar ---
with st.sidebar:
    st.title("Arabic Mentor 🧠")
    st.subheader(f"ניקוד יומי: {st.session_state.daily_correct - st.session_state.daily_wrong}")
    st.divider()
    if st.button("🏠 תרגול יומי", use_container_width=True): st.session_state.page = "home"
    if st.button("🗂️ רשימת המילים", use_container_width=True): st.session_state.page = "list"
    if st.button("📊 סטטיסטיקה", use_container_width=True): st.session_state.page = "stats"
    st.divider()
    if st.button("💾 שמירה סופית", type="primary", use_container_width=True): save_to_cloud()

# --- 1. דף הבית (תרגול) ---
if st.session_state.page == "home":
    df = st.session_state.master_df
    today = pd.Timestamp.now().normalize()
    due_words = df[df['next_review'] <= today]

    if due_words.empty:
        st.balloons()
        st.success("סיימת את כל המילים להיום! יא אלוף 🏆")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_words.index:
            st.session_state.current_idx = random.choice(due_words.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        
        # --- מד סיכויי הצלחה ---
        # חישוב פשוט: ככל שהרמה גבוהה יותר, סיכוי ההצלחה גדל
        chance = min(95, row['level'] * 12 + random.randint(-5, 5))
        st.write(f"סיכוי הצלחה מוערך: **{chance}%**")
        st.progress(chance / 100)
        
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; padding: 40px;'>{row['word']}</h1>", unsafe_allow_html=True)
        
        # הבאג של ה-Toggle נפתר כאן (ID ייחודי לכל מילה)
        show = st.toggle("חשוף תשובה", key=f"tgl_{st.session_state.current_idx}")
        
        if show:
            st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{row['translation']}</h2>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ ידעתי", use_container_width=True):
                    st.session_state.master_df.at[st.session_state.current_idx, 'level'] += 1
                    st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=row['level']*2)
                    st.session_state.daily_correct += 1
                    del st.session_state.current_idx
                    st.rerun()
            with c2:
                if st.button("❌ טעיתי", use_container_width=True):
                    st.session_state.master_df.at[st.session_state.current_idx, 'level'] = 1
                    st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                    st.session_state.daily_wrong += 1
                    del st.session_state.current_idx
                    st.rerun()

# --- 2. דף רשימת המילים (עם סינון רמות) ---
elif st.session_state.page == "list":
    st.title("🗂️ ניהול רשימות")
    
    levels = sorted(st.session_state.master_df['level'].unique())
    selected_level = st.select_slider("סנן לפי רמה:", options=["הכל"] + list(levels))
    
    display_df = st.session_state.master_df.copy()
    if selected_level != "הכל":
        display_df = display_df[display_df['level'] == selected_level]
    
    st.dataframe(display_df[['word', 'translation', 'level', 'next_review', 'category']], use_container_width=True)

# --- 3. דף סטטיסטיקה מפורט ---
elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקה וביצועים")
    df = st.session_state.master_df
    
    col1, col2, col3 = st.columns(3)
    col1.metric("סה\"כ מילים במערכת", len(df))
    col2.metric("מילים שנלמדו (רמה 5+)", len(df[df['level'] >= 5]))
    col3.metric("מילים חדשות השבוע", len(df[df['date_added'] > (pd.Timestamp.now() - pd.Timedelta(days=7))]))
    
    st.divider()
    
    # גרף התפלגות רמות
    st.subheader("התפלגות רמות הלמידה")
    lvl_dist = df['level'].value_counts().sort_index().reset_index()
    lvl_dist.columns = ['רמה', 'כמות מילים']
    fig_lvl = px.bar(lvl_dist, x='רמה', y='כמות מילים', color='כמות מילים', color_continuous_scale='Viridis')
    st.plotly_chart(fig_lvl, use_container_width=True)
    
    # גרף קצב התקדמות (לפי תאריך הוספה)
    st.subheader("קצב הוספת מילים חדשות")
    df_growth = df.groupby('date_added').size().cumsum().reset_index()
    df_growth.columns = ['תאריך', 'סה"כ מילים']
    fig_growth = px.line(df_growth, x='תאריך', y='סה"כ מילים', markers=True)
    st.plotly_chart(fig_growth, use_container_width=True)