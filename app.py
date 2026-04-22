import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
from datetime import datetime, timedelta

# --- 1. הגדרות דף ועיצוב ---
st.set_page_config(page_title="Arabic Mentor Ultra v3", layout="wide")
st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; height: 3em; font-weight: bold; width: 100%; }
    .hard-word { color: #ff4b4b; font-weight: bold; border: 1px solid #ff4b4b; padding: 2px 5px; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def fetch_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        
        # עמודות נדרשות כולל החדשות
        required_cols = {
            'word': "", 'translation': "", 'level': 1, 
            'next_review': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'category': "כללי", 'history': "", 'date_added': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'last_seen': pd.Timestamp.now().strftime('%Y-%m-%d'), # חדש
            'punished': 0 # חדש
        }
        for col, default in required_cols.items():
            if col not in df.columns:
                df[col] = default
        
        # ניקוי פורמטים
        df['history'] = df['history'].astype(str).replace(['nan', 'None', 'NaN'], '')
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').dt.normalize()
        df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce').dt.normalize()
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        df['punished'] = pd.to_numeric(df['punished'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינה: {e}")
        return pd.DataFrame()

# --- 3. לוגיקת עונשים (Punishment System) ---
def apply_daily_punishment(df):
    today = pd.Timestamp.now().normalize()
    # מילה שהייתה צריכה להיענות לפני היום ולא נענתה
    overdue_mask = (df['next_review'] < today) & (df['level'] < 8)
    
    for idx in df[overdue_mask].index:
        # עונש: תופיע למחרת (היום)
        df.at[idx, 'next_review'] = today
        # 50% סיכוי לירידת רמה
        if random.random() < 0.5:
            df.at[idx, 'level'] = max(1, df.at[idx, 'level'] - 1)
            df.at[idx, 'punished'] += 1
    return df

# --- 4. אתחול Session State ---
if "master_df" not in st.session_state:
    raw_df = fetch_data()
    st.session_state.master_df = apply_daily_punishment(raw_df)

defaults = {
    "page": "home", "daily_correct": 0, "daily_wrong": 0, 
    "practice_direction": "ערבית ⬅️ עברית", "temp_hard_words": []
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 5. פונקציות עזר ---
def save_to_cloud():
    df_save = st.session_state.master_df.copy()
    df_save['next_review'] = df_save['next_review'].dt.strftime('%Y-%m-%d')
    df_save['last_seen'] = df_save['last_seen'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.toast("✅ הנתונים נשמרו בגיליון!")

def is_hard_word(history_str):
    # בודק אם 3 התווים האחרונים בהיסטוריה הם "L-L-L-"
    return history_str.endswith("L-L-L-")

# --- 6. Sidebar ---
with st.sidebar:
    st.title("Arabic Mentor 🧠")
    if st.button("🏠 דף הבית (תרגול)"): st.session_state.page = "home"
    if st.button("🗂️ ניהול רשימות"): st.session_state.page = "groups"
    if st.button("📊 סטטיסטיקה"): st.session_state.page = "stats"
    st.divider()
    st.session_state.practice_direction = st.radio("כיוון תרגול:", ["ערבית ⬅️ עברית", "עברית ⬅️ ערבית"])
    st.divider()
    if st.button("💾 שמירה סופית", type="primary"): save_to_cloud()

# --- 7. דף הבית ---
if st.session_state.page == "home":
    st.title("🏠 תרגול יומי")
    
    # פיצ'ר הוספת מילה (בתוך דף הבית)
    with st.expander("➕ הוסף מילה חדשה למערכת"):
        with st.form("add_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            w = c1.text_input("ערבית")
            t = c2.text_input("עברית")
            cat = c3.text_input("קבוצה", value="כללי")
            if st.form_submit_button("שמור מילה"):
                new_row = pd.DataFrame([{'word': w, 'translation': t, 'level': 1, 'category': cat, 
                                         'next_review': pd.Timestamp.now().normalize(), 'history': '',
                                         'date_added': pd.Timestamp.now().normalize(), 'punished': 0}])
                st.session_state.master_df = pd.concat([st.session_state.master_df, new_row], ignore_index=True)
                st.success("נוסף!")

    df = st.session_state.master_df
    today = pd.Timestamp.now().normalize()
    due_words = df[(df['next_review'] <= today) & (df['level'] < 8)]
    
    st.metric("מילים שנותרו להיום", len(due_words))

    if due_words.empty:
        st.success("סיימת הכל! 🏆")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_words.index:
            st.session_state.current_idx = random.choice(due_words.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        
        # עדכון last_seen (פנימי ל-Session)
        st.session_state.master_df.at[st.session_state.current_idx, 'last_seen'] = today

        # תצוגה
        q = row['word'] if "ערבית" in st.session_state.practice_direction else row['translation']
        a = row['translation'] if "ערבית" in st.session_state.practice_direction else row['word']
        
        if is_hard_word(row['history']): st.markdown("<span class='hard-word'>מילה קשה 🔥</span>", unsafe_allow_html=True)
        
        st.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{q}</h1>", unsafe_allow_html=True)
        
        if st.toggle("חשוף תשובה", key=f"ans_{st.session_state.current_idx}"):
            st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{a}</h2>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ ידעתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "W-"
                new_lvl = min(8, row['level'] + 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = new_lvl
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=new_lvl*2)
                st.session_state.daily_correct += 1
                del st.session_state.current_idx
                st.rerun()
            if c2.button("❌ טעיתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "L-"
                # ירידה רמה ב-100% (סעיף 4)
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = max(1, row['level'] - 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                st.session_state.daily_wrong += 1
                del st.session_state.current_idx
                st.rerun()

# --- 8. דף ניהול רשימות ---
elif st.session_state.page == "groups":
    st.title("🗂️ ניהול רשימות")
    df = st.session_state.master_df
    
    # זיהוי מילים קשות
    hard_words_df = df[df['history'].str.endswith("L-L-L-")].copy()
    
    tab1, tab2 = st.tabs(["כל המילים", "🔥 מילים קשות"])
    
    with tab1:
        st.dataframe(df)
        
    with tab2:
        st.subheader(f"מצאנו {len(hard_words_df)} מילים שטעית בהן 3 פעמים ברציפות")
        if not hard_words_df.empty:
            if st.button("🚀 תרגול מילים קשות (ללא השפעה על הגיליון)"):
                st.session_state.page = "hard_practice"
                st.session_state.practice_list = hard_words_df.index.tolist()
                st.rerun()
            st.dataframe(hard_words_df[['word', 'translation', 'level', 'punished']])

# --- 9. דף תרגול מילים קשות (Sandbox) ---
elif st.session_state.page == "hard_practice":
    st.title("🔥 תרגול מילים קשות (מצב בטוח)")
    if st.button("🔙 חזור לניהול"): st.session_state.page = "groups"; st.rerun()
    
    idx_list = st.session_state.get("practice_list", [])
    if not idx_list:
        st.success("אין מילים לתרגול!")
    else:
        if "hard_idx" not in st.session_state: st.session_state.hard_idx = random.choice(idx_list)
        row = st.session_state.master_df.loc[st.session_state.hard_idx]
        
        st.markdown(f"<h1 style='text-align: center;'>{row['word']}</h1>", unsafe_allow_html=True)
        if st.toggle("תשובה"):
            st.write(f"### {row['translation']}")
            if st.button("הבנתי, נקסט!"):
                del st.session_state.hard_idx
                st.rerun()

# --- 10. סטטיסטיקה ---
elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקה")
    df = st.session_state.master_df
    c1, c2 = st.columns(2)
    c1.metric("סה\"כ עונשים שחולקו", df['punished'].sum())
    c2.metric("מילים קשות", len(df[df['history'].str.endswith("L-L-L-")]))
    st.write("פעם אחרונה שנראה (מדגם):")
    st.table(df[['word', 'last_seen']].tail(5))
