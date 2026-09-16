import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os

st.set_page_config(
    page_title="Annual Maintenance Tracker", 
    page_icon="🛠️", 
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. DATABASE / PERSISTENCE SETUP
# -----------------------------------------------------------------------------

if "users_db" not in st.session_state:
    st.session_state.users_db = pd.DataFrame([
        {"User_ID": "TECH01", "Full_Name": "Aaryan Sharma", "Role": "Technician", "Password": "123"},
        {"User_ID": "TECH02", "Full_Name": "Rahul Verma", "Role": "Technician", "Password": "123"},
        {"User_ID": "MGR01", "Full_Name": "Vikas Patel", "Role": "Manager", "Password": "admin"}
    ])

if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = pd.DataFrame([
        {
            "Job_ID": "JOB-101",
            "Assigned_Tech_ID": "TECH01",
            "Client_Name": "Apex Textiles",
            "Client_Phone": "+919876543210",
            "Address": "Plot 42, GIDC Phase 2",
            "City": "Vadodara",
            "Issue_Description": "Automatic shutter motor maintenance and sensor calibration.",
            "Status": "In Transit",
            "Scheduled_Time": "2026-09-16 14:00"
        },
        {
            "Job_ID": "JOB-102",
            "Assigned_Tech_ID": "TECH01",
            "Client_Name": "Gujarat Auto Ancillaries",
            "Client_Phone": "+919123456789",
            "Address": "Ring Road Sector 4",
            "City": "Surat",
            "Issue_Description": "Hydraulic automation gear service.",
            "Status": "Completed",
            "Scheduled_Time": "2026-09-16 09:30"
        },
        {
            "Job_ID": "JOB-103",
            "Assigned_Tech_ID": "TECH02",
            "Client_Name": "Lalita Chemicals",
            "Client_Phone": "+919898001122",
            "Address": "Sanand Industrial Estate",
            "City": "Ahmedabad",
            "Issue_Description": "Rolling shutter control box inspection.",
            "Status": "In Transit",
            "Scheduled_Time": "2026-09-16 11:00"
        }
    ])

if "tech_status_db" not in st.session_state:
    st.session_state.tech_status_db = pd.DataFrame([
        {
            "Tech_ID": "TECH01",
            "Current_City": "Surat",
            "Current_Status": "In Transit",
            "Next_City": "Vadodara",
            "ETA": "14:00",
            "Last_Updated": "10:30 AM"
        },
        {
            "Tech_ID": "TECH02",
            "Current_City": "Ahmedabad",
            "Current_Status": "In Transit",
            "Next_City": "Ahmedabad",
            "ETA": "11:00",
            "Last_Updated": "10:15 AM"
        }
    ])

def make_google_maps_link(address, city):
    query = urllib.parse.quote(f"{address}, {city}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"

def get_logo_path():
    for name in ["Company Logo.jpeg", "Company Logo.png", "Company Logo.jpg"]:
        if os.path.exists(name):
            return name
    return None

# -----------------------------------------------------------------------------
# 2. BRANDED UI STYLING (LOGOS, COLORS, BUTTONS, TABS)
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    /* Global Color Overrides to Blue (#1565C0) & Green (#10B981) */
    
    /* Active Tab Line & Text Color Override */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #1565C0 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #1565C0 !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }

    /* Sidebar Logo & Card Container Styling */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
    }
    .sidebar-brand-box {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 12px;
        border: 1px solid #E2E8F0;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Primary Action Buttons Override */
    .stButton > button {
        background-color: #1565C0 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #0D47A1 !important;
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.3) !important;
    }

    /* Links Color Override */
    a {
        color: #1565C0 !important;
    }

    /* Centered Login Screen Card Setup */
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        border: 2px solid #1565C0;
        border-radius: 16px;
        padding: 35px 30px;
        box-shadow: 0 12px 30px rgba(21, 101, 192, 0.12);
    }
    
    .brand-title {
        text-align: center;
        color: #0D47A1;
        font-weight: 800;
        font-size: 1.6rem;
        margin-top: 15px;
        margin-bottom: 5px;
    }
    .brand-subtitle {
        text-align: center;
        color: #10B981;
        font-weight: 700;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. AUTHENTICATION / LOGIN SCREEN
# -----------------------------------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    col_left, col_center, col_right = st.columns([1, 2.2, 1])

    with col_center:
        with st.form("login_form"):
            logo_path = get_logo_path()
            if logo_path:
                st.image(logo_path, use_container_width=True)
            else:
                st.markdown("<h1 style='text-align: center; color: #0D47A1;'>⚙️ SIDHARTH</h1>", unsafe_allow_html=True)
            
            st.markdown("<div class='brand-title'>AMC Annual Maintenance Tracker</div>", unsafe_allow_html=True)
            st.markdown("<div class='brand-subtitle'>● Technician Portal Sign In</div>", unsafe_allow_html=True)

            user_id_input = st.text_input("User ID / Tech ID", placeholder="e.g. TECH01").strip().upper()
            password_input = st.text_input("Password", type="password", placeholder="Enter your password").strip()
            
            submit_login = st.form_submit_button("Sign In")

            if submit_login:
                user_df = st.session_state.users_db
                match = user_df[(user_df["User_ID"] == user_id_input) & (user_df["Password"] == password_input)]
                
                if not match.empty:
                    st.session_state.user = match.iloc[0].to_dict()
                    st.success(f"Welcome back, {st.session_state.user['Full_Name']}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password")

    st.stop()

# -----------------------------------------------------------------------------
# 4. SIDEBAR SETUP WITH LOGO ON TOP-LEFT
# -----------------------------------------------------------------------------

with st.sidebar:
    # Display logo at top-left of sidebar
    logo_path = get_logo_path()
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h3 style='color: #0D47A1; margin: 0;'>⚙️ SIDHARTH</h3>", unsafe_allow_html=True)
    
    st.markdown("<p style='color: #10B981; font-weight: 700; font-size: 0.8rem; letter-spacing: 0.5px; margin-top: -10px;'>AMC TRACKER SYSTEM</p>", unsafe_allow_html=True)
    st.divider()

    st.markdown(f"**Logged User:** {st.session_state.user['Full_Name']}")
    st.markdown(f"**Role:** `{st.session_state.user['Role']}`")
    
    if st.button("Logout", key="logout_btn"):
        st.session_state.user = None
        st.rerun()

# -----------------------------------------------------------------------------
# 5. TECHNICIAN DASHBOARD
# -----------------------------------------------------------------------------

if st.session_state.user["Role"] == "Technician":
    tech_id = st.session_state.user["User_ID"]
    
    # Custom Styled Header
    st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 10px;'>
        <h1 style='color: #0D47A1; margin: 0;'>🛠️ Technician Dashboard</h1>
        <span style='font-size: 1.5rem; color: #64748B;'>— {st.session_state.user['Full_Name']}</span>
    </div>
    """, unsafe_allow_html=True)

    tech_tab1, tech_tab2, tech_tab3 = st.tabs(["📋 My Assigned Work Orders", "📍 Update Status & Destination", "📜 Service History"])

    # TAB 1: Assigned Jobs
    with tech_tab1:
        st.subheader("Scheduled Maintenance Visits")
        
        tech_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"] == tech_id) & 
            (st.session_state.jobs_db["Status"] != "Completed")
        ]
        
        if tech_jobs.empty:
            st.info("🎉 No pending maintenance visits assigned to you.")
        else:
            for idx, job in tech_jobs.iterrows():
                with st.expander(f"🔵 [{job['Job_ID']}] {job['Client_Name']} — {job['City']} ({job['Status']})", expanded=True):
                    col_a, col_b = st.columns([2, 1])
                    
                    with col_a:
                        st.markdown(f"**Address:** {job['Address']}, {job['City']}")
                        st.markdown(f"**Client Contact:** [{job['Client_Phone']}](tel:{job['Client_Phone']})")
                        st.markdown(f"**Task Description:** {job['Issue_Description']}")
                        st.markdown(f"**Scheduled Time:** {job['Scheduled_Time']}")
                        
                        maps_url = make_google_maps_link(job['Address'], job['City'])
                        st.markdown(f"[📍 **Open Route in Google Maps**]({maps_url})")

                    with col_b:
                        st.markdown("### Update Progress")
                        new_status = st.selectbox(
                            "Job Status",
                            ["Assigned", "In Transit", "On Site", "Completed"],
                            index=["Assigned", "In Transit", "On Site", "Completed"].index(job["Status"]),
                            key=f"status_{job['Job_ID']}"
                        )
                        if st.button("Save Status", key=f"btn_{job['Job_ID']}"):
                            st.session_state.jobs_db.loc[
                                st.session_state.jobs_db["Job_ID"] == job["Job_ID"], "Status"
                            ] = new_status
                            st.success("Work Order status updated!")
                            st.rerun()

    # TAB 2: Travel Updates
    with tech_tab2:
        st.subheader("Broadcast Live Location & Next Travel City")
        curr_status = st.session_state.tech_status_db[st.session_state.tech_status_db["Tech_ID"] == tech_id]
        
        with st.form("status_update_form"):
            c1, c2 = st.columns(2)
            with c1:
                current_city = st.text_input("Current City", value=curr_status["Current_City"].values[0] if not curr_status.empty else "")
                work_status = st.selectbox("Current Activity", ["Available", "On Site", "In Transit"])
            with c2:
                next_city = st.text_input("Next Target Destination", value=curr_status["Next_City"].values[0] if not curr_status.empty else "")
                eta = st.text_input("Estimated Arrival Time (ETA)", value=curr_status["ETA"].values[0] if not curr_status.empty else "")
                
            submit_status = st.form_submit_button("Broadcast Location Update")
            
            if submit_status:
                now_str = datetime.now().strftime("%I:%M %p")
                if tech_id in st.session_state.tech_status_db["Tech_ID"].values:
                    st.session_state.tech_status_db.loc[
                        st.session_state.tech_status_db["Tech_ID"] == tech_id,
                        ["Current_City", "Current_Status", "Next_City", "ETA", "Last_Updated"]
                    ] = [current_city, work_status, next_city, eta, now_str]
                else:
                    new_rec = {
                        "Tech_ID": tech_id, "Current_City": current_city,
                        "Current_Status": work_status, "Next_City": next_city,
                        "ETA": eta, "Last_Updated": now_str
                    }
                    st.session_state.tech_status_db = pd.concat([st.session_state.tech_status_db, pd.DataFrame([new_rec])], ignore_index=True)
                
                st.success("Your location update has been sent to dispatch!")
                st.rerun()

    # TAB 3: History
    with tech_tab3:
        st.subheader("My Service Record")
        completed_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"] == tech_id) & 
            (st.session_state.jobs_db["Status"] == "Completed")
        ]
        st.dataframe(completed_jobs, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. MANAGER COMMAND DASHBOARD
# -----------------------------------------------------------------------------

elif st.session_state.user["Role"] == "Manager":
    st.markdown("<h1 style='color: #0D47A1;'>📡 Dispatch Control Center</h1>", unsafe_allow_html=True)

    mgr_tab1, mgr_tab2, mgr_tab3 = st.tabs(["🗺️ Live Technician Radar", "➕ Create Maintenance Order", "👥 Manage Users"])

    # TAB 1: Live Radar
    with mgr_tab1:
        st.subheader("Technician Fleet Live Status")
        full_radar = pd.merge(st.session_state.tech_status_db, st.session_state.users_db[["User_ID", "Full_Name"]], left_on="Tech_ID", right_on="User_ID")
        
        st.dataframe(
            full_radar[["Tech_ID", "Full_Name", "Current_City", "Current_Status", "Next_City", "ETA", "Last_Updated"]],
            use_container_width=True
        )

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
                    "Job_ID": j_id, "Assigned_Tech_ID": assigned_tech,
                    "Client_Name": client_name, "Client_Phone": client_phone,
                    "Address": address, "City": city,
                    "Issue_Description": issue, "Status": "Assigned",
                    "Scheduled_Time": sched_time
                }
                st.session_state.jobs_db = pd.concat([st.session_state.jobs_db, pd.DataFrame([new_job_entry])], ignore_index=True)
                st.success(f"Work Order {j_id} assigned to {assigned_tech}!")
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
                if new_uid in st.session_state.users_db["User_ID"].values:
                    st.error("User ID already exists!")
                else:
                    user_entry = {"User_ID": new_uid, "Full_Name": new_name, "Role": new_role, "Password": new_pass}
                    st.session_state.users_db = pd.concat([st.session_state.users_db, pd.DataFrame([user_entry])], ignore_index=True)
                    st.success(f"Account for {new_name} ({new_uid}) created successfully!")
                    st.rerun()
        
        st.subheader("Registered System Users")
        st.dataframe(st.session_state.users_db[["User_ID", "Full_Name", "Role"]], use_container_width=True)
