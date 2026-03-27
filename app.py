import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random

# --- הגדרות מערכת ---
st.set_page_config(page_title="Arabic Pro", layout="wide", initial_sidebar_state="collapsed")

# עיצוב נקי ומקצועי
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #f0f2f6; border: 1px solid #d1d5db; }
    .stButton>button:hover { border-color: #3b82f6; color: #3b82f6; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data():
    try:
        df = conn.read(ttl=0)
        # השלמת עמודות חסרות
        for col in ['word', 'translation', 'level', 'category', 'next_review', 'history']:
            if col not in df.columns: df[col] = ""
        
        df['level'] = pd.to_numeric(df['level']).fillna(1).astype(int)
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').dt.normalize()
        return df
    except:
        return pd.DataFrame(columns=['word', 'translation', 'level', 'category', 'next_review', 'history'])

if "df" not in st.session_state:
    st.session_state.df = fetch_data()

def sync():
    save_df = st.session_state.df.copy()
    save_df['next_review'] = save_df['next_review'].dt.strftime('%Y-%m-%d')
    conn.update(data=save_df)
    st.toast("✅ נשמר בענן!")

# --- תפריט ניווט ---
page = st.sidebar.radio("תפריט", ["🎯 תרגול", "📂 ניהול מאגר", "📊 ביצועים"])
if st.sidebar.button("💾 שמירה סופית לענן"): sync()

# --- דף תרגול ---
if page == "🎯 תרגול":
    st.title("🎯 תרגול יומי")
# תצוגת בדיקה זמנית - תראה לנו מה האפליקציה "רואה" בגיליון
    st.write(f"סה\"כ מילים בגיליון: {len(df)}")
    if not df.empty:
        st.write("דוגמה למילה ראשונה ורמתה:", df.iloc[0][['word', 'level', 'next_review']])
    
    # סינון אגרסיבי - מציג הכל חוץ מרמה 8
    due = df[df['level'] < 8]
    if due.empty:
        st.success("כל המילים מעודכנות! אין מה לתרגל כרגע.")
        if st.button("תרגל מילים מרמה 1 בכל זאת"):
            st.session_state.temp_due = df[df['level'] == 1]
            st.rerun()
    else:
        if "idx" not in st.session_state or st.session_state.idx not in due.index:
            st.session_state.idx = random.choice(due.index.tolist())
        
        item = df.loc[st.session_state.idx]
        
        with st.container():
            st.write(f"**קבוצה:** {item['category']} | **רמה:** {item['level']}")
            st.markdown(f"<h1 style='text-align: center; padding: 50px; background: #f9fafb; border-radius: 15px;'>{item['word']}</h1>", unsafe_allow_html=True)
            
            if st.checkbox("👁️ הצג תרגום", key="show"):
                st.markdown(f"<h2 style='text-align: center; color: #2563eb;'>{item['translation']}</h2>", unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("✅ ידעתי"):
                    st.session_state.df.at[st.session_state.idx, 'history'] += "W"
                    new_lvl = min(8, item['level'] + 1)
                    st.session_state.df.at[st.session_state.idx, 'level'] = new_lvl
                    st.session_state.df.at[st.session_state.idx, 'next_review'] = today + pd.Timedelta(days=new_lvl)
                    del st.session_state.idx
                    st.rerun()
                if c2.button("❌ לא ידעתי"):
                    st.session_state.df.at[st.session_state.idx, 'history'] += "L"
                    st.session_state.df.at[st.session_state.idx, 'level'] = 1
                    st.session_state.df.at[st.session_state.idx, 'next_review'] = today
                    del st.session_state.idx
                    st.rerun()

# --- דף ניהול מאגר ---
elif page == "📂 ניהול מאגר":
    st.title("📂 ניהול המילים")
    
    # כפתורי אריח לסינון רמות
    st.write("בחר רמה להצגה:")
    lvl_cols = st.columns(8)
    for i in range(1, 9):
        if lvl_cols[i-1].button(f"L-{i}"):
            st.session_state.manage_lvl = i
            
    selected_lvl = st.session_state.get("manage_lvl", 1)
    
    # טבלת עריכה ישירה
    subset = st.session_state.df[st.session_state.df['level'] == selected_lvl]
    st.write(f"עורך רמה **{selected_lvl}** (לחץ פעמיים על תא לשינוי):")
    
    edited_df = st.data_editor(subset[['word', 'translation', 'category', 'level']], 
                               use_container_width=True, num_rows="dynamic")
    
    if st.button("אישור שינויים בטבלה"):
        st.session_state.df.update(edited_df)
        st.success("השינויים נשמרו בזיכרון. אל תשכח ללחוץ על 'שמור לענן' בסוף.")

# --- דף סטטיסטיקה ---
elif page == "📊 ביצועים":
    st.title("📊 מצב המאגר")
    df = st.session_state.df
    counts = df['level'].value_counts().reindex(range(1, 9), fill_value=0)
    st.bar_chart(counts)
    st.metric("סה\"כ מילים במאגר", len(df))
