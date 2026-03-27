import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random

# הגדרות דף
st.set_page_config(page_title="Arabic Pro", layout="wide")

# חיבור
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data():
    try:
        # ניסיון קריאה ישיר
        df = conn.read(ttl=0)
        return df
    except Exception as e:
        st.error(f"שגיאת חיבור: {e}")
        # אם נכשל, ננסה להחזיר מבנה ריק כדי שהאפליקציה לא תתרסק
        return pd.DataFrame(columns=['word', 'translation', 'level', 'category', 'next_review', 'history'])

# אתחול נתונים ב-Session State
if "df" not in st.session_state:
    raw_df = fetch_data()
    # וידוא עמודות ותיקון פורמטים
    for col in ['word', 'translation', 'history', 'category']:
        if col not in raw_df.columns: raw_df[col] = ""
    if 'level' not in raw_df.columns: raw_df['level'] = 1
    if 'next_review' not in raw_df.columns: 
        raw_df['next_review'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    raw_df['next_review'] = pd.to_datetime(raw_df['next_review']).dt.normalize()
    raw_df['level'] = pd.to_numeric(raw_df['level']).fillna(1).astype(int)
    st.session_state.df = raw_df

# --- פונקציית שמירה ---
def sync():
    try:
        save_df = st.session_state.df.copy()
        save_df['next_review'] = save_df['next_review'].dt.strftime('%Y-%m-%d')
        conn.update(data=save_df)
        st.toast("✅ נשמר בהצלחה!")
    except Exception as e:
        st.error(f"לא הצלחתי לשמור: {e}")

# --- תפריט וניווט ---
page = st.sidebar.radio("ניווט", ["🎯 תרגול", "📂 ניהול", "📊 סטטיסטיקה"])
if st.sidebar.button("💾 שמור לענן"): sync()

# --- דף תרגול ---
if page == "🎯 תרגול":
    st.title("תרגול יומי")
    df = st.session_state.df
    today = pd.Timestamp.now().normalize()
    due = df[(df['next_review'] <= today) & (df['level'] < 8)]
    
    if due.empty:
        st.success("אין מילים לתרגול להיום! הכל מעודכן.")
    else:
        if "idx" not in st.session_state or st.session_state.idx not in due.index:
            st.session_state.idx = random.choice(due.index.tolist())
        
        item = df.loc[st.session_state.idx]
        st.info(f"### {item['word']}")
        
        if st.toggle("חשוף תרגום"):
            st.success(f"### {item['translation']}")
            c1, c2 = st.columns(2)
            if c1.button("✅ הצלחתי"):
                st.session_state.df.at[st.session_state.idx, 'history'] += "W"
                lvl = min(8, item['level'] + 1)
                st.session_state.df.at[st.session_state.idx, 'level'] = lvl
                st.session_state.df.at[st.session_state.idx, 'next_review'] = today + pd.Timedelta(days=lvl)
                del st.session_state.idx
                st.rerun()
            if c2.button("❌ טעיתי"):
                st.session_state.df.at[st.session_state.idx, 'history'] += "L"
                st.session_state.df.at[st.session_state.idx, 'level'] = max(1, item['level'] - 1)
                st.session_state.df.at[st.session_state.idx, 'next_review'] = today + pd.Timedelta(days=1)
                del st.session_state.idx
                st.rerun()

# --- דף ניהול ---
elif page == "📂 ניהול":
    st.title("ניהול מילים")
    
    # כפתורי רמות
    st.write("סנן לפי רמה:")
    cols = st.columns(8)
    for i in range(1, 9):
        if cols[i-1].button(f"L{i}"): st.session_state.lvl_filter = i
    
    current_lvl = st.session_state.get("lvl_filter", 1)
    sub_df = st.session_state.df[st.session_state.df['level'] == current_lvl]
    
    st.write(f"מציג רמה {current_lvl}:")
    edited = st.data_editor(sub_df, use_container_width=True, num_rows="dynamic")
    
    if st.button("עדכן שינויים בטבלה"):
        st.session_state.df.update(edited)
        st.success("עודכן בזיכרון המקומי")

# דף סטטיסטיקה
elif page == "📊 סטטיסטיקה":
    st.title("ביצועים")
    st.bar_chart(st.session_state.df['level'].value_counts())
