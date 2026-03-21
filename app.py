import streamlit as st
import pandas as pd
import datetime
import os
import random
import plotly.express as px

# --- הגדרות ---
SHEET_ID = "1Nm1YozZqkQ7iy11ivmC-ukARGXJWy_bzpeXQIUMxMbg"
CLOUD_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def load_data():
    # ניסיון טעינה ראשוני מהענן
    try:
        df = pd.read_csv(CLOUD_URL)
        st.toast("סונכרן מהענן! ☁️")
    except:
        # אם הענן נכשל, ניצור דאטה-פריים ריק עם עמודות
        df = pd.DataFrame(columns=["word", "translation", "level", "next_review", "last_seen", "punished", "example"])
    
    # ניקוי נתונים ו-וידוא עמודות
    for col in ["level", "next_review", "last_seen", "punished", "example"]:
        if col not in df.columns: df[col] = ""
    
    # המרת תאריכים לפורמט טקסט אחיד
    df['next_review'] = df['next_review'].fillna(str(datetime.date.today()))
    df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
    return df

# --- ניהול מצב (Session State) ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'page' not in st.session_state:
    st.session_state.page = "home"

# פונקציית שמירה שמעדכנת את הזיכרון של האפליקציה
def save_data():
    st.session_state.data = st.session_state.data # מעדכן את ה-state

# --- עיצוב מותאם לנייד ---
st.markdown("""
    <style>
    .main-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; }
    .arabic-font { font-size: 45px !important; color: #2c3e50; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- דף בית (תרגול) ---
if st.session_state.page == "home":
    st.title("🛡️ My Arabic Mentor")
    
    data = st.session_state.data
    today = str(datetime.date.today())
    
    # סינון מילים לתרגול
    due_words = data[data['next_review'] <= today].copy()
    
    if not due_words.empty:
        # בוחרים מילה אחת אקראית מתוך התור
        if 'current_idx' not in st.session_state:
            st.session_state.current_idx = due_words.index[0]
        
        idx = st.session_state.current_idx
        curr = data.loc[idx]
        
        st.markdown(f'<div class="main-card"><p class="arabic-font">{curr["word"]}</p></div>', unsafe_allow_html=True)
        
        with st.expander("👁️ חשוף תשובה"):
            st.write(f"**תרגום:** {curr['translation']}")
            if str(curr['example']) != 'nan':
                st.info(f"💡 {curr['example']}")
        
        c1, c2 = st.columns(2)
        if c1.button("✅ צדקתי"):
            # וידוא שהרמה היא מספר לפני החישוב
            current_lvl = pd.to_numeric(data.at[idx, 'level'], errors='coerce')
            if pd.isna(current_lvl): current_lvl = 1
            
            new_lvl = int(current_lvl + 1)
            data.at[idx, 'level'] = new_lvl
            
            # חישוב ימים לתצוגה הבאה (לפי הרמה)
            delta_days = new_lvl * 2
            data.at[idx, 'next_review'] = str(datetime.date.today() + datetime.timedelta(days=delta_days))
            
            if 'current_idx' in st.session_state:
                del st.session_state.current_idx
            save_data()
            st.rerun()
            
        if c2.button("❌ טעיתי"):
            data.at[idx, 'next_review'] = str(datetime.date.today() + datetime.timedelta(days=1))
            if 'current_idx' in st.session_state:
                del st.session_state.current_idx
            save_data()
            st.rerun()
    else:
        st.success("סיימת הכל להיום! 🏆")

    st.write("---")
    # הוספת מילה (עובד לתוך ה-Session)
    with st.expander("➕ הוספת מילה חדשה"):
        w = st.text_input("מילה בערבית")
        t = st.text_input("תרגום לעברית")
        ex = st.text_input("משפט לדוגמה")
        if st.button("שמור אצלי"):
            new_row = pd.DataFrame([{"word": w, "translation": t, "level": 1, "next_review": today, "example": ex}])
            st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
            st.success("המילה נוספה בהצלחה!")
            st.rerun()

    # ניווט
    col1, col2 = st.columns(2)
    if col1.button("📂 כל המילים"): st.session_state.page = "manager"; st.rerun()
    if col2.button("📊 ביצועים"): st.session_state.page = "stats"; st.rerun()

# --- דף ניהול מילים (מתוקן לנייד) ---
elif st.session_state.page == "manager":
    st.header("📂 רשימת המילים שלי")
    if st.button("⬅️ חזרה"): st.session_state.page = "home"; st.rerun()
    
    for i, row in st.session_state.data.iterrows():
        with st.container():
            st.markdown(f"**{row['word']}** - {row['translation']} (Lvl {row['level']})")
            st.write(f"---")

# --- דף סטטיסטיקות ---
elif st.session_state.page == "stats":
    st.header("📊 מצב הלימוד")
    if st.button("⬅️ חזרה"): st.session_state.page = "home"; st.rerun()
    levels = st.session_state.data['level'].value_counts()
    fig = px.bar(levels, title="מילים לפי רמה")
    st.plotly_chart(fig, use_container_width=True)
