import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
import plotly.express as px

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Arabic Mentor Ultra", layout="wide")
st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; height: 3em; font-weight: bold; width: 100%; }
    .stProgress > div > div > div > div { background-color: #00dc82; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def fetch_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        
        required_cols = {
            'word': "", 'translation': "", 'level': 1, 
            'next_review': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'category': "כללי", 'history': "", 'date_added': pd.Timestamp.now().strftime('%Y-%m-%d')
        }
        for col, default in required_cols.items():
            if col not in df.columns:
                df[col] = default
        
        # תיקון קריטי לשגיאת ה-history: הפיכה לטקסט ומילוי ריקים
        df['history'] = df['history'].astype(str).replace(['nan', 'None', 'NaN'], '')
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').dt.normalize()
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        return df
    except Exception as e:
        st.error(f"שגיאה: {e}")
        return pd.DataFrame()

# --- 3. Session State ---
if "master_df" not in st.session_state:
    st.session_state.master_df = fetch_data()

defaults = {
    "page": "home", "daily_correct": 0, "daily_wrong": 0, 
    "total_session_correct": 0, "list_view": "today"
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

level_names = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"FINAL"}

# --- 4. פונקציות עזר ---
def save_to_cloud():
    df_save = st.session_state.master_df.copy()
    df_save['next_review'] = df_save['next_review'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_save)
    st.cache_data.clear()
    st.toast("✅ נשמר בגיליון!")

# --- 5. Sidebar ---
with st.sidebar:
    st.title("Arabic Mentor 🧠")
    if st.button("🏠 דף הבית"): st.session_state.page = "home"
    if st.button("🗂️ ניהול רשימות"): st.session_state.page = "groups"
    if st.button("📊 סטטיסטיקה"): st.session_state.page = "stats"
    st.divider()
    if st.button("💾 שמירה לענן", type="primary"): save_to_cloud()

# --- 6. דף הבית ---
if st.session_state.page == "home":
    st.title("🏠 תרגול יומי")
    df = st.session_state.master_df
    today = pd.Timestamp.now().normalize()
    
    # סינון מילים להיום
    due_words = df[(df['next_review'] <= today) & (df['level'] < 8)]
    total_left = len(due_words)

    # הצגת מונה מילים שנשארו
    st.subheader(f"נשארו לך עוד **{total_left}** מילים להיום")

    # מד הצלחה יומי ויזואלי (ירוק-אדום)
    total_daily = st.session_state.daily_correct + st.session_state.daily_wrong
    if total_daily > 0:
        c_pct = (st.session_state.daily_correct / total_daily) * 100
        w_pct = 100 - c_pct
        st.markdown(f"""
            <div style="width:100%; height:15px; background:#eee; border-radius:10px; display:flex; overflow:hidden; margin-top:10px;">
                <div style="width:{c_pct}%; background:#00dc82;"></div>
                <div style="width:{w_pct}%; background:#ff4b4b;"></div>
            </div>
            <p style="text-align:center; font-size:0.9em;">הצלחות: {st.session_state.daily_correct} | טעויות: {st.session_state.daily_wrong}</p>
        """, unsafe_allow_html=True)

    if due_words.empty:
        st.balloons()
        st.success("אין יותר מילים לתרגול להיום! 🏆")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_words.index:
            st.session_state.current_idx = random.choice(due_words.index.tolist())
        
        row = df.loc[st.session_state.current_idx]
        
        # סיכוי הצלחה (צבעוני)
        chance = min(95, row['level'] * 12)
        color = "red" if chance < 40 else "orange" if chance < 70 else "green"
        st.markdown(f"סיכוי הצלחה מוערך: <span style='color:{color}; font-weight:bold;'>{chance}%</span>", unsafe_allow_html=True)
        st.progress(chance/100)

        st.markdown(f"<h1 style='text-align: center; font-size: 80px; padding: 40px;'>{row['word']}</h1>", unsafe_allow_html=True)
        
        if st.toggle("חשוף תשובה", key=f"ans_{st.session_state.current_idx}"):
            st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{row['translation']}</h2>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ ידעתי"):
                # עדכון היסטוריה בצורה בטוחה
                current_hist = str(st.session_state.master_df.at[st.session_state.current_idx, 'history'])
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] = current_hist + "W-"
                
                new_lvl = min(8, row['level'] + 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = new_lvl
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=new_lvl*2)
                st.session_state.daily_correct += 1
                del st.session_state.current_idx
                st.rerun()
            if c2.button("❌ טעיתי"):
                current_hist = str(st.session_state.master_df.at[st.session_state.current_idx, 'history'])
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] = current_hist + "L-"
                
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = 1
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                st.session_state.daily_wrong += 1
                del st.session_state.current_idx
                st.rerun()

# --- דפי קבוצות וסטטיסטיקה (מקוצר ליציבות) ---
elif st.session_state.page == "groups":
    st.title("🗂️ ניהול רשימות")
    st.dataframe(st.session_state.master_df[['word', 'translation', 'level', 'category']])

elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקה")
    st.metric("סה\"כ מילים", len(st.session_state.master_df))
    st.subheader("התפלגות רמות")
    lvl_dist = st.session_state.master_df['level'].value_counts().sort_index().reset_index()
    fig = px.bar(lvl_dist, x='level', y='count', color='level')
    st.plotly_chart(fig)