import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# הגדרות דף
st.set_page_config(page_title="Arabic Learning App", dir="rtl")

# חיבור לגוגל שיטס באמצעות Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
    # ניקוי נתונים ריקים
    df = df.dropna(subset=['ערבית', 'תרגום'])
except Exception as e:
    st.error("שגיאת תקשורת עם הגיליון. וודא שה-Secrets מוגדרים ושניתנה גישת שיתוף למייל הבוט.")
    st.stop()

# אתחול מצב האפליקציה
if 'current_word' not in st.session_state:
    st.session_state.current_word = None
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False

def get_new_word():
    st.session_state.current_word = df.sample(n=1).iloc[0]
    st.session_state.show_answer = False

if st.session_state.current_word is None:
    get_new_word()

# עיצוב הממשק
st.title("מתרגלים ערבית 💡")

word = st.session_state.current_word

st.subheader("איך אומרים בעברית?")
st.markdown(f"### **{word['ערבית']}**")

if st.button("בדוק תשובה"):
    st.session_state.show_answer = True

if st.session_state.show_answer:
    st.success(f"התרגום הוא: **{word['תרגום']}**")
    if 'תעתיק' in word and pd.notna(word['תעתיק']):
        st.info(f"תעתיק: {word['תעתיק']}")
    
    if st.button("מילה הבאה"):
        get_new_word()
        st.rerun()