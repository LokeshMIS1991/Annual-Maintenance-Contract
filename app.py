import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="AMC Annual Maintenance Tracker", 
    page_icon="🛠️", 
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. GOOGLE SHEETS CONNECTION & PERSISTENCE
# -----------------------------------------------------------------------------

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

try:
    gc = get_gspread_client()
    SPREADSHEET_ID = st.secrets.get("spreadsheet_id", "12ppqL-NM7JhXbvUPZTJJQBK3Hapx_WbQ_K5Czc2VvBc")
    sh = gc.open_by_key(SPREADSHEET_ID)
except Exception as e:
    st.error(f"⚠️ Could not connect to Google Sheets. Please check permissions and secrets.toml. Error: {e}")
    st.stop()

def load_sheet_data(worksheet_name):
    try:
        ws = sh.worksheet(worksheet_name)
        records = ws.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        st.warning(f"Could not load '{worksheet_name}' tab. Returning empty table.")
        return pd.DataFrame()

def save_sheet_data(df, worksheet_name):
    try:
        ws = sh.worksheet(worksheet_name)
        ws.clear()
        clean_df = df.fillna("").astype(str)
        ws.update([clean_df.columns.values.tolist()] + clean_df.values.tolist())
    except Exception as e:
        st.error(f"❌ Failed to save data to Google Sheets ({worksheet_name}): {e}")

# Load dynamic data from Google Sheets into session state on initial run
if "users_db" not in st.session_state:
    st.session_state.users_db = load_sheet_data("Users")

if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = load_sheet_data("Jobs")

if "tech_status_db" not in st.session_state:
    st.session_state.tech_status_db = load_sheet_data("TechStatus")

# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def make_google_maps_link(address, city, pincode=""):
    query = urllib.parse.quote(f"{address}, {city} {pincode}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={query}"

def get_logo_path():
    for name in ["Company Logo.jpeg", "Company Logo.png", "Company Logo.jpg"]:
        if os.path.exists(name):
            return name
    return None

# -----------------------------------------------------------------------------
# 3. BRANDED UI STYLING
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    /* Active Tab Highlight Overrides */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #1565C0 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #1565C0 !important;
        font-weight: 700 !important;
    }

    /* Sidebar Logo Container Setup */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
    }
    
    .sidebar-logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        margin-bottom: 10px;
    }
    
    .sidebar-logo-sub {
        color: #10B981;
        font-weight: 800;
        font-size: 0.95rem;
        letter-spacing: 1.5px;
        text-align: center;
        margin-top: 6px;
        width: 100%;
    }

    /* Primary Action Buttons & Form Submit Buttons in Blue */
    .stButton > button, div[data-testid="stForm"] button {
        background-color: #1565C0 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover, div[data-testid="stForm"] button:hover {
        background-color: #0D47A1 !important;
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.3) !important;
    }

    a {
        color: #1565C0 !important;
    }

    /* General Form Container Styling */
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        border: 2px solid #1565C0;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(21, 101, 192, 0.1);
    }

    /* Compact Login Screen Form */
    .login-container div[data-testid="stForm"] {
        padding: 18px 24px !important;
        max-width: 380px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. LOGIN SCREEN
# -----------------------------------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    col_left, col_center, col_right = st.columns([1.2, 1.3, 1.2])

    with col_center:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        with st.form("login_form"):
            logo_path = get_logo_path()
            if logo_path:
                st.image(logo_path, use_container_width=True)
            else:
                st.markdown("<h2 style='text-align: center; color: #0D47A1; margin:0;'>⚙️ SIDHARTH</h2>", unsafe_allow_html=True)
            
            st.markdown("<h3 style='text-align:center; color:#0D47A1; margin-top:6px; margin-bottom:2px; font-size:1.2rem;'>AMC Tracker</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; color:#10B981; font-weight:700; font-size:0.8rem; margin-bottom:12px;'>● SIGN IN</p>", unsafe_allow_html=True)

            user_id_input = st.text_input("User ID / Tech ID", placeholder="e.g. TECH01").strip().upper()
            password_input = st.text_input("Password", type="password", placeholder="Enter password").strip()
            
            submit_login = st.form_submit_button("Sign In", use_container_width=True)

            if submit_login:
                user_df = st.session_state.users_db
                match = user_df[(user_df["User_ID"].astype(str) == user_id_input) & (user_df["Password"].astype(str) == password_input)]
                
                if not match.empty:
                    st.session_state.user = match.iloc[0].to_dict()
                    st.success(f"Welcome back, {st.session_state.user['Full_Name']}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password")
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# -----------------------------------------------------------------------------
# 5. SIDEBAR SETUP
# -----------------------------------------------------------------------------

with st.sidebar:
    logo_path = get_logo_path()
    
    st.markdown("<div class='sidebar-logo-container'>", unsafe_allow_html=True)
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h3 style='color: #0D47A1; text-align:center;'>⚙️ SIDHARTH</h3>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-logo-sub'>AMC TRACKER</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.divider()

    st.markdown(f"**Logged User:** {st.session_state.user['Full_Name']}")
    st.markdown(f"**Role:** `{st.session_state.user['Role']}`")
    
    if st.button("Logout", key="logout_btn"):
        st.session_state.user = None
        st.rerun()

# -----------------------------------------------------------------------------
# 6. TECHNICIAN DASHBOARD
# -----------------------------------------------------------------------------

if st.session_state.user["Role"] == "Technician":
    tech_id = str(st.session_state.user["User_ID"])
    
    st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 10px;'>
        <h1 style='color: #0D47A1; margin: 0;'>🛠️ Technician Dashboard</h1>
        <span style='font-size: 1.5rem; color: #64748B;'>— {st.session_state.user['Full_Name']}</span>
    </div>
    """, unsafe_allow_html=True)

    tech_tab1, tech_tab2, tech_tab3 = st.tabs(["📋 My Assigned Work Orders", "📍 Update Status & Destination", "📜 Service History"])

    # TAB 1: Assigned Jobs
    with tech_tab1:
        st.subheader("Assigned Maintenance Tasks")
        
        tech_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"].astype(str) == tech_id) & 
            (st.session_state.jobs_db["Status"] != "Completed")
        ]
        
        if tech_jobs.empty:
            st.info("🎉 No pending maintenance visits assigned to you.")
        else:
            st.caption(f"📌 You have **{len(tech_jobs)} active task(s)** assigned.")
            for idx, job in tech_jobs.iterrows():
                pincode_str = f" - {job['Pincode']}" if "Pincode" in job and pd.notna(job["Pincode"]) else ""
                with st.expander(f"🔵 [{job['Job_ID']}] {job['Client_Name']} — {job['City']}{pincode_str} ({job['Status']})", expanded=True):
                    col_a, col_b = st.columns([2, 1])
                    
                    with col_a:
                        st.markdown(f"**Address:** {job['Address']}, {job['City']} {pincode_str}")
                        st.markdown(f"**Client Contact:** [{job['Client_Phone']}](tel:{job['Client_Phone']})")
                        st.markdown(f"**Task Description:** {job['Issue_Description']}")
                        st.markdown(f"**Scheduled Time:** {job['Scheduled_Time']}")
                        
                        maps_url = make_google_maps_link(job['Address'], job['City'], job.get('Pincode', ''))
                        st.markdown(f"[📍 **Open Route in Google Maps**]({maps_url})")

                    with col_b:
                        st.markdown("### Update Progress")
                        status_list = ["Assigned", "In Transit", "On Site", "Completed"]
                        current_status = job["Status"] if job["Status"] in status_list else "Assigned"
                        
                        new_status = st.selectbox(
                            "Job Status",
                            status_list,
                            index=status_list.index(current_status),
                            key=f"status_{job['Job_ID']}"
                        )
                        if st.button("Save Status", key=f"btn_{job['Job_ID']}"):
                            st.session_state.jobs_db.loc[
                                st.session_state.jobs_db["Job_ID"] == job["Job_ID"], "Status"
                            ] = new_status
                            
                            save_sheet_data(st.session_state.jobs_db, "Jobs")
                            st.toast(f"✅ Status updated for {job['Job_ID']} in Google Sheets!")
                            st.rerun()

    # TAB 2: Location Broadcast
    with tech_tab2:
        st.subheader("Broadcast Live Location & Next Travel City")
        
        curr_rec = st.session_state.tech_status_db[
            st.session_state.tech_status_db["Tech_ID"].astype(str) == tech_id
        ]
        
        c_city = str(curr_rec["Current_City"].values[0]) if not curr_rec.empty and "Current_City" in curr_rec.columns else ""
        c_pin = str(curr_rec["Current_Pincode"].values[0]) if not curr_rec.empty and "Current_Pincode" in curr_rec.columns else ""
        c_status = str(curr_rec["Current_Status"].values[0]) if not curr_rec.empty and "Current_Status" in curr_rec.columns else "Available"
        n_city = str(curr_rec["Next_City"].values[0]) if not curr_rec.empty and "Next_City" in curr_rec.columns else ""
        n_pin = str(curr_rec["Next_Pincode"].values[0]) if not curr_rec.empty and "Next_Pincode" in curr_rec.columns else ""
        eta_val = str(curr_rec["ETA"].values[0]) if not curr_rec.empty and "ETA" in curr_rec.columns else ""

        with st.form("broadcast_location_form"):
            c1, c2 = st.columns(2)
            
            with c1:
                input_curr_city = st.text_input("Current City", value=c_city)
                input_curr_pin = st.text_input("Current Pin Code", value=c_pin, max_chars=6)
                status_options = ["Available", "On Site", "In Transit"]
                input_status = st.selectbox("Current Activity", status_options, index=status_options.index(c_status) if c_status in status_options else 0)
                
            with c2:
                input_next_city = st.text_input("Next Target Destination City", value=n_city)
                input_next_pin = st.text_input("Next Target Pin Code", value=n_pin, max_chars=6)
                input_eta = st.text_input("Estimated Arrival Time (ETA)", value=eta_val)
                
            submit_broadcast = st.form_submit_button("Broadcast Location Update")
            
            if submit_broadcast:
                now_str = datetime.now().strftime("%I:%M %p")
                
                if tech_id in st.session_state.tech_status_db["Tech_ID"].astype(str).values:
                    st.session_state.tech_status_db.loc[
                        st.session_state.tech_status_db["Tech_ID"].astype(str) == tech_id,
                        ["Current_City", "Current_Pincode", "Current_Status", "Next_City", "Next_Pincode", "ETA", "Last_Updated"]
                    ] = [input_curr_city, input_curr_pin, input_status, input_next_city, input_next_pin, input_eta, now_str]
                else:
                    new_row = {
                        "Tech_ID": tech_id,
                        "Current_City": input_curr_city,
                        "Current_Pincode": input_curr_pin,
                        "Current_Status": input_status,
                        "Next_City": input_next_city,
                        "Next_Pincode": input_next_pin,
                        "ETA": input_eta,
                        "Last_Updated": now_str
                    }
                    st.session_state.tech_status_db = pd.concat([st.session_state.tech_status_db, pd.DataFrame([new_row])], ignore_index=True)
                
                save_sheet_data(st.session_state.tech_status_db, "TechStatus")
                st.toast(f"📍 Location Updated Successfully at {now_str}!", icon="✅")
                st.rerun()

    # TAB 3: History
    with tech_tab3:
        st.subheader("My Service Record")
        completed_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"].astype(str) == tech_id) & 
            (st.session_state.jobs_db["Status"] == "Completed")
        ]
        st.dataframe(completed_jobs, use_container_width=True)

# -----------------------------------------------------------------------------
# 7. MANAGER COMMAND DASHBOARD
# -----------------------------------------------------------------------------

elif st.session_state.user["Role"] == "Manager":
    st.markdown("<h1 style='color: #0D47A1;'>📡 Dispatch Control Center</h1>", unsafe_allow_html=True)

    mgr_tab1, mgr_tab2, mgr_tab3 = st.tabs(["🗺️ Live Technician Radar", "➕ Create Maintenance Order", "👥 Manage Users"])

    # TAB 1: Live Radar
    with mgr_tab1:
        st.subheader("Technician Fleet Live Status")
        full_radar = pd.merge(
            st.session_state.tech_status_db, 
            st.session_state.users_db[["User_ID", "Full_Name"]], 
            left_on="Tech_ID", 
            right_on="User_ID", 
            how="left"
        )
        st.dataframe(full_radar, use_container_width=True)

        st.divider()
        st.subheader("All Maintenance Work Orders")
        st.dataframe(st.session_state.jobs_db, use_container_width=True)

    # TAB 2: Create Job
    with mgr_tab2:
        st.subheader("Dispatch Maintenance Visit")
        with st.form("new_job_form"):
            j_id = f"JOB-{len(st.session_state.jobs_db) + 101}"
            client_name = st.text_input("Client Name")
            client_phone = st.text_input("Client Phone")
            address = st.text_input("Site Address / GIDC Zone")
            city = st.text_input("City")
            pincode = st.text_input("Pin Code", max_chars=6)
            issue = st.text_area("Maintenance Service Notes")
            
            tech_list = st.session_state.users_db[st.session_state.users_db["Role"] == "Technician"]
            assigned_tech = st.selectbox(
                "Assign Technician", 
                options=tech_list["User_ID"].tolist(),
                format_func=lambda x: f"{x} - {tech_list[tech_list['User_ID']==x]['Full_Name'].values[0]}"
            )
            
            sched_time = st.text_input("Scheduled Date & Time", value="Today, 2:00 PM")
            submit_job = st.form_submit_button("Dispatch Order")
            
            if submit_job:
                new_job_entry = {
                    "Job_ID": j_id, "Assigned_Tech_ID": str(assigned_tech),
                    "Client_Name": client_name, "Client_Phone": client_phone,
                    "Address": address, "City": city, "Pincode": pincode,
                    "Issue_Description": issue, "Status": "Assigned",
                    "Scheduled_Time": sched_time
                }
                st.session_state.jobs_db = pd.concat([st.session_state.jobs_db, pd.DataFrame([new_job_entry])], ignore_index=True)
                
                save_sheet_data(st.session_state.jobs_db, "Jobs")
                st.toast(f"✅ Work Order {j_id} assigned and saved to Google Sheets!")
                st.rerun()

    # TAB 3: User Accounts
    with mgr_tab3:
        st.subheader("Register Technician Account")
        with st.form("add_user_form"):
            new_uid = st.text_input("User ID (e.g. TECH03)").strip().upper()
            new_name = st.text_input("Full Name")
            new_role = st.selectbox("Role", ["Technician", "Manager"])
            new_pass = st.text_input("Password", type="password").strip()
            
            submit_user = st.form_submit_button("Create Account")
            
            if submit_user:
                if new_uid in st.session_state.users_db["User_ID"].astype(str).values:
                    st.error("User ID already exists!")
                else:
                    user_entry = {"User_ID": new_uid, "Full_Name": new_name, "Role": new_role, "Password": new_pass}
                    st.session_state.users_db = pd.concat([st.session_state.users_db, pd.DataFrame([user_entry])], ignore_index=True)
                    
                    save_sheet_data(st.session_state.users_db, "Users")
                    st.toast(f"✅ Account for {new_name} saved to Google Sheets!")
                    st.rerun()
        
        st.subheader("Registered System Users")
        st.dataframe(st.session_state.users_db[["User_ID", "Full_Name", "Role"]], use_container_width=True)
