import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# הגדרות דף - הסרנו את dir="rtl" כדי למנוע קריסה בשרת
st.set_page_config(page_title="Arabic Learning App", layout="centered")

# חיבור לגוגל שיטס באמצעות Secrets
# חיבור לגוגל שיטס באמצעות Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
    # ניקוי שורות ריקות לפי שמות העמודות בגיליון
    df = df.dropna(subset=['word', 'translation'])
except Exception as e:
    st.error(f"פרטי השגיאה: {e}") # זה יגיד לנו מה הבעיה המדויקת
    st.stop()

# אתחול מצב האפליקציה (Session State)
if 'current_word' not in st.session_state:
    st.session_state.current_word = None
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

def get_new_word():
    if not df.empty:
        st.session_state.current_word = df.sample(n=1).iloc[0]
        st.session_state.show_answer = False

if st.session_state.current_word is None:
    get_new_word()

# ממשק המשתמש (UI)
st.title("מתרגלים ערבית 💡")

if st.session_state.current_word is not None:
    word_data = st.session_state.current_word
    
    st.subheader("איך אומרים בעברית?")
    # הצגת המילה בערבית מהעמודה 'word'
    st.markdown(f"## **{word_data['word']}**")

    if st.button("בדוק תשובה"):
        st.session_state.show_answer = True

    if st.session_state.show_answer:
        # הצגת התרגום מהעמודה 'translation'
        st.success(f"התרגום הוא: **{word_data['translation']}**")
        
        if st.button("מילה הבאה"):
            get_new_word()
            st.rerun()
else:
    st.warning("לא נמצאו נתונים בגיליון.")