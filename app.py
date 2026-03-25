 import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
from datetime import datetime

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Arabic Mentor Pro", layout="wide")

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def fetch_from_sheets():
    df = conn.read(ttl=0)
    for col in ['word', 'translation', 'level', 'next_review', 'wrong_streak', 'date_added']:
        if col not in df.columns:
            if col == 'wrong_streak': df[col] = 0
            elif col == 'level': df[col] = 1
            elif col == 'date_added': df[col] = pd.Timestamp.now().strftime('%Y-%m-%d')
            else: df[col] = ""
    
    df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').dt.normalize()
    df['date_added'] = pd.to_datetime(df['date_added'], errors='coerce').dt.normalize()
    df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
    df['wrong_streak'] = pd.to_numeric(df['wrong_streak'], errors='coerce').fillna(0).astype(int)
    return df

# --- 3. ניהול Session State ---
if "master_df" not in st.session_state:
    st.session_state.master_df = fetch_from_sheets()

for key, val in [("page", "home"), ("daily_correct", 0), ("daily_wrong", 0)]:
    if key not in st.session_state:
        st.session_state[key] = val

df = st.session_state.master_df
level_map = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"FINAL"}

# --- 4. Sidebar ---
with st.sidebar:
    st.title("Arabic Pro 🧠")
    if st.button("🏠 תרגול יומי", use_container_width=True): st.session_state.page = "home"
    if st.button("📖 מרכז למידה (קשות)", use_container_width=True): st.session_state.page = "learning"
    if st.button("📋 רשימות מילים", use_container_width=True): st.session_state.page = "lists"
    st.divider()
    if st.button("💾 שמירה לענן (SAVE)", type="primary", use_container_width=True):
        df_save = st.session_state.master_df.copy()
        df_save['next_review'] = df_save['next_review'].dt.strftime('%Y-%m-%d')
        df_save['date_added'] = df_save['date_added'].dt.strftime('%Y-%m-%d')
        conn.update(data=df_save)
        st.toast("נשמר!")

# --- 5. דף למידה (מילים קשות) ---
if st.session_state.page == "learning":
    st.title("📖 מילים ללמידה מרוכזת")
    two_months_ago = pd.Timestamp.now().normalize() - pd.Timedelta(days=60)
    
    # סינון לפי הקריטריונים שלך
    hard_words = df[
        (df['wrong_streak'] >= 4) | 
        ((df['date_added'] < two_months_ago) & (df['level'] < 8))
    ]
    
    if hard_words.empty:
        st.success("אין כרגע מילים שמוגדרות כ'קשות'. כל הכבוד!")
    else:
        sample_size = min(5, len(hard_words))
        study_set = hard_words.sample(sample_size)
        st.write(f"הנה {sample_size} מילים שדורשות תשומת לב מיוחדת:")
        for idx, row in study_set.iterrows():
            with st.expander(f"מילה: {row['word']}"):
                st.write(f"**תרגום:** {row['translation']}")
                st.write(f"**רמה:** {level_map[row['level']]}")
                st.write(f"**רצף טעויות:** {row['wrong_streak']}")

# --- 6. דף הבית (תרגול) ---
elif st.session_state.page == "home":
    today = pd.Timestamp.now().normalize()
    due_words = df[(df['next_review'] <= today) & (df['level'] < 8)]
    
    # יחס הצלחה
    total = st.session_state.daily_correct + st.session_state.daily_wrong
    rate = (st.session_state.daily_correct / total * 100) if total > 0 else 0
    st.write(f"### הצלחה: {rate:.0f}% | נותרו: {len(due_words)}")
    st.markdown(f'<div style="width:100%; background:#eee; height:10px;"><div style="width:{rate}%; background:#00dc82; height:100%;"></div></div>', unsafe_allow_html=True)

    if due_words.empty:
        st.success("סיימת להיום!")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_words.index:
            st.session_state.current_idx = random.choice(due_words.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        st.markdown(f"**רמה: {level_map[row['level']]}**") # תצוגת רמה
        
        mode = st.radio("כיוון:", ["ערבית ⬅️ עברית", "עברית ⬅️ ערבית"], horizontal=True)
        q = row['word'] if "ערבית ⬅️" in mode else row['translation']
        a = row['translation'] if "ערבית ⬅️" in mode else row['word']
        
        st.info(f"# {q}")
        if st.toggle("הצג תשובה", key=f"ans_{st.session_state.current_idx}"):
            st.success(f"# {a}")
            c1, c2 = st.columns(2)
            if c1.button("✅ נכון"):
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = min(8, row['level'] + 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=row['level']+1)
                st.session_state.master_df.at[st.session_state.current_idx, 'wrong_streak'] = 0
                st.session_state.daily_correct += 1
                del st.session_state.current_idx
                st.rerun()
            if c2.button("❌ טעות"):
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = max(1, row['level'] - 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                st.session_state.master_df.at[st.session_state.current_idx, 'wrong_streak'] += 1
                st.session_state.daily_wrong += 1
                del st.session_state.current_idx
                st.rerun()

# (דף רשימות נשאר כפי שהיה בגרסאות קודמות)
