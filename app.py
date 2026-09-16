import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os

st.set_page_config(page_title="TechDispatch System", page_icon="🔐", layout="wide")

# -----------------------------------------------------------------------------
# 1. DATABASE / PERSISTENCE SETUP (Session State Mock Data)
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
            "Issue_Description": "Main motor overhaul and sensor check.",
            "Status": "Assigned",
            "Scheduled_Time": "2026-09-16 14:00"
        },
        {
            "Job_ID": "JOB-102",
            "Assigned_Tech_ID": "TECH01",
            "Client_Name": "Gujarat Auto Ancillaries",
            "Client_Phone": "+919123456789",
            "Address": "Ring Road Sector 4",
            "City": "Surat",
            "Issue_Description": "Hydraulic pressure error code E-04.",
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
            "Issue_Description": "Control panel calibration.",
            "Status": "In Transit",
            "Scheduled_Time": "2026-09-16 11:00"
        }
    ])

if "tech_status_db" not in st.session_state:
    st.session_state.tech_status_db = pd.DataFrame([
        {
            "Tech_ID": "TECH01",
            "Current_City": "Surat",
            "Current_Status": "Available",
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

# Google Maps link generator
def make_google_maps_link(address, city):
    query = urllib.parse.quote(f"{address}, {city}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"

# -----------------------------------------------------------------------------
# 2. AUTHENTICATION & BRANDED CENTERED LOGIN SCREEN
# -----------------------------------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    # Custom CSS for theme-matching elements
    st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            max-width: 1000px !important;
        }
        
        div[data-testid="stForm"] {
            background-color: #FFFFFF;
            border: 2px solid #F59E0B;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
        }
        
        div[data-testid="stForm"] .stButton > button {
            background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
            color: #111827 !important;
            font-weight: 700 !important;
            font-size: 1.1rem !important;
            width: 100% !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.6rem 0 !important;
            margin-top: 10px !important;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3) !important;
        }
        
        div[data-testid="stForm"] .stButton > button:hover {
            background: linear-gradient(135deg, #D97706 0%, #B45309 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 6px 16px rgba(217, 119, 6, 0.4) !important;
        }
        
        .login-title {
            text-align: center;
            color: #111827;
            font-weight: 800;
            font-size: 1.7rem;
            margin-top: 10px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    # 3-column layout to center the login container
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        with st.form("login_form"):
            # Load image logo if present, fallback to icon
            logo_file = "Company Logo.png"
            if os.path.exists(logo_file):
                st.image(logo_file, use_container_width=True)
            else:
                st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin:0;'>🔐</h1>", unsafe_allow_html=True)
            
            st.markdown("<div class='login-title'>TechDispatch System Login</div>", unsafe_allow_html=True)

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
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------

st.sidebar.markdown(f"### 👤 Active User:\n**{st.session_state.user['Full_Name']}** ({st.session_state.user['Role']})")
if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

st.sidebar.divider()

# -----------------------------------------------------------------------------
# 4. TECHNICIAN DASHBOARD
# -----------------------------------------------------------------------------

if st.session_state.user["Role"] == "Technician":
    tech_id = st.session_state.user["User_ID"]
    st.title(f"🛠️ Technician Portal — {st.session_state.user['Full_Name']}")

    tech_tab1, tech_tab2, tech_tab3 = st.tabs(["📋 My Schedule", "📍 Live Status & Travel", "📜 Service History"])

    # TAB 1: Assigned Jobs
    with tech_tab1:
        st.subheader("Upcoming Work Orders")
        
        tech_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"] == tech_id) & 
            (st.session_state.jobs_db["Status"] != "Completed")
        ]
        
        if tech_jobs.empty:
            st.info("🎉 You have no active pending tasks.")
        else:
            for idx, job in tech_jobs.iterrows():
                with st.expander(f"🔴 [{job['Job_ID']}] {job['Client_Name']} — {job['City']} ({job['Status']})", expanded=True):
                    col_a, col_b = st.columns([2, 1])
                    
                    with col_a:
                        st.markdown(f"**Address:** {job['Address']}, {job['City']}")
                        st.markdown(f"**Contact Phone:** [{job['Client_Phone']}](tel:{job['Client_Phone']})")
                        st.markdown(f"**Issue Details:** {job['Issue_Description']}")
                        st.markdown(f"**Scheduled Arrival:** {job['Scheduled_Time']}")
                        
                        maps_url = make_google_maps_link(job['Address'], job['City'])
                        st.markdown(f"[📍 **Open Google Maps Route**]({maps_url})")

                    with col_b:
                        st.markdown("### Update Status")
                        new_status = st.selectbox(
                            "Job Status",
                            ["Assigned", "In Transit", "On Site", "Completed"],
                            index=["Assigned", "In Transit", "On Site", "Completed"].index(job["Status"]),
                            key=f"status_{job['Job_ID']}"
                        )
                        if st.button("Update Job", key=f"btn_{job['Job_ID']}"):
                            st.session_state.jobs_db.loc[
                                st.session_state.jobs_db["Job_ID"] == job["Job_ID"], "Status"
                            ] = new_status
                            st.success("Status updated!")
                            st.rerun()

    # TAB 2: Travel & Status Updates
    with tech_tab2:
        st.subheader("Broadcast Location & Next Destination")
        curr_status = st.session_state.tech_status_db[st.session_state.tech_status_db["Tech_ID"] == tech_id]
        
        with st.form("status_update_form"):
            c1, c2 = st.columns(2)
            with c1:
                current_city = st.text_input("Current City", value=curr_status["Current_City"].values[0] if not curr_status.empty else "")
                work_status = st.selectbox("Current Status", ["Available", "On Site", "In Transit"])
            with c2:
                next_city = st.text_input("Next Destination City", value=curr_status["Next_City"].values[0] if not curr_status.empty else "")
                eta = st.text_input("Estimated Arrival Time (ETA)", value=curr_status["ETA"].values[0] if not curr_status.empty else "")
                
            submit_status = st.form_submit_button("Send Update to Dispatch")
            
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
                
                st.success("Location update broadcasted successfully!")
                st.rerun()

    # TAB 3: History
    with tech_tab3:
        st.subheader("My Service History")
        completed_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"] == tech_id) & 
            (st.session_state.jobs_db["Status"] == "Completed")
        ]
        st.dataframe(completed_jobs, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. MANAGER DASHBOARD
# -----------------------------------------------------------------------------

elif st.session_state.user["Role"] == "Manager":
    st.title("📡 Dispatch Radar & Management Console")

    mgr_tab1, mgr_tab2, mgr_tab3 = st.tabs(["🗺️ Fleet Radar", "➕ Create Work Order", "👥 Manage Users"])

    # TAB 1: Live Fleet Overview
    with mgr_tab1:
        st.subheader("Technician Live Locations")
        full_radar = pd.merge(st.session_state.tech_status_db, st.session_state.users_db[["User_ID", "Full_Name"]], left_on="Tech_ID", right_on="User_ID")
        
        st.dataframe(
            full_radar[["Tech_ID", "Full_Name", "Current_City", "Current_Status", "Next_City", "ETA", "Last_Updated"]],
            use_container_width=True
        )

        st.divider()
        st.subheader("All System Work Orders")
        st.dataframe(st.session_state.jobs_db, use_container_width=True)

    # TAB 2: Create Job
    with mgr_tab2:
        st.subheader("Dispatch New Job")
        with st.form("new_job_form"):
            j_id = f"JOB-{len(st.session_state.jobs_db) + 101}"
            client_name = st.text_input("Client Name")
            client_phone = st.text_input("Client Phone")
            address = st.text_input("Address / Area")
            city = st.text_input("City")
            issue = st.text_area("Issue Description")
            
            tech_list = st.session_state.users_db[st.session_state.users_db["Role"] == "Technician"]
            assigned_tech = st.selectbox(
                "Assign To", 
                options=tech_list["User_ID"].tolist(),
                format_func=lambda x: f"{x} - {tech_list[tech_list['User_ID']==x]['Full_Name'].values[0]}"
            )
            
            sched_time = st.text_input("Scheduled Date/Time", value="Today, 2:00 PM")
            submit_job = st.form_submit_button("Create Assignment")
            
            if submit_job:
                new_job_entry = {
                    "Job_ID": j_id, "Assigned_Tech_ID": assigned_tech,
                    "Client_Name": client_name, "Client_Phone": client_phone,
                    "Address": address, "City": city,
                    "Issue_Description": issue, "Status": "Assigned",
                    "Scheduled_Time": sched_time
                }
                st.session_state.jobs_db = pd.concat([st.session_state.jobs_db, pd.DataFrame([new_job_entry])], ignore_index=True)
                st.success(f"Work Order {j_id} created and dispatched to {assigned_tech}!")
                st.rerun()

    # TAB 3: Add/Manage Users
    with mgr_tab3:
        st.subheader("Add Account")
        with st.form("add_user_form"):
            new_uid = st.text_input("User ID (e.g. TECH03)").strip().upper()
            new_name = st.text_input("Full Name")
            new_role = st.selectbox("Role", ["Technician", "Manager"])
            new_pass = st.text_input("Password", type="password").strip()
            
            submit_user = st.form_submit_button("Save User Account")
            
            if submit_user:
                if new_uid in st.session_state.users_db["User_ID"].values:
                    st.error("User ID already exists!")
                else:
                    user_entry = {"User_ID": new_uid, "Full_Name": new_name, "Role": new_role, "Password": new_pass}
                    st.session_state.users_db = pd.concat([st.session_state.users_db, pd.DataFrame([user_entry])], ignore_index=True)
                    st.success(f"Account for {new_name} ({new_uid}) created!")
                    st.rerun()
        
        st.subheader("Registered Users")
        st.dataframe(st.session_state.users_db[["User_ID", "Full_Name", "Role"]], use_container_width=True)
