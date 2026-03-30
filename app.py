import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import random
import plotly.express as px

# --- 1. הגדרות דף ועיצוב ---
st.set_page_config(page_title="Arabic Mentor Ultra", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { border-radius: 8px; height: 3em; font-weight: bold; width: 100%; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1 { color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. חיבור לנתונים ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def fetch_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        
        # וידוא עמודות קריטיות (כולל החדשות)
        required_cols = {
            'word': "", 'translation': "", 'level': 1, 
            'next_review': pd.Timestamp.now().strftime('%Y-%m-%d'),
            'category': "כללי", 'history': "", 'date_added': pd.Timestamp.now().strftime('%Y-%m-%d')
        }
        for col, default in required_cols.items():
            if col not in df.columns:
                df[col] = default
        
        # ניקוי תאריכים ופורמטים
        df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce').dt.normalize()
        df['date_added'] = pd.to_datetime(df['date_added'], errors='coerce').dt.normalize()
        df['level'] = pd.to_numeric(df['level'], errors='coerce').fillna(1).astype(int)
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת הנתונים: {e}")
        return pd.DataFrame()

# --- 3. ניהול Session State ---
if "master_df" not in st.session_state:
    st.session_state.master_df = fetch_data()

# אתחול משתנים אם הם לא קיימים
defaults = {
    "page": "home", "daily_correct": 0, "daily_wrong": 0, 
    "total_session_correct": 0, "list_view": "today",
    "selected_level": None, "selected_group": None
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

df = st.session_state.master_df
level_names = {1:"I", 2:"II", 3:"III", 4:"IV", 5:"V", 6:"VI", 7:"VII", 8:"FINAL"}

# --- 4. פונקציות עזר ---
def save_to_cloud():
    df_to_save = st.session_state.master_df.copy()
    df_to_save['next_review'] = df_to_save['next_review'].dt.strftime('%Y-%m-%d')
    df_to_save['date_added'] = df_to_save['date_added'].dt.strftime('%Y-%m-%d')
    conn.update(data=df_to_save)
    st.cache_data.clear()
    st.toast("✅ הנתונים נשמרו ב-Google Sheets!")

motivational_quotes = [
    "כל הכבוד! אפילו המילון התרשם.", "עוד קצת ואתה מחליף את גוגל טרנסלייט.", 
    "המוח שלך כרגע: 🧠🔥", "וואו, אתה בטח אוכל חומוס לארוחת בוקר עם יכולות כאלה.",
    "יפה! הערבית שלך יותר טובה מהעברית שלי.", "10/10! אפילו אמא שלך הייתה גאה.",
    "תמשיך ככה ותוכל להזמין פלאפל בלי טעויות.", "אתה מכונה! מקווה ששימנת את הגלגלים.",
    "חביבי, אתה אש!", "מלך העולם!"
]

# --- 5. Sidebar ---
with st.sidebar:
    st.title("Arabic Mentor 🧠")
    if st.button("🏠 דף הבית"): st.session_state.page = "home"
    if st.button("🗂️ ניהול רשימות"): st.session_state.page = "groups"
    if st.button("📊 סטטיסטיקה"): st.session_state.page = "stats"
    st.divider()
    st.write(f"הצלחות היום: **{st.session_state.daily_correct}**")
    st.write(f"טעויות היום: **{st.session_state.daily_wrong}**")
    if st.button("💾 שמירה לענן", type="primary"):
        save_to_cloud()

# --- 6. דף הבית: תרגול והוספת מילים ---
if st.session_state.page == "home":
    st.title("🏠 תרגול יומי")
    
    # הוספת מילה חדשה
    with st.expander("➕ הוספת מילה חדשה למערכת"):
        with st.form("add_word_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_word = c1.text_input("מילה בערבית")
            new_trans = c2.text_input("תרגום לעברית")
            new_cat = st.text_input("קבוצה", value="כללי")
            if st.form_submit_button("הוסף לטבלה"):
                new_row = pd.DataFrame([{
                    'word': new_word, 'translation': new_trans, 'level': 1,
                    'category': new_cat, 'next_review': pd.Timestamp.now().normalize(),
                    'history': "", 'date_added': pd.Timestamp.now().normalize()
                }])
                st.session_state.master_df = pd.concat([st.session_state.master_df, new_row], ignore_index=True)
                st.success(f"המילה '{new_word}' נוספה!")

    # מד הצלחה יומי (ויזואלי)
    total_daily = st.session_state.daily_correct + st.session_state.daily_wrong
    if total_daily > 0:
        c_pct = (st.session_state.daily_correct / total_daily) * 100
        w_pct = 100 - c_pct
        st.markdown(f"""
            <div style="width:100%; height:15px; background:#eee; border-radius:10px; display:flex; overflow:hidden; margin-bottom:20px;">
                <div style="width:{c_pct}%; background:#00dc82;"></div>
                <div style="width:{w_pct}%; background:#ff4b4b;"></div>
            </div>
        """, unsafe_allow_html=True)

    # לוגיקת תרגול
    today = pd.Timestamp.now().normalize()
    due_words = st.session_state.master_df[(st.session_state.master_df['next_review'] <= today) & (st.session_state.master_df['level'] < 8)]
    
    if due_words.empty:
        st.balloons()
        st.success("סיימת הכל להיום! 🎉")
    else:
        if "current_idx" not in st.session_state or st.session_state.current_idx not in due_words.index:
            st.session_state.current_idx = random.choice(due_words.index.tolist())
        
        row = st.session_state.master_df.loc[st.session_state.current_idx]
        
        # הצגת סיכוי הצלחה (צבעוני)
        chance = min(95, row['level'] * 12 + random.randint(-5, 5))
        st.write(f"סיכוי הצלחה מוערך: **{chance}%**")
        st.progress(chance/100)

        mode = st.radio("כיוון:", ["ערבית ⬅️ עברית", "עברית ⬅️ ערבית"], horizontal=True)
        q = row['word'] if "ערבית" in mode else row['translation']
        a = row['translation'] if "ערבית" in mode else row['word']
        
        st.markdown(f"<h1 style='text-align: center; font-size: 80px; padding: 30px;'>{q}</h1>", unsafe_allow_html=True)
        
        # תיקון באג ה-toggle: מפתח ייחודי לכל מילה
        if st.toggle("חשוף תשובה", key=f"ans_{st.session_state.current_idx}"):
            st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>{a}</h2>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button("✅ הצלחתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "W-"
                new_lvl = min(8, row['level'] + 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = new_lvl
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=new_lvl)
                st.session_state.daily_correct += 1
                st.session_state.total_session_correct += 1
                if st.session_state.total_session_correct % 10 == 0:
                    st.toast(random.choice(motivational_quotes))
                del st.session_state.current_idx
                st.rerun()
            if b2.button("❌ טעיתי"):
                st.session_state.master_df.at[st.session_state.current_idx, 'history'] += "L-"
                st.session_state.master_df.at[st.session_state.current_idx, 'level'] = max(1, row['level'] - 1)
                st.session_state.master_df.at[st.session_state.current_idx, 'next_review'] = today + pd.Timedelta(days=1)
                st.session_state.daily_wrong += 1
                del st.session_state.current_idx
                st.rerun()

# --- 7. דף קבוצות וניהול רשימות ---
elif st.session_state.page == "groups":
    st.title("🗂️ ניהול רשימות")
    
    # סינון רמות
    st.subheader("סנן לפי רמה:")
    cols = st.columns(8)
    for i in range(1, 9):
        if cols[i-1].button(f"Lev {level_names[i]}", use_container_width=True):
            st.session_state.list_view = "level"
            st.session_state.selected_level = i

    # סינון קבוצות
    st.subheader("סנן לפי קבוצה:")
    cats = sorted(st.session_state.master_df['category'].unique())
    cat_cols = st.columns(4)
    for idx, cat in enumerate(cats):
        if cat_cols[idx % 4].button(f"📁 {cat}", use_container_width=True):
            st.session_state.list_view = "category"
            st.session_state.selected_group = cat

    if st.button("🔍 הצג הכל"): st.session_state.list_view = "all"

    st.divider()
    
    # הצגת הטבלה
    view = st.session_state.list_view
    target_df = st.session_state.master_df
    if view == "level": target_df = target_df[target_df['level'] == st.session_state.selected_level]
    elif view == "category": target_df = target_df[target_df['category'] == st.session_state.selected_group]
    
    st.dataframe(target_df[['word', 'translation', 'level', 'category', 'next_review']], use_container_width=True)

# --- 8. דף סטטיסטיקה ---
elif st.session_state.page == "stats":
    st.title("📊 סטטיסטיקה")
    df_s = st.session_state.master_df
    
    c1, c2, c3 = st.columns(3)
    c1.metric("סה\"כ מילים", len(df_s))
    c2.metric("רמת FINAL (סיימו)", len(df_s[df_s['level'] == 8]))
    
    thirty_days = pd.Timestamp.now().normalize() - pd.Timedelta(days=30)
    new_words = len(df_s[df_s['date_added'] > thirty_days])
    c3.metric("חדשות (חודש)", new_words)
    
    st.divider()
    
    # גרף התפלגות
    st.subheader("התפלגות רמות")
    lvl_counts = df_s['level'].value_counts().sort_index().reset_index()
    lvl_counts.columns = ['Level', 'Count']
    lvl_counts['Name'] = lvl_counts['Level'].map(level_names)
    fig = px.bar(lvl_counts, x='Name', y='Count', color='Count', color_continuous_scale='Greens', text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

    # טבלת היסטוריה אחרונה
    st.subheader("ביצועים אחרונים")
    hist_df = df_s[df_s['history'] != ""].tail(5)
    if not hist_df.empty:
        st.table(hist_df[['word', 'translation', 'history']])