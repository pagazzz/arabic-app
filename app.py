import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random

# --- הגדרות מערכת ---
st.set_page_config(page_title="Arabic Mentor Pro", layout="wide")

# עיצוב כפתורים נקי (בלי שטויות)
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: 600; }
    div[data-testid="stExpander"] { border: none; box-shadow: 0px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור ונתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data():
    df = conn.read(ttl=0)
    # וידוא עמודות
    cols = {'word':"", 'translation':"", 'level':1, 'category':"כללי", 
            'next_review':pd.Timestamp.now().strftime('%Y-%m-%d'), 'history':""}
    for col, val in cols.items():
        if col not in df.columns: df[col] = val
    df['next_review'] = pd.to_datetime(df['next_review']).dt.normalize()
    df['level'] = pd.to_numeric(df['level']).fillna(1).astype(int)
    return df

if "df" not in st.session_state:
    st.session_state.df = fetch_data()

# פונקציית שמירה
def sync():
    save_df = st.session_state.df.copy()
    save_df['next_review'] = save_df['next_review'].dt.strftime('%Y-%m-%d')
    conn.update(data=save_df)
    st.toast("✅ נשמר בענן")

# --- תפריט צד ---
with st.sidebar:
    st.title("Arabic Pro")
    page = st.radio("ניווט:", ["🎯 תרגול", "📂 ניהול וקבוצות", "📊 סטטיסטיקה"])
    st.divider()
    if st.button("💾 שמור שינויים לענן"): sync()

# --- דף תרגול ---
if page == "🎯 תרגול":
    st.subheader("תרגול יומי")
    
    # טופס הוספה מהיר
    with st.expander("➕ הוספת מילה חדשה"):
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            w = c1.text_input("ערבית")
            t = c2.text_input("עברית")
            cat = st.text_input("קבוצה", value="כללי")
            if st.form_submit_button("הוסף"):
                new_row = pd.DataFrame([{'word':w, 'translation':t, 'level':1, 'category':cat, 
                                        'next_review':pd.Timestamp.now().normalize(), 'history':""}])
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                st.success("נוסף")

    # לוגיקת תרגול
    df = st.session_state.df
    today = pd.Timestamp.now().normalize()
    due = df[(df['next_review'] <= today) & (df['level'] < 8)]
    
    if due.empty:
        st.success("אין מילים לתרגול כרגע.")
    else:
        if "idx" not in st.session_state or st.session_state.idx not in due.index:
            st.session_state.idx = random.choice(due.index.tolist())
        
        item = df.loc[st.session_state.idx]
        st.caption(f"רמה {item['level']} | {item['category']}")
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

# --- דף ניהול וקבוצות ---
elif page == "📂 ניהול וקבוצות":
    st.subheader("ניהול מאגר המילים")
    
    # סינון רמות באריחים
    st.write("סנן לפי רמה:")
    lvl_cols = st.columns(8)
    for i in range(1, 9):
        if lvl_cols[i-1].button(str(i)): st.session_state.filter = i
    
    # טבלת עריכה ישירה
    st.write("ניתן לערוך תאים ישירות בטבלה:")
    f_val = st.session_state.get("filter", 1)
    view_df = st.session_state.df[st.session_state.df['level'] == f_val]
    
    edited_df = st.data_editor(view_df[['word', 'translation', 'category', 'level', 'history']], 
                               use_container_width=True, num_rows="dynamic")
    
    if st.button("אשר שינויי עריכה"):
        st.session_state.df.update(edited_df)
        st.success("עודכן בזיכרון האפליקציה")

# --- דף סטטיסטיקה ---
elif page == "📊 סטטיסטיקה":
    st.subheader("ביצועים")
    df = st.session_state.df
    st.bar_chart(df['level'].value_counts())
    st.write("מילים אחרונות שתרגלת:")
    st.table(df[df['history'] != ""].tail(10)[['word', 'history']])
