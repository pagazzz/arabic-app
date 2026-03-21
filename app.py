import streamlit as st
import pandas as pd
import datetime
import random
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- חיבור מאובטח לגוגל שיטס ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # טעינת הנתונים ישירות מהחיבור שהגדרת ב-Secrets
        df = conn.read(ttl=0) # ttl=0 מבטיח שהנתונים תמיד יהיו טריים
        st.toast("הנתונים נטענו מהענן! ☁️")
        return df
    except Exception as e:
        st.error(f"שגיאה בחיבור: {e}")
        return pd.DataFrame(columns=["word", "translation", "level", "next_review", "example"])

# --- ניהול מצב (Session State) ---
if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'page' not in st.session_state:
    st.session_state.page = "home"

# פונקציית שמירה שכותבת פיזית לגיליון גוגל
def save_to_cloud(updated_df):
    try:
        conn.update(data=updated_df)
        st.session_state.data = updated_df
        st.success("נשמר בגיליון גוגל! ✅")
    except Exception as e:
        st.error(f"שגיאה בשמירה: {e}")

# --- עיצוב ---
st.markdown("""
    <style>
    .main-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; border: 1px solid #eee; }
    .arabic-font { font-size: 48px !important; color: #2c3e50; font-family: 'Arial'; }
    .stButton>button { width: 100%; border-radius: 10px; height: 55px; font-weight: bold; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- דף בית (תרגול) ---
if st.session_state.page == "home":
    st.title("🛡️ המנטור לערבית")
    
    data = st.session_state.data
    today = str(datetime.date.today())
    
    # סינון מילים לתרגול (כולל המרה בטוחה של תאריכים)
    data['next_review'] = data['next_review'].astype(str)
    due_words = data[data['next_review'] <= today].copy()
    
    if not due_words.empty:
        if 'current_idx' not in st.session_state:
            st.session_state.current_idx = due_words.index[0]
        
        idx = st.session_state.current_idx
        curr = data.loc[idx]
        
        st.markdown(f'<div class="main-card"><p class="arabic-font">{curr["word"]}</p></div>', unsafe_allow_html=True)
        
        with st.expander("👁️ חשוף תשובה"):
            st.subheader(curr['translation'])
            if str(curr['example']) != 'nan' and curr['example'] != "":
                st.info(f"💡 {curr['example']}")
        
        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("✅ צדקתי"):
            # עדכון רמה ותאריך
            lvl = pd.to_numeric(data.at[idx, 'level'], errors='coerce')
            if pd.isna(lvl): lvl = 1
            new_lvl = int(lvl + 1)
            
            data.at[idx, 'level'] = new_lvl
            data.at[idx, 'next_review'] = str(datetime.date.today() + datetime.timedelta(days=new_lvl * 2))
            
            del st.session_state.current_idx
            save_to_cloud(data)
            st.rerun()
            
        if c2.button("❌ טעיתי"):
            data.at[idx, 'next_review'] = str(datetime.date.today() + datetime.timedelta(days=1))
            del st.session_state.current_idx
            save_to_cloud(data)
            st.rerun()
    else:
        st.success("סיימת הכל להיום! 🏆")
        if st.button("🔄 רענן נתונים"): 
            st.session_state.data = load_data()
            st.rerun()

    st.write("---")
    with st.expander("➕ הוספת מילה חדשה"):
        w = st.text_input("ערבית")
        t = st.text_input("עברית")
        ex = st.text_input("משפט לדוגמה")
        if st.button("שמור לגיליון"):
            new_row = pd.DataFrame([{"word": w, "translation": t, "level": 1, "next_review": today, "example": ex}])
            updated_df = pd.concat([st.session_state.data, new_row], ignore_index=True)
            save_to_cloud(updated_df)
            st.rerun()

    col1, col2 = st.columns(2)
    if col1.button("📂 ניהול"): st.session_state.page = "manager"; st.rerun()
    if col2.button("📊 סטטיסטיקה"): st.session_state.page = "stats"; st.rerun()

# --- דף ניהול ---
elif st.session_state.page == "manager":
    st.header("📂 מאגר המילים")
    if st.button("⬅️ חזרה"): st.session_state.page = "home"; st.rerun()
    st.write(f"סה\"כ מילים: {len(st.session_state.data)}")
    st.dataframe(st.session_state.data[['word', 'translation', 'level']], use_container_width=True)

# --- דף סטטיסטיקה ---
elif st.session_state.page == "stats":
    st.header("📊 התקדמות")
    if st.button("⬅️ חזרה"): st.session_state.page = "home"; st.rerun()
    fig = px.pie(st.session_state.data, names='level', title="חלוקה לפי רמות")
    st.plotly_chart(fig, use_container_width=True)
