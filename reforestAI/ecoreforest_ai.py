# ecoreforest_ai.py
# Final decorated version: registration shows code, verification updates DB reliably, login works, and Home page is beautifully styled.

import streamlit as st
import sqlite3
import random
import pandas as pd
from datetime import datetime, timedelta

# ---------------------------
# Compatibility: safe rerun
# ---------------------------
if not hasattr(st, "rerun"):
    try:
        st.rerun = st.experimental_rerun
    except Exception:
        def _noop(): pass
        st.rerun = _noop

# ---------------------------
# Database initialization & migration
# ---------------------------
DB_PATH = "users.db"

def get_conn_cursor():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def init_db():
    conn, c = get_conn_cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            verified INTEGER DEFAULT 0,
            verification_code TEXT,
            free_uses INTEGER DEFAULT 2
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            plan TEXT,
            start_date TEXT,
            end_date TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    conn.commit()

    c.execute("PRAGMA table_info(users)")
    existing = [r["name"] for r in c.fetchall()]
    if "free_uses" not in existing:
        try:
            c.execute("ALTER TABLE users ADD COLUMN free_uses INTEGER DEFAULT 2")
            conn.commit()
        except:
            pass

    c.execute("PRAGMA table_info(subscriptions)")
    s_existing = [r["name"] for r in c.fetchall()]
    for col_def in [("end_date","TEXT"), ("active","INTEGER DEFAULT 1")]:
        if col_def[0] not in s_existing:
            try:
                c.execute(f"ALTER TABLE subscriptions ADD COLUMN {col_def[0]} {col_def[1]}")
                conn.commit()
            except:
                pass

    return conn, c

conn, c = init_db()

# ---------------------------
# DB helper functions
# ---------------------------
def normalize_email(email: str) -> str:
    return email.strip().lower() if email else ""

def add_user(email, password, code):
    email = normalize_email(email)
    c.execute("SELECT 1 FROM users WHERE email=?", (email,))
    if c.fetchone():
        return False
    c.execute("INSERT INTO users (email, password, verification_code, verified, free_uses) VALUES (?, ?, ?, 0, 2)",
              (email, password, str(code)))
    conn.commit()
    return True

def get_user(email):
    email = normalize_email(email)
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    return c.fetchone()

def verify_user(email, code):
    email = normalize_email(email)
    row = get_user(email)
    if not row: 
        return False
    stored = row["verification_code"]
    if stored is None:
        return False
    if str(stored) == str(code):
        c.execute("UPDATE users SET verified=1 WHERE email=?", (email,))
        conn.commit()
        return True
    return False

def set_password(email, new_password):
    email = normalize_email(email)
    c.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
    conn.commit()

def login_user(email, password):
    email = normalize_email(email)
    c.execute("SELECT * FROM users WHERE email=? AND password=? AND verified=1", (email, password))
    return c.fetchone()

def decrement_free_uses(email):
    email = normalize_email(email)
    row = get_user(email)
    if not row:
        return 0
    current = int(row["free_uses"] or 0)
    newv = max(0, current - 1)
    c.execute("UPDATE users SET free_uses=? WHERE email=?", (newv, email))
    conn.commit()
    return newv

def get_free_uses(email):
    email = normalize_email(email)
    row = get_user(email)
    return int(row["free_uses"]) if row else 0

def create_subscription(email, plan):
    email = normalize_email(email)
    durations = {"Daily":1,"Weekly":7,"Monthly":30,"Yearly":365}
    days = durations.get(plan, 0)
    start = datetime.now()
    end = start + timedelta(days=days)
    c.execute("UPDATE subscriptions SET active=0 WHERE email=? AND active=1", (email,))
    c.execute("INSERT INTO subscriptions (email, plan, start_date, end_date, active) VALUES (?, ?, ?, ?, 1)",
              (email, plan, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    conn.commit()

def get_active_subscription(email):
    email = normalize_email(email)
    c.execute("SELECT * FROM subscriptions WHERE email=? AND active=1 ORDER BY id DESC LIMIT 1", (email,))
    row = c.fetchone()
    if not row: return None
    try:
        enddt = datetime.strptime(row["end_date"], "%Y-%m-%d")
        if datetime.now().date() <= enddt.date():
            return row
    except:
        pass
    c.execute("UPDATE subscriptions SET active=0 WHERE id=?", (row["id"],))
    conn.commit()
    return None

# ---------------------------
# Styling & config
# ---------------------------
st.set_page_config(page_title="Ecoreforest AI", layout="wide")
st.markdown("""
<style>
.main-title{background:linear-gradient(to right,#00b09b,#96c93d);color:white;
text-align:center;padding:14px;border-radius:10px;font-size:26px;font-weight:600;}
.section-divider{border-top:2px solid #96c93d;margin:12px 0;}
.species-card{background:#f6fff8;border-left:5px solid #00b09b;padding:10px 14px;border-radius:10px;margin-bottom:8px;}
.small-muted{color:#666;font-size:13px;}
.home-hero{background:linear-gradient(to right,#a8e063,#56ab2f);
color:white;text-align:center;padding:50px 10px;border-radius:15px;margin-bottom:20px;}
.home-hero h1{font-size:42px;margin-bottom:10px;}
.home-hero p{font-size:18px;}
.info-card{background:white;border-radius:15px;padding:20px;margin:10px 0;
box-shadow:0 3px 10px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Sidebar
# ---------------------------
if "menu" not in st.session_state:
    st.session_state.menu = "Home"

menu = st.sidebar.radio("📋 Menu", ["Home", "Register/Login", "Subscription Plan", "AI Tool"], index=["Home","Register/Login","Subscription Plan","AI Tool"].index(st.session_state.menu) if st.session_state.menu in ["Home","Register/Login","Subscription Plan","AI Tool"] else 0)
st.session_state.menu = menu

st.sidebar.markdown("**Ecoreforest AI** 🌿 — Smart Reforestation")
if "user" in st.session_state:
    st.sidebar.markdown(f"Signed in as: **{st.session_state.user}**")
    if st.sidebar.button("Logout"):
        del st.session_state["user"]
        st.experimental_rerun()

# ---------------------------
# HOME (Decorated)
# ---------------------------
if menu == "Home":
    st.markdown("""
    <div class="home-hero">
        <h1>🌳 Welcome to Ecoreforest AI</h1>
        <p>Empowering smarter reforestation decisions with artificial intelligence.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='info-card'><h3>🌱 AI Recommendations</h3><p>Get intelligent, data-driven native species suggestions tailored to your soil and climate conditions.</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='info-card'><h3>💧 Sustainable Planning</h3><p>Design reforestation projects that maximize biodiversity and water retention.</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='info-card'><h3>📊 Easy Insights</h3><p>Download and use results instantly for reports or field planning.</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.info("👤 Register or Login to start your free AI-based reforestation planning (2 free runs included).")

# ---------------------------
# REGISTER / LOGIN / VERIFY / FORGOT
# ---------------------------
elif menu == "Register/Login":
    st.header("👤 Account")

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = None
    if "last_ver_code" not in st.session_state:
        st.session_state.last_ver_code = None
    if "prefill_email" not in st.session_state:
        st.session_state.prefill_email = ""

    cols = st.columns(3)
    if cols[0].button("📝 Register"): st.session_state.auth_mode = "register"
    if cols[1].button("🔑 Login"): st.session_state.auth_mode = "login"
    if cols[2].button("❓ Forgot"): st.session_state.auth_mode = "forgot"

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    # --- Register UI ---
    if st.session_state.auth_mode == "register":
        st.subheader("Create Account")
        r_email = st.text_input("Email", key="reg_email")
        r_pass = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register Account"):
            if not r_email or not r_pass:
                st.warning("Enter email and password.")
            else:
                normalized = normalize_email(r_email)
                code = random.randint(100000, 999999)
                created = add_user(normalized, r_pass, code)
                if created:
                    st.session_state.last_ver_code = str(code)
                    st.session_state.prefill_email = normalized
                    st.success("Account created. Verification code shown below (simulation).")
                    st.info(f"🔐 Verification code: **{code}**")
                    verify_email = st.text_input("Verify Email", value=normalized, key="post_reg_verify_email")
                    verify_code = st.text_input("Verification Code", value=str(code), key="post_reg_verify_code")
                    if st.button("Verify Now"):
                        ok = verify_user(verify_email, verify_code)
                        if ok:
                            st.success("Email verified. You can now log in.")
                            st.session_state.auth_mode = "login"
                        else:
                            st.error("Verification failed. Check code and email.")
                else:
                    st.error("Email already registered. Try login or forgot password.")

    # --- Login UI ---
    elif st.session_state.auth_mode == "login":
        st.subheader("Login")
        l_email = st.text_input("Email", value=st.session_state.get("prefill_email",""), key="login_email")
        l_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login Now"):
            if not l_email or not l_pass:
                st.warning("Enter both email and password.")
            else:
                user = login_user(l_email, l_pass)
                if user:
                    st.session_state.user = normalize_email(l_email)
                    if get_active_subscription(st.session_state.user):
                        st.session_state.menu = "AI Tool"
                    else:
                        st.session_state.menu = "Subscription Plan"
                    st.success(f"Welcome back, {st.session_state.user}!")
                    st.rerun()
                else:
                    row = get_user(l_email)
                    if row and row["verified"] == 0:
                        st.error("Account exists but is not verified. Use the Verify form below.")
                    else:
                        st.error("Invalid credentials. Check email/password or register first.")

        st.markdown("---")
        with st.expander("Verify account (have a code?)"):
            v_email = st.text_input("Verification Email", value=st.session_state.get("prefill_email",""), key="verify_email_inline")
            v_code = st.text_input("Verification Code", key="verify_code_inline")
            if st.button("Verify Code"):
                if not v_email or not v_code:
                    st.warning("Enter both email and code.")
                else:
                    ok = verify_user(v_email, v_code)
                    if ok:
                        st.success("Verified! Now login.")
                        st.session_state.prefill_email = normalize_email(v_email)
                        st.session_state.auth_mode = "login"
                    else:
                        st.error("Verification failed. Check email and code.")

    # --- Forgot password ---
    elif st.session_state.auth_mode == "forgot":
        st.subheader("Reset Password (simulation)")
        f_email = st.text_input("Registered Email", key="forgot_email")
        new_password = st.text_input("New Password", type="password", key="forgot_newpass")
        if st.button("Reset Password"):
            if not f_email or not new_password:
                st.warning("Enter email and a new password.")
            else:
                if get_user(f_email):
                    set_password(f_email, new_password)
                    st.success("Password updated. Please login.")
                    st.session_state.auth_mode = "login"
                else:
                    st.error("Email not found. Please register.")

# ---------------------------
# Subscription Page
# ---------------------------
elif menu == "Subscription Plan":
    st.header("💳 Subscription Plans (USD)")
    if "user" not in st.session_state:
        st.warning("Please login first to subscribe.")
    else:
        plans = {"Daily":1, "Weekly":5, "Monthly":15, "Yearly":100}
        cols = st.columns(len(plans))
        for i,(p,price) in enumerate(plans.items()):
            with cols[i]:
                st.markdown(f"**{p}**\n\nPrice: **${price}**")
                if st.button(f"Activate {p}", key=f"buy_{p}"):
                    create_subscription(st.session_state.user, p)
                    st.success(f"Subscribed to {p} (${price}).")
                    st.rerun()

        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        active = get_active_subscription(st.session_state.user)
        if active:
            st.info(f"Active subscription: **{active['plan']}** (ends {active['end_date']})")
        else:
            st.warning("No active subscription found.")

# ---------------------------
# AI Tool
# ---------------------------
elif menu == "AI Tool":
    st.markdown("<div class='main-title'>🌱 Ecoreforest AI Recommender</div>", unsafe_allow_html=True)
    if "user" not in st.session_state:
        st.warning("Please login to use the AI tool.")
    else:
        active = get_active_subscription(st.session_state.user)
        free = get_free_uses(st.session_state.user)
        if (not active) and free <= 0:
            st.error("Free uses exhausted. Please subscribe to continue.")
        else:
            st.subheader("Provide Site & Project Details (10 inputs)")
            with st.expander("Site & Soil", expanded=True):
                soil_type = st.selectbox("Soil Type", ["Sandy","Loamy","Clay","Lateritic"])
                soil_ph = st.selectbox("Soil pH", ["Acidic (<6)","Neutral (6–7.5)","Alkaline (>7.5)"])
                drainage = st.selectbox("Drainage Quality", ["Poor","Moderate","Good"])
                soil_depth = st.selectbox("Soil Depth", ["Shallow","Medium","Deep"])
            with st.expander("Climate", expanded=True):
                rainfall = st.number_input("Annual Rainfall (mm)", 200, 4000, 1200)
                temperature = st.number_input("Average Temp (°C)", 5, 40, 25)
                altitude = st.number_input("Altitude (m)", 0, 4000, 500)
                dry_season = st.slider("Dry Season (months)", 0, 12, 4)
            with st.expander("Project", expanded=True):
                goal = st.selectbox("Main Objective", ["Timber","Erosion Control","Carbon Sequestration","Biodiversity","Agroforestry"])
                maintenance = st.selectbox("Maintenance Level", ["Low","Medium","High"])
                region = st.selectbox("Region / Biome", ["Tropical Rainforest","Savanna","Coastal Forest","Dry Woodland","Highland Forest"])

            if st.button("Generate Recommendations"):
                if not active:
                    new_free = decrement_free_uses(st.session_state.user)
                    st.info(f"Free uses remaining: {new_free}")

                recs = {
                    "Tropical Rainforest": ["Milicia excelsa","Khaya anthotheca","Terminalia superba","Albizia ferruginea","Nauclea diderrichii","Entandrophragma cylindricum","Afzelia africana","Ceiba pentandra","Triplochiton scleroxylon","Piptadeniastrum africanum"],
                    "Savanna": ["Acacia senegal","Balanites aegyptiaca","Combretum molle","Terminalia avicennioides","Anogeissus leiocarpa","Faidherbia albida","Adansonia digitata","Prosopis africana","Daniellia oliveri","Vitellaria paradoxa"],
                    "Coastal Forest": ["Rhizophora mucronata","Avicennia marina","Ceriops tagal","Barringtonia racemosa","Heritiera littoralis","Pandanus tectorius","Bruguiera gymnorrhiza","Thespesia populnea","Hibiscus tiliaceus","Casuarina equisetifolia"],
                    "Dry Woodland": ["Combretum collinum","Julbernardia globiflora","Pterocarpus angolensis","Brachystegia spiciformis","Albizia harveyi","Terminalia sericea","Xeroderris stuhlmannii","Afzelia quanzensis","Acacia tortilis","Dichrostachys cinerea"],
                    "Highland Forest": ["Podocarpus falcatus","Juniperus procera","Hagenia abyssinica","Olea europaea subsp. cuspidata","Croton macrostachyus","Polyscias fulva","Prunus africana","Schefflera abyssinica","Cassipourea malosana","Ilex mitis"]
                }

                species_list = recs.get(region, [])[:10]
                results = []
                st.subheader(f"🌳 Top 10 Native Species for {region}")
                for s in species_list:
                    reason = f"Matches {soil_type.lower()} soils; tolerates ~{rainfall}mm rainfall; useful for {goal.lower()}."
                    benefit = random.choice(["Excellent carbon storage","Supports biodiversity","Good for erosion control","Fast-growing timber"])
                    st.markdown(f"<div class='species-card'>🌿 <b>{s}</b><br>💡 {reason}<br>🌎 {benefit}</div>", unsafe_allow_html=True)
                    results.append({"Species": s, "Reason": reason, "Benefit": benefit})
                df = pd.DataFrame(results)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Recommendations (CSV)", csv, "ecoreforest_recommendations.csv", "text/csv")
