import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="TechDispatch Manager", page_icon="🛠️", layout="wide")

# -----------------------------------------------------------------------------
# 1. MOCK DATA & PERSISTENCE (Replace with Google Sheets API / gspread in production)
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

# Helper function to generate Google Maps link
def make_google_maps_link(address, city):
    query = urllib.parse.quote(f"{address}, {city}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"

# -----------------------------------------------------------------------------
# 2. USER AUTHENTICATION & LOGIN SCREEN
# -----------------------------------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🔐 TechDispatch System Login")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        user_id_input = st.text_input("User ID / Tech ID").strip().upper()
        password_input = st.text_input("Password", type="password")
        
        if st.button("Login", type="primary"):
            user_df = st.session_state.users_db
            match = user_df[(user_df["User_ID"] == user_id_input) & (user_df["Password"] == password_input)]
            
            if not match.empty:
                st.session_state.user = match.iloc[0].to_dict()
                st.success(f"Welcome back, {st.session_state.user['Full_Name']}!")
                st.rerun()
            else:
                st.error("Invalid User ID or Password")
    st.stop()

# -----------------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION & USER INFO
# -----------------------------------------------------------------------------

st.sidebar.markdown(f"### 👤 Logged in as:\n**{st.session_state.user['Full_Name']}** ({st.session_state.user['Role']})")
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

    # Tab layout for Technician
    tech_tab1, tech_tab2, tech_tab3 = st.tabs(["📋 My Assigned Jobs", "📍 Update My Status & Travel", "📜 Job History"])

    # TAB 1: Assigned Jobs
    with tech_tab1:
        st.subheader("Upcoming Client Assignments")
        
        tech_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"] == tech_id) & 
            (st.session_state.jobs_db["Status"] != "Completed")
        ]
        
        if tech_jobs.empty:
            st.info("🎉 No pending jobs assigned to you right now.")
        else:
            for idx, job in tech_jobs.iterrows():
                with st.expander(f"🔴 [{job['Job_ID']}] {job['Client_Name']} — {job['City']} ({job['Status']})", expanded=True):
                    col_a, col_b = st.columns([2, 1])
                    
                    with col_a:
                        st.markdown(f"**Address:** {job['Address']}, {job['City']}")
                        st.markdown(f"**Contact:** [{job['Client_Phone']}](tel:{job['Client_Phone']})")
                        st.markdown(f"**Issue Description:** {job['Issue_Description']}")
                        st.markdown(f"**Scheduled Time:** {job['Scheduled_Time']}")
                        
                        # Google Maps Button
                        maps_url = make_google_maps_link(job['Address'], job['City'])
                        st.markdown(f"[📍 Open Location in Google Maps]({maps_url})")

                    with col_b:
                        st.markdown("### Update Job Status")
                        new_status = st.selectbox(
                            "Change Status",
                            ["Assigned", "In Transit", "On Site", "Completed"],
                            index=["Assigned", "In Transit", "On Site", "Completed"].index(job["Status"]),
                            key=f"status_{job['Job_ID']}"
                        )
                        if st.button("Save Job Status", key=f"btn_{job['Job_ID']}"):
                            st.session_state.jobs_db.loc[
                                st.session_state.jobs_db["Job_ID"] == job["Job_ID"], "Status"
                            ] = new_status
                            st.success("Job status updated successfully!")
                            st.rerun()

    # TAB 2: Travel / Status Updates
    with tech_tab2:
        st.subheader("Update Live Location & Next Travel Destination")
        
        curr_status = st.session_state.tech_status_db[st.session_state.tech_status_db["Tech_ID"] == tech_id]
        
        with st.form("status_update_form"):
            c1, c2 = st.columns(2)
            with c1:
                current_city = st.text_input("Current City", value=curr_status["Current_City"].values[0] if not curr_status.empty else "")
                work_status = st.selectbox("Current Activity", ["Available", "On Site", "In Transit"])
            with c2:
                next_city = st.text_input("Next Destination City", value=curr_status["Next_City"].values[0] if not curr_status.empty else "")
                eta = st.text_input("ETA / Scheduled Arrival Time", value=curr_status["ETA"].values[0] if not curr_status.empty else "")
                
            submit_status = st.form_submit_button("Broadcast Location Update")
            
            if submit_status:
                now_str = datetime.now().strftime("%I:%M %p")
                
                # Check if tech exists in DB
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
                
                st.success("Your location and next destination have been sent to dispatch!")
                st.rerun()

    # TAB 3: History
    with tech_tab3:
        st.subheader("My Completed Jobs")
        completed_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"] == tech_id) & 
            (st.session_state.jobs_db["Status"] == "Completed")
        ]
        st.dataframe(completed_jobs, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. MANAGER COMMAND CENTER
# -----------------------------------------------------------------------------

elif st.session_state.user["Role"] == "Manager":
    st.title("📡 Manager Dispatch & Live Fleet Radar")

    mgr_tab1, mgr_tab2, mgr_tab3 = st.tabs(["🗺️ Live Technician Radar", "➕ Assign New Job", "👥 Manage Users"])

    # TAB 1: Live Status Board
    with mgr_tab1:
        st.subheader("Technician Fleet Overview")
        
        # Merge status with user names
        full_radar = pd.merge(st.session_state.tech_status_db, st.session_state.users_db[["User_ID", "Full_Name"]], left_on="Tech_ID", right_on="User_ID")
        
        st.dataframe(
            full_radar[["Tech_ID", "Full_Name", "Current_City", "Current_Status", "Next_City", "ETA", "Last_Updated"]],
            use_container_width=True
        )

        st.divider()
        st.subheader("All System Work Orders")
        st.dataframe(st.session_state.jobs_db, use_container_width=True)

    # TAB 2: Assign Job
    with mgr_tab2:
        st.subheader("Create & Assign Work Order")
        
        with st.form("new_job_form"):
            j_id = f"JOB-{len(st.session_state.jobs_db) + 101}"
            client_name = st.text_input("Client Name")
            client_phone = st.text_input("Client Contact Number")
            address = st.text_input("Street Address / GIDC Zone")
            city = st.text_input("Target City")
            issue = st.text_area("Issue / Service Notes")
            
            # Select Technician
            tech_list = st.session_state.users_db[st.session_state.users_db["Role"] == "Technician"]
            assigned_tech = st.selectbox(
                "Assign To Technician", 
                options=tech_list["User_ID"].tolist(),
                format_func=lambda x: f"{x} - {tech_list[tech_list['User_ID']==x]['Full_Name'].values[0]}"
            )
            
            sched_time = st.text_input("Scheduled Date & Time", value="Today, 2:00 PM")
            
            submit_job = st.form_submit_button("Dispatch Work Order")
            
            if submit_job:
                new_job_entry = {
                    "Job_ID": j_id,
                    "Assigned_Tech_ID": assigned_tech,
                    "Client_Name": client_name,
                    "Client_Phone": client_phone,
                    "Address": address,
                    "City": city,
                    "Issue_Description": issue,
                    "Status": "Assigned",
                    "Scheduled_Time": sched_time
                }
                st.session_state.jobs_db = pd.concat([st.session_state.jobs_db, pd.DataFrame([new_job_entry])], ignore_index=True)
                st.success(f"Work Order {j_id} assigned successfully to {assigned_tech}!")
                st.rerun()

    # TAB 3: Account Creation
    with mgr_tab3:
        st.subheader("Register New Technician / Manager")
        with st.form("add_user_form"):
            new_uid = st.text_input("New User ID (e.g., TECH03)").strip().upper()
            new_name = st.text_input("Full Name")
            new_role = st.selectbox("Role", ["Technician", "Manager"])
            new_pass = st.text_input("Initial Password", type="password")
            
            submit_user = st.form_submit_button("Create User Account")
            
            if submit_user:
                if new_uid in st.session_state.users_db["User_ID"].values:
                    st.error("User ID already exists!")
                else:
                    user_entry = {"User_ID": new_uid, "Full_Name": new_name, "Role": new_role, "Password": new_pass}
                    st.session_state.users_db = pd.concat([st.session_state.users_db, pd.DataFrame([user_entry])], ignore_index=True)
                    st.success(f"Account for {new_name} ({new_uid}) created successfully!")
                    st.rerun()
        
        st.subheader("All User Accounts")
        st.dataframe(st.session_state.users_db[["User_ID", "Full_Name", "Role"]], use_container_width=True)
