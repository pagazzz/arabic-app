import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random

# הגדרות דף
st.set_page_config(page_title="Arabic Mentor", layout="wide")

# חיבור לגוגל שיטס
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_data():
    try:
        # קריאה ישירה מה-URL ששמנו ב-Secrets
        df = conn.read(ttl=0)
        return df
    except Exception as e:
        st.error(f"שגיאת תקשורת עם גוגל: {e}")
        return pd.DataFrame()

# טעינת הנתונים לזיכרון האפליקציה
if "master_df" not in st.session_state:
    data = fetch_data()
    if not data.empty:
        # ניקוי שמות עמודות (למקרה שיש רווחים מיותרים בגיליון)
        data.columns = [c.strip().lower() for c in data.columns]
        
        # וידוא עמודות חובה
        for col in ['word', 'level', 'next_review']:
            if col not in data.columns:
                st.warning(f"שים לב: העמודה '{col}' חסרה בגיליון שלך!")
                data[col] = ""
        
        # תיקון פורמטים
        data['level'] = pd.to_numeric(data['level'], errors='coerce').fillna(1).astype(int)
        data['next_review'] = pd.to_datetime(data['next_review'], errors='coerce').dt.normalize()
        
    st.session_state.master_df = data

# --- תצוגת אבחון (Debug) - תעזור לנו להבין מה קורה ---
with st.expander("🛠️ בדיקת חיבור (לחץ כאן אם אין מילים)"):
    df_debug = st.session_state.master_df
    st.write(f"סטטוס מאגר: {len(df_debug)} שורות נמצאו.")
    if not df_debug.empty:
        st.write("שמות העמודות שגוגל שלחה:", list(df_debug.columns))
        st.write("תצוגה מקדימה של הנתונים:", df_debug.head(3))

# --- לוגיקת תרגול ---
st.title("🎯 תרגול ערבית")

df = st.session_state.master_df
today = pd.Timestamp.now().normalize()

if df.empty:
    st.warning("הגיליון חזר ריק. וודא שיש בו מילים ושמות העמודות נכונים.")
else:
    # סינון: כל מה שרמה פחות מ-8 (מתעלמים מתאריכים כרגע כדי שזה יעבוד לך)
    due = df[df['level'] < 8]
    
    if due.empty:
        st.success("אין מילים לתרגול (כולן ברמה 8).")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due.index:
            st.session_state.current_idx = random.choice(due.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        
        st.info(f"### {row['word']}")
        
        if st.toggle("חשוף תרגום"):
            st.success(f"### {row.get('translation', 'חסר תרגום')}")
            
            c1, c2 = st.columns(2)
            if c1.button("✅ ידעתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] += 1
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                del st.session_state.current_idx
                st.rerun()
            if c2.button("❌ לא ידעתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = 1
                del st.session_state.current_idx
                st.rerun()

# כפתור שמירה בסיידבר
if st.sidebar.button("💾 שמור שינויים לענן"):
    conn.update(data=st.session_state.master_df)
    st.sidebar.success("נשמר!")
