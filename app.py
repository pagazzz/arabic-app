import streamlit as st
import pandas as pd
import datetime
import os
import random
import plotly.express as px

# --- הגדרות סנכרון ענן ---
# הקישור הישיר לייצוא CSV מהגיליון שלך
SHEET_ID = "1Nm1YozZqkQ7iy11ivmC-ukARGXJWy_bzpeXQIUMxMbg"
CLOUD_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
LOCAL_FILE = "vocabulary.csv"

def load_data():
    # ניסיון טעינה מהענן
    try:
        df = pd.read_csv(CLOUD_URL)
        df.to_csv(LOCAL_FILE, index=False) # גיבוי מקומי
        st.toast("סונכרן בהצלחה מהענן! ☁️")
    except:
        # אם אין אינטרנט, טען מהמחשב
        if os.path.exists(LOCAL_FILE):
            df = pd.read_csv(LOCAL_FILE)
            st.warning("עובד במצב אופליין (גיבוי מקומי)")
        else:
            return pd.DataFrame(columns=["word", "translation", "level", "next_review", "last_seen", "punished", "example"])
    
    # וידוא עמודות ותקינות נתונים
    for col in ["level", "next_review", "last_seen", "punished", "example"]:
        if col not in df.columns: df[col] = ""
    df['level'] = df['level'].apply(lambda x: int(x) if str(x).isdigit() else x)
    df['punished'] = df['punished'].fillna(False)
    return df

def save_data(df):
    # שומר מקומית (בשביל עדכון גוגל שיטס אוטומטי מלא נדרשת הגדרה מורכבת יותר, 
    # כרגע זה מגבה הכל ב-CSV המקומי שלך)
    df.to_csv(LOCAL_FILE, index=False)

if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'page' not in st.session_state:
    st.session_state.page = "home"

data = st.session_state.data

# --- CSS מעוצב ---
st.markdown("""
    <style>
    .main-card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; }
    .arabic-font { font-size: 52px !important; color: #2c3e50; font-family: 'Arial'; }
    .example-text { color: #666; font-style: italic; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 10px; }
    .stButton>button:active { transform: scale(0.92); box-shadow: 0 0 15px #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

# --- לוגיקת דפים ---
def move_page(p):
    st.session_state.page = p
    st.rerun()

if st.session_state.page == "home":
    st.title("🛡️ המנטור האישי שלך")
    
    # חישוב מילים להיום
    today = str(datetime.date.today())
    due_words = data[(data['next_review'] <= today) & (data['level'] != "FINAL")].copy()
    
    if 'current_queue' not in st.session_state or st.session_state.get('reset_queue'):
        st.session_state.current_queue = due_words.sample(frac=1).reset_index()
        st.session_state.reset_queue = False

    queue = st.session_state.current_queue

    if not queue.empty:
        curr = queue.iloc[0]
        idx = curr['index']
        
        # כיוון תרגום
        if f"f_{idx}" not in st.session_state: st.session_state[f"f_{idx}"] = random.choice([True, False])
        flipped = st.session_state[f"f_{idx}"]
        
        # תצוגת כרטיס
        st.markdown(f'<div class="main-card"><p class="{"arabic-font" if flipped else ""}" style="font-size: 30px;">{curr["word"] if flipped else curr["translation"]}</p></div>', unsafe_allow_html=True)
        
        if st.button("👁️ חשוף תשובה"):
            st.success(curr['translation'] if flipped else curr['word'])
            if str(curr['example']) != 'nan' and curr['example'] != "":
                st.markdown(f'<div class="example-text">💡 {curr["example"]}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button("✅ צדקתי"):
            lvl = data.at[idx, 'level']
            data.at[idx, 'level'] = (lvl + 1) if isinstance(lvl, int) and lvl < 6 else "FINAL"
            data.at[idx, 'next_review'] = str(datetime.date.today() + datetime.timedelta(days=2))
            save_data(data); st.session_state.current_queue = queue.iloc[1:]; st.rerun()
        if c2.button("❌ טעיתי"):
            data.at[idx, 'next_review'] = str(datetime.date.today() + datetime.timedelta(days=1))
            save_data(data); st.session_state.current_queue = queue.iloc[1:]; st.rerun()
    else:
        st.info("אין מילים לתרגול כרגע. זמן מצוין להוסיף חדשות!")

    st.write("---")
    with st.expander("➕ הוספת מילה ומשפט"):
        w = st.text_input("ערבית")
        t = st.text_input("עברית")
        ex = st.text_input("משפט לדוגמה")
        if st.button("שמור לגיבוי"):
            new = {"word": w, "translation": t, "level": 1, "next_review": str(datetime.date.today()), "example": ex, "punished": False, "last_seen": str(datetime.date.today())}
            data = pd.concat([data, pd.DataFrame([new])], ignore_index=True)
            save_data(data); st.rerun()

    c_nav1, c_nav2 = st.columns(2)
    if c_nav1.button("📂 ניהול"): move_page("manager")
    if c_nav2.button("📊 ביצועים"): move_page("stats")

elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקות")
    if st.button("⬅️"): move_page("home")
    fig = px.pie(data['level'].value_counts().reset_index(), values='count', names='level', hole=.4)
    st.plotly_chart(fig)

elif st.session_state.page == "manager":
    st.title("📂 ניהול מילים")
    if st.button("⬅️"): move_page("home")
    st.dataframe(data[['word', 'translation', 'level', 'example']])