import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import zoneinfo
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
    st.error(f"⚠️ Could not connect to Google Sheets. Error: {e}")
    st.stop()

def load_sheet_data(worksheet_name):
    service_report_cols = [
        "Report_ID", "Job_ID", "Tech_ID", "Tech_Name", "Client_Name", "PO_Number", 
        "Site_Location", "AMC_Contract_No", "Category", "Equipment_Type", "Make_Model", 
        "Door_Size", "Qty", "Condition", "Checklist_Data", "Service_Date", "Visit_Number", 
        "Next_Service_Due_Date", "Distance_Travelled_KM", "Time_Taken_Hours", "Work_Done_Details", 
        "Site_Photo", "Problems_Faced", "Remarks", "Submitted_At"
    ]
    
    for i in range(1, 19):
        service_report_cols.extend([f"Q{i}_Choice", f"Q{i}_Remark"])

    default_columns = {
        "Users": ["User_ID", "Full_Name", "Role", "Password"],
        "Jobs": ["Job_ID", "Assigned_Tech_ID", "Client_Name", "Client_Phone", "Address", "City", "Pincode", "Issue_Description", "Status", "Scheduled_Time"],
        "TechStatus": ["Tech_ID", "Current_City", "Current_Pincode", "Current_Status", "Next_City", "Next_Pincode", "ETA", "Last_Updated"],
        "ServiceReports": service_report_cols,
        "AMCContracts": ["AMC_Contract_No", "PO_Number", "Client_Name", "Start_Date", "End_Date", "Allowed_Visits", "Next_Visit_Due"]
    }
    
    cols = default_columns.get(worksheet_name, [])
    
    try:
        ws = sh.worksheet(worksheet_name)
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        
        for col in cols:
            if col not in df.columns:
                df[col] = ""
                
        return df[cols]
    except Exception:
        try:
            ws = sh.add_worksheet(title=worksheet_name, rows="100", cols="60")
            if cols:
                ws.append_row(cols)
            return pd.DataFrame(columns=cols)
        except Exception:
            return pd.DataFrame(columns=cols)

def save_sheet_data(df, worksheet_name):
    try:
        ws = sh.worksheet(worksheet_name)
        ws.clear()
        clean_df = df.fillna("").astype(str)
        ws.update([clean_df.columns.values.tolist()] + clean_df.values.tolist())
    except Exception as e:
        st.error(f"❌ Failed to save data to Google Sheets ({worksheet_name}): {e}")

# Initialize Session Data
if "users_db" not in st.session_state:
    st.session_state.users_db = load_sheet_data("Users")

if "jobs_db" not in st.session_state:
    st.session_state.jobs_db = load_sheet_data("Jobs")

if "tech_status_db" not in st.session_state:
    st.session_state.tech_status_db = load_sheet_data("TechStatus")

if "service_reports_db" not in st.session_state:
    st.session_state.service_reports_db = load_sheet_data("ServiceReports")

if "amc_contracts_db" not in st.session_state:
    st.session_state.amc_contracts_db = load_sheet_data("AMCContracts")

if "selected_job_for_report" not in st.session_state:
    st.session_state.selected_job_for_report = None

# -----------------------------------------------------------------------------
# 2. CHECKLIST DATA CONFIGURATION
# -----------------------------------------------------------------------------

EQUIPMENT_DATA = {
    "Rolling Shutter": {
        "types": [
            "Motorized Rolling Shutter (Central / Side Motor)",
            "Manual Pull-Push / Gear Operated Shutter",
            "Insulated / Double-Walled Slats Shutter",
            "Perforated / Grill Type Rolling Shutter",
            "Fire Rated Rolling Shutter"
        ],
        "checklist": [
            "Shutter Curtain Slats, End Locks & Bottom Profile Alignment",
            "Side Guide Channels (Tracks), Rubber Seals & Weather Strips Check",
            "Main Shaft Pipe, Counterbalance Springs & Drum Bearings",
            "Drive Motor (Central/Side Tubular), Gear Box & Mechanical Brake",
            "Mechanical Electromechanical Limit Switches (Top & Bottom Cut-off)",
            "Manual Override System (Hand Chain / Hand Crank Release)",
            "Control Panel, Push Button Box, Wiring Connections & Relays",
            "RF Remote Control Receiver, Handheld Transmitters & Key Switches",
            "Safety Anti-Fall Brake / Parachute Safety Device Inspection",
            "Safety Obstacle Infrared Sensors / Safety Edge Operation Check",
            "Drive Sprockets, Drive Chains & Alignment Tension Adjustments",
            "Fire Shutter Fusible Link & Auto-Closing Signal Drop Test (If App.)",
            "Central Shaft Mechanical Spring Tension Adjustments",
            "Hood Cover (Canopy Box) Structure & Brackets Rigidity",
            "Greasing & Lubrication of Guide Tracks, Bearings & Chains",
            "Smooth Up/Down Motion Check & Absence of Abnormal Noise",
            "Mechanical Center Lock & Side Shoot Bolt Lock Verification",
            "Complete Automatic & Manual Operation Cycle Test"
        ]
    },
    "High Speed Door": {
        "types": [
            "High Speed Roll-Up Door (PVC Fabric)",
            "Self-Repairing High Speed Door",
            "Cold Room / Freezer High Speed Door",
            "Cleanroom High Speed Door",
            "High Speed Spiral / Aluminium Door"
        ],
        "checklist": [
            "Door Curtain / Fabric Panel Condition & Vision Window Clarity",
            "Side Guide Channels, Wind Stiffener Bars & Seals Integrity",
            "Self-Repairing Zipper / Track Re-insertion Mechanism",
            "High-Speed Drive Motor, Gearbox & Brake Assembly",
            "VFD (Variable Frequency Drive) Speed Settings (Soft Start / Stop)",
            "Digital Absolute Encoder / Limit Switch Settings",
            "Multi-Beam Safety Light Curtain Barrier Operation",
            "Bottom Edge Wireless/Wired Safety Sensor & Contact Edge",
            "Radar Motion Sensors / Microwave Motion Activation",
            "Induction Loop Sensors & Pull-Cord Switch Functions",
            "Air Lock Interlocking System (Cleanroom / Cold Room Door)",
            "Control Panel Connections, PLC / Microcontroller Display & Fuses",
            "Counterbalance Springs / Tensioning Belts / Shaft Bearings",
            "Emergency Manual Crank / Hand Lever Release Operation",
            "UPS / Battery Backup Automatic Opening System",
            "Greasing & Lubrication of Bearings, Guides & Drive Chains",
            "Full Cycle High-Speed Opening & Closing Operation Check",
            "Safety Reversing Test on Obstacle Detection"
        ]
    }
}

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def make_google_maps_link(address, city, pincode=""):
    query = urllib.parse.quote(f"{address}, {city} {pincode}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={query}"

def get_logo_path():
    for name in ["Company Logo.jpeg", "Company Logo.png", "Company Logo.jpg"]:
        if os.path.exists(name):
            return name
    return None

def filter_df_by_date_range(df, date_col, filter_option):
    if df.empty or date_col not in df.columns:
        return df
    
    temp_df = df.copy()
    temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
    today = pd.Timestamp(date.today())
    
    if filter_option == "Today":
        return temp_df[temp_df[date_col].dt.date == date.today()]
    elif filter_option == "Weekly (Last 7 Days)":
        return temp_df[temp_df[date_col] >= (today - timedelta(days=7))]
    elif filter_option == "Monthly (Last 30 Days)":
        return temp_df[temp_df[date_col] >= (today - timedelta(days=30))]
    elif filter_option == "3 Months":
        return temp_df[temp_df[date_col] >= (today - timedelta(days=90))]
    elif filter_option == "Yearly":
        return temp_df[temp_df[date_col] >= (today - timedelta(days=365))]
    return temp_df

# -----------------------------------------------------------------------------
# 4. BRANDED UI STYLING
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    .stApp { background-color: #F4F6F9 !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #0F3D7A !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #0F3D7A !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .sidebar-logo-sub { color: #00A859; font-weight: 800; font-size: 0.85rem; letter-spacing: 1.5px; text-align: center; margin-top: 4px; }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 2px solid #0F3D7A !important;
        border-radius: 20px !important;
        padding: 30px 28px 24px 28px !important;
        box-shadow: 0px 10px 25px rgba(15, 61, 122, 0.08) !important;
        max-width: 440px !important;
        margin: 20px auto 0 auto !important;
    }

    div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }

    .login-subtitle {
        text-align: center; color: #556B82; font-size: 0.95rem; font-weight: 600;
        margin-top: -10px; margin-bottom: 25px;
    }

    .login-field-label {
        color: #0F3D7A; font-weight: 700; font-size: 0.95rem;
        margin-bottom: 4px; margin-top: 12px;
    }

    div[data-testid="stTextInput"] > div[data-baseweb="input"] {
        background-color: #F0F4F8 !important;
        border: 1.5px solid #0F3D7A !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    div[data-testid="stTextInput"] input {
        border: none !important; background-color: transparent !important; color: #1E293B !important; height: 42px !important;
    }

    div[data-testid="stFormSubmitButton"] > button {
        background-color: #00A859 !important; color: #FFFFFF !important;
        border-radius: 8px !important; font-weight: 800 !important; font-size: 1rem !important;
        padding: 12px 28px !important; border: none !important; margin: 0 auto !important; display: block !important;
        box-shadow: 0 4px 10px rgba(0, 168, 89, 0.25) !important;
    }

    .equipment-box {
        background-color: #FFFFFF; border-left: 5px solid #0F3D7A;
        border-radius: 8px; padding: 12px 18px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .equipment-title { color: #0F3D7A !important; font-weight: 700; margin: 0 0 10px 0; font-size: 1.25rem; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN FORM SECTION ---
def render_login_form():
    st.markdown("### 🔐 User Login")
    
    # Toggle password visibility checkbox
    show_password = st.checkbox("Show password", key="show_pwd_toggle")
    pwd_type = "text" if show_password else "password"
    
    # Username input
    user_id_input = st.text_input(
        "User ID / Phone", 
        placeholder="Enter User ID or Phone", 
        key="login_userid",
        label_visibility="collapsed"
    )
    if user_id_input:
        user_id_input = user_id_input.strip()

    # Password input (FIXED)
    password_input = st.text_input(
        "Password Input Field", 
        type=pwd_type, 
        placeholder="Enter password", 
        key="login_password", 
        label_visibility="collapsed"
    )
    if password_input:
        password_input = password_input.strip()

    # Login Action Button
    if st.button("Sign In", type="primary", use_container_width=True):
        if not user_id_input or not password_input:
            st.warning("⚠️ Please enter both User ID and Password.")
        else:
            users_df = st.session_state.users_db
            
            # Match user credentials
            matched_user = users_df[
                (users_df["User_ID"].astype(str) == user_id_input) & 
                (users_df["Password"].astype(str) == password_input)
            ]
            
            if not matched_user.empty:
                user_info = matched_user.iloc[0]
                st.session_state["authenticated"] = True
                st.session_state["user_id"] = str(user_info["User_ID"])
                st.session_state["user_name"] = str(user_info["Full_Name"])
                st.session_state["user_role"] = str(user_info["Role"])
                st.success(f"Welcome back, {user_info['Full_Name']}!")
                st.rerun()
            else:
                st.error("❌ Invalid User ID or Password. Please try again.")

# -----------------------------------------------------------------------------
# 6. SIDEBAR
# -----------------------------------------------------------------------------

with st.sidebar:
    logo_path = get_logo_path()
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h3 style='color: #0F3D7A; text-align:center;'>⚙️ SIDHARTH</h3>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-logo-sub'>AMC TRACKER</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"**Logged User:** {st.session_state.user['Full_Name']}")
    st.markdown(f"**Role:** `{st.session_state.user['Role']}`")
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

# -----------------------------------------------------------------------------
# 7. TECHNICIAN DASHBOARD
# -----------------------------------------------------------------------------

if st.session_state.user["Role"] == "Technician":
    tech_id = str(st.session_state.user["User_ID"])
    tech_name = st.session_state.user["Full_Name"]

    st.markdown(f"<h1>🛠️ Technician Dashboard — <span style='color:#64748B;'>{tech_name}</span></h1>", unsafe_allow_html=True)

    tech_tab1, tech_tab2, tech_tab3, tech_tab4 = st.tabs([
        "📋 Assigned Work Orders", 
        "📝 Submit Service Report",
        "📍 Update Live Status", 
        "📈 My Reports & Progress History"
    ])

    # TAB 1: Filterable Progress Dashboard & Analytics
    with mgr_tab1:
        st.subheader("📊 Technician Field Operations & Progress Dashboard")
        
        # 1. FILTERS SECTION
        f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
        with f_col1:
            time_filter = st.selectbox(
                "🗓️ Date Range Filter", 
                ["All Time", "Today", "Weekly (Last 7 Days)", "Monthly (Last 30 Days)", "3 Months", "Yearly"]
            )
        
        tech_users = st.session_state.users_db[st.session_state.users_db["Role"] == "Technician"]
        tech_options = ["All Technicians"] + tech_users["Full_Name"].tolist()
        
        with f_col2:
            tech_filter = st.selectbox("👷 Technician Filter", tech_options)

        all_reports = st.session_state.service_reports_db.copy()
        
        # Apply Time & Tech Filters
        if time_filter != "All Time":
            all_reports = filter_df_by_date_range(all_reports, "Service_Date", time_filter)
            
        if tech_filter != "All Technicians":
            all_reports = all_reports[all_reports["Tech_Name"] == tech_filter]

        st.divider()

        # 2. TOP LEVEL SUMMARY METRICS (KPIs)
        tot_visited = len(all_reports)
        
        if not all_reports.empty and "Distance_Travelled_KM" in all_reports.columns:
            all_reports["Distance_Travelled_KM"] = pd.to_numeric(all_reports["Distance_Travelled_KM"], errors='coerce').fillna(0)
            tot_dist = all_reports["Distance_Travelled_KM"].sum()
        else:
            tot_dist = 0.0

        if not all_reports.empty and "Time_Taken_Hours" in all_reports.columns:
            all_reports["Time_Taken_Hours"] = pd.to_numeric(all_reports["Time_Taken_Hours"], errors='coerce').fillna(0)
            tot_time = all_reports["Time_Taken_Hours"].sum()
        else:
            tot_time = 0.0

        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.metric("📍 Total Sites Visited", tot_visited)
        p_col2.metric("🚗 Total Travelled", f"{tot_dist:.1f} KM")
        p_col3.metric("⏱️ Total Field Hours", f"{tot_time:.1f} Hours")
        p_col4.metric("📊 Avg Time / Site", f"{(tot_time / tot_visited):.1f} Hrs" if tot_visited > 0 else "0.0 Hrs")

        st.divider()

        # 3. VISUAL ANALYTICS & CHARTS
        if not all_reports.empty and "Tech_Name" in all_reports.columns:
            chart_col1, chart_col2 = st.columns(2)
            
            # Aggregate per technician for charts
            summary_grp = all_reports.groupby("Tech_Name").agg(
                Sites_Visited=("Report_ID", "count"),
                Total_KM=("Distance_Travelled_KM", "sum"),
                Total_Hours=("Time_Taken_Hours", "sum")
            ).reset_index()

            with chart_col1:
                st.markdown("#### 📍 Sites Visited per Technician")
                st.bar_chart(data=summary_grp, x="Tech_Name", y="Sites_Visited", color="#0F3D7A")

            with chart_col2:
                st.markdown("#### 🚗 Total Travel Distance (KM)")
                st.bar_chart(data=summary_grp, x="Tech_Name", y="Total_KM", color="#00A859")

            st.divider()

            # 4. WORK COMPLETION PROGRESS
            st.markdown("### 🎯 Task Completion Rate by Technician")
            all_jobs = st.session_state.jobs_db.copy()
            
            for _, tech in tech_users.iterrows():
                t_id = str(tech["User_ID"])
                t_name = tech["Full_Name"]
                
                tech_jobs = all_jobs[all_jobs["Assigned_Tech_ID"].astype(str) == t_id]
                total_assigned = len(tech_jobs)
                completed = len(tech_jobs[tech_jobs["Status"] == "Completed"])
                
                if total_assigned > 0:
                    pct = int((completed / total_assigned) * 100)
                    col_txt, col_bar = st.columns([2, 5])
                    with col_txt:
                        st.write(f"**{t_name}**: {completed}/{total_assigned} Jobs Done ({pct}%)")
                    with col_bar:
                        st.progress(pct / 100)

            st.divider()

            # 5. DATA TABLE & CSV DOWNLOAD BUTTON
            st.markdown("### 📋 Progress Summary Table")
            st.dataframe(summary_grp, use_container_width=True)
            
            csv_data = all_reports.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Detailed Progress Report (CSV)",
                data=csv_data,
                file_name=f"technician_progress_report_{date.today()}.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.info("ℹ️ No visit or progress records match the selected filter criteria.")
            
    # TAB 2: Service Report Form (WITH PO NUMBER, TIME & DISTANCE TRACKING)
    with tech_tab2:
        st.subheader("📝 Submit Field Service Visit Report")
        
        pending_tech_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"].astype(str) == tech_id) & 
            (st.session_state.jobs_db["Status"] != "Completed")
        ]
        
        if pending_tech_jobs.empty:
            st.info("🎉 No pending or assigned tasks found for you to submit a report for.")
        else:
            job_options = pending_tech_jobs["Job_ID"].tolist()
            default_index = job_options.index(st.session_state.selected_job_for_report) if st.session_state.selected_job_for_report in job_options else 0
                
            selected_job_id = st.selectbox(
                "Select Assigned Job / Task*", 
                job_options, 
                index=default_index,
                format_func=lambda x: f"{x} — {pending_tech_jobs[pending_tech_jobs['Job_ID'] == x]['Client_Name'].values[0]} ({pending_tech_jobs[pending_tech_jobs['Job_ID'] == x]['City'].values[0]})"
            )
            
            selected_job = pending_tech_jobs[pending_tech_jobs["Job_ID"] == selected_job_id].iloc[0]
            auto_client_name = str(selected_job.get("Client_Name", ""))
            auto_address = f"{selected_job.get('Address', '')}, {selected_job.get('City', '')}".strip(", ")
            if selected_job.get("Pincode"):
                auto_address += f" - {selected_job.get('Pincode')}"

            contracts_df = st.session_state.amc_contracts_db
            contract_options = ["N/A"] + contracts_df["AMC_Contract_No"].astype(str).tolist() if not contracts_df.empty else ["N/A"]

            c_header1, c_header2 = st.columns(2)
            with c_header1:
                st.text_input("Client Name", value=auto_client_name, disabled=True)
                selected_contract_no = st.selectbox("Link AMC Contract Number", contract_options)
                
                # Auto-populate PO Number associated with Contract Number if available
                auto_po = "N/A"
                if selected_contract_no != "N/A" and not contracts_df.empty:
                    po_match = contracts_df[contracts_df["AMC_Contract_No"] == selected_contract_no]["PO_Number"].values
                    if len(po_match) > 0 and str(po_match[0]).strip():
                        auto_po = str(po_match[0])
                
                rpt_po_number = st.text_input("PO Number (Auto Linked or Manual)", value=auto_po)
            
            with c_header2:
                selected_category = st.selectbox("Equipment Category*", ["Rolling Shutter", "High Speed Door"])
                rpt_visit_num_str = st.selectbox("AMC Visit Sequence*", ["Visit 1 of 4", "Visit 2 of 4", "Visit 3 of 4", "Visit 4 of 4"])

            st.divider()

            with st.form(f"service_report_form_{tech_id}"):
                st.markdown("### General Visit Details & Travel Metrics")
                c_det1, c_det2 = st.columns(2)
                with c_det1:
                    rpt_site_location = st.text_input("Site / Location*", value=auto_address)
                    rpt_service_date = st.date_input("Service Date", value=date.today())
                    rpt_distance = st.number_input("Distance Travelled to Site (KM)*", min_value=0.0, value=10.0, step=0.5)
                with c_det2:
                    rpt_next_due = st.date_input("Next Service Due Date", value=date.today() + pd.Timedelta(days=90))
                    rpt_time_taken = st.number_input("Time Spent on Site (Hours)*", min_value=0.25, value=1.5, step=0.25)

                # Section 1: Equipment Details
                st.markdown("<div class='equipment-box'><h3 class='equipment-title'>1. Equipment Details</h3>", unsafe_allow_html=True)
                eq_col1, eq_col2, eq_col3, eq_col4, eq_col5 = st.columns([3, 2, 2, 1, 2])
                with eq_col1:
                    eq_type = st.selectbox("Equipment Type", EQUIPMENT_DATA[selected_category]["types"])
                with eq_col2:
                    eq_make_model = st.text_input("Make / Model", placeholder="e.g. Sidharth / Standard")
                with eq_col3:
                    eq_size = st.text_input("Door Size (W x H)", placeholder="e.g. 4000x4500 mm")
                with eq_col4:
                    eq_qty = st.number_input("Qty", min_value=1, value=1)
                with eq_col5:
                    eq_condition = st.selectbox("Condition", ["Good", "Requires Repair", "Critical", "Replaced"])
                st.markdown("</div>", unsafe_allow_html=True)

                # Section 2: Preventive Maintenance Checklist
                st.markdown(f"### 2. Preventive Maintenance Checklist ({selected_category})")
                
                checklist_results = {}
                checklist_items = EQUIPMENT_DATA[selected_category]["checklist"]
                
                for idx, point in enumerate(checklist_items, 1):
                    col_num, col_point, col_status, col_remark = st.columns([0.5, 4.0, 3.5, 4.0])
                    with col_num:
                        st.write(f"**{idx}.**")
                    with col_point:
                        st.write(point)
                    with col_status:
                        status = st.radio("Status", ["Satisfactory", "Repaired On-Site", "Action Required", "Not Applicable"], horizontal=False, key=f"check_{selected_category}_{idx}", label_visibility="collapsed")
                    with col_remark:
                        remark = st.text_input("Remarks", placeholder="Action taken / Remark", key=f"rem_{selected_category}_{idx}", label_visibility="collapsed")
                    
                    checklist_results[f"Q{idx}"] = {
                        "choice": status, 
                        "remark": remark.strip() if remark.strip() else "N/A"
                    }
                    st.divider()

                # Section 3: Work Execution & Site Media
                st.markdown("### 3. Work Done, Site Photo & Obstacles")
                rpt_work_done = st.text_area("Detailed Action Taken / Work Done*", placeholder="Describe parts replaced, adjustments made, greasing performed...")
                
                media_col1, media_col2 = st.columns(2)
                with media_col1:
                    site_photo_file = st.file_uploader("📷 Upload Site Photo", type=["jpg", "jpeg", "png"], key=f"uploader_{selected_job_id}")
                
                with media_col2:
                    problems_faced_input = st.text_area("⚠️ Problems / Challenges Faced", placeholder="e.g. Power supply delay, inaccessible high height...", key=f"problems_{selected_job_id}")

                st.divider()

                # Section 4: General Remarks
                st.markdown("### 4. General Remarks / Client Recommendations")
                rpt_remarks = st.text_area("General Remarks*", placeholder="Overall observations...")

                submit_report = st.form_submit_button("Submit Final Service Report")
                
                if submit_report:
                    if not rpt_site_location or not rpt_remarks or not rpt_work_done:
                        st.error("⚠️ Please fill in all required fields marked with *")
                    else:
                        try:
                            local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                            submit_time_str = datetime.now(local_tz).strftime("%Y-%m-%d %I:%M %p")
                        except Exception:
                            submit_time_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

                        photo_filename = site_photo_file.name if site_photo_file is not None else "No Photo Uploaded"

                        report_entry = {
                            "Report_ID": f"RPT-{len(st.session_state.service_reports_db) + 1001}",
                            "Job_ID": selected_job_id,
                            "Tech_ID": tech_id,
                            "Tech_Name": tech_name,
                            "Client_Name": auto_client_name,
                            "PO_Number": rpt_po_number,
                            "Site_Location": rpt_site_location,
                            "AMC_Contract_No": selected_contract_no,
                            "Category": selected_category,
                            "Equipment_Type": eq_type,
                            "Make_Model": eq_make_model,
                            "Door_Size": eq_size,
                            "Qty": str(eq_qty),
                            "Condition": eq_condition,
                            "Checklist_Data": "Stored in Q1-Q18 columns",
                            "Service_Date": str(rpt_service_date),
                            "Visit_Number": rpt_visit_num_str,
                            "Next_Service_Due_Date": str(rpt_next_due),
                            "Distance_Travelled_KM": float(rpt_distance),
                            "Time_Taken_Hours": float(rpt_time_taken),
                            "Work_Done_Details": rpt_work_done,
                            "Site_Photo": photo_filename,
                            "Problems_Faced": problems_faced_input.strip() if problems_faced_input.strip() else "None",
                            "Remarks": rpt_remarks,
                            "Submitted_At": submit_time_str
                        }

                        for idx in range(1, 19):
                            q_key = f"Q{idx}"
                            if q_key in checklist_results:
                                report_entry[f"Q{idx}_Choice"] = checklist_results[q_key]["choice"]
                                report_entry[f"Q{idx}_Remark"] = checklist_results[q_key]["remark"]
                            else:
                                report_entry[f"Q{idx}_Choice"] = "N/A"
                                report_entry[f"Q{idx}_Remark"] = "N/A"

                        valid_columns = load_sheet_data("ServiceReports").columns.tolist()
                        new_row_df = pd.DataFrame([report_entry])[valid_columns]

                        st.session_state.service_reports_db = pd.concat([st.session_state.service_reports_db[valid_columns], new_row_df], ignore_index=True)
                        save_sheet_data(st.session_state.service_reports_db, "ServiceReports")
                        
                        st.session_state.jobs_db.loc[st.session_state.jobs_db["Job_ID"] == selected_job_id, "Status"] = "Completed"
                        save_sheet_data(st.session_state.jobs_db, "Jobs")
                        
                        st.session_state.selected_job_for_report = None
                        st.toast(f"✅ Service report submitted for {selected_job_id}!", icon="📄")
                        st.rerun()

    # TAB 3: Broadcast Location
    with tech_tab3:
        st.subheader("Broadcast Live Location & Next Target")
        curr_rec = st.session_state.tech_status_db[st.session_state.tech_status_db["Tech_ID"].astype(str) == tech_id]
        
        c_city = str(curr_rec["Current_City"].values[0]) if not curr_rec.empty and "Current_City" in curr_rec.columns else ""
        c_pin = str(curr_rec["Current_Pincode"].values[0]) if not curr_rec.empty and "Current_Pincode" in curr_rec.columns else ""
        c_status_raw = str(curr_rec["Current_Status"].values[0]).strip().title() if not curr_rec.empty and "Current_Status" in curr_rec.columns else "Available"
        n_city = str(curr_rec["Next_City"].values[0]) if not curr_rec.empty and "Next_City" in curr_rec.columns else ""
        n_pin = str(curr_rec["Next_Pincode"].values[0]) if not curr_rec.empty and "Next_Pincode" in curr_rec.columns else ""
        eta_val = str(curr_rec["ETA"].values[0]) if not curr_rec.empty and "ETA" in curr_rec.columns else ""

        with st.form(f"broadcast_location_form_{tech_id}"):
            c1, c2 = st.columns(2)
            with c1:
                input_curr_city = st.text_input("Current City", value=c_city)
                input_curr_pin = st.text_input("Current Pin Code", value=c_pin, max_chars=6)
                status_options = ["Available", "On Site", "In Transit"]
                selected_idx = status_options.index(c_status_raw) if c_status_raw in status_options else 0
                input_status = st.radio("Current Activity", status_options, index=selected_idx, horizontal=True)
                
            with c2:
                input_next_city = st.text_input("Next Target City", value=n_city)
                input_next_pin = st.text_input("Next Target Pin Code", value=n_pin, max_chars=6)
                input_eta = st.text_input("ETA Arrival Time", value=eta_val)
                
            if st.form_submit_button("Broadcast Location Update"):
                try:
                    local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                    now_str = datetime.now(local_tz).strftime("%I:%M %p")
                except Exception:
                    now_str = datetime.now().strftime("%I:%M %p")
                
                if tech_id in st.session_state.tech_status_db["Tech_ID"].astype(str).values:
                    st.session_state.tech_status_db.loc[
                        st.session_state.tech_status_db["Tech_ID"].astype(str) == tech_id,
                        ["Current_City", "Current_Pincode", "Current_Status", "Next_City", "Next_Pincode", "ETA", "Last_Updated"]
                    ] = [input_curr_city, input_curr_pin, input_status, input_next_city, input_next_pin, input_eta, now_str]
                else:
                    new_row = {"Tech_ID": tech_id, "Current_City": input_curr_city, "Current_Pincode": input_curr_pin, "Current_Status": input_status, "Next_City": input_next_city, "Next_Pincode": input_next_pin, "ETA": input_eta, "Last_Updated": now_str}
                    st.session_state.tech_status_db = pd.concat([st.session_state.tech_status_db, pd.DataFrame([new_row])], ignore_index=True)
                
                save_sheet_data(st.session_state.tech_status_db, "TechStatus")
                st.toast(f"📍 Location Broadcast Updated at {now_str}!", icon="✅")
                st.rerun()

    # TAB 4: Technician Individual Reports & Progress History
    with tech_tab4:
        st.subheader("📈 My Personal Performance Summary")
        reports_df = st.session_state.service_reports_db
        
        if not reports_df.empty and "Tech_ID" in reports_df.columns:
            my_reports = reports_df[reports_df["Tech_ID"].astype(str) == tech_id]
            
            if not my_reports.empty:
                # Safely extract Series or fallback to empty Series
                km_series = my_reports["Distance_Travelled_KM"] if "Distance_Travelled_KM" in my_reports.columns else pd.Series(dtype=float)
                hrs_series = my_reports["Time_Taken_Hours"] if "Time_Taken_Hours" in my_reports.columns else pd.Series(dtype=float)

                sites_visited = len(my_reports)
                tot_km = pd.to_numeric(km_series, errors='coerce').sum()
                tot_hrs = pd.to_numeric(hrs_series, errors='coerce').sum()

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Sites Visited", sites_visited)
                m2.metric("Total Travelled", f"{tot_km:.1f} KM")
                m3.metric("Time Spent On-Site", f"{tot_hrs:.1f} Hrs")
                m4.metric("Avg Time / Site", f"{(tot_hrs / sites_visited):.1f} Hrs" if sites_visited > 0 else "0 Hrs")
                
                st.divider()
                st.markdown("### Detailed Reports Log")
                st.dataframe(my_reports, use_container_width=True)
            else:
                st.info("📜 No service reports submitted yet.")
        else:
            st.info("📜 No service reports submitted yet.")

# -----------------------------------------------------------------------------
# 8. MANAGER COMMAND DASHBOARD & ANALYTICS
# -----------------------------------------------------------------------------

elif st.session_state.user["Role"] in ["Manager", "Admin"]:
    st.markdown("<h1 style='color: #0F3D7A;'>📡 Dispatch, Progress Analytics & AMC Control Center</h1>", unsafe_allow_html=True)

    # MANAGER NOTIFICATIONS: UPCOMING AMC VISITS
    contracts_df = st.session_state.amc_contracts_db
    if not contracts_df.empty and "Next_Visit_Due" in contracts_df.columns:
        contracts_df["Next_Visit_Due_DT"] = pd.to_datetime(contracts_df["Next_Visit_Due"], errors="coerce")
        today_dt = pd.Timestamp(date.today())
        upcoming_due = contracts_df[
            (contracts_df["Next_Visit_Due_DT"] >= today_dt) & 
            (contracts_df["Next_Visit_Due_DT"] <= (today_dt + timedelta(days=7)))
        ]
        
        if not upcoming_due.empty:
            st.warning(f"🔔 **Upcoming AMC Visit Alerts ({len(upcoming_due)} Due in Next 7 Days)**")
            for _, u_row in upcoming_due.iterrows():
                st.caption(f"• **{u_row['Client_Name']}** (Contract: `{u_row['AMC_Contract_No']}`, PO: `{u_row.get('PO_Number','N/A')}`) — Visit Due Date: **{u_row['Next_Visit_Due']}**")
            st.divider()

    mgr_tab1, mgr_tab2, mgr_tab3, mgr_tab4, mgr_tab5 = st.tabs([
        "📊 Progress Reports & Analytics",
        "MAP / Live Radar", 
        "📄 All Service Reports",
        "📅 AMC Contract Manager",
        "➕ Create Task / User"
    ])

    # TAB 1: Filterable Progress Reports & Performance
    with mgr_tab1:
        st.subheader("📈 Technician Field Operations & Travel Progress")
        
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            time_filter = st.selectbox(
                "🗓️ Filter Time Period", 
                ["All Time", "Today", "Weekly (Last 7 Days)", "Monthly (Last 30 Days)", "3 Months", "Yearly"]
            )
        
        tech_users = st.session_state.users_db[st.session_state.users_db["Role"] == "Technician"]
        tech_options = ["All Technicians"] + tech_users["Full_Name"].tolist()
        
        with f_col2:
            tech_filter = st.selectbox("👷 Filter Technician", tech_options)

        all_reports = st.session_state.service_reports_db.copy()
        
        # Apply Filters
        if time_filter != "All Time":
            all_reports = filter_df_by_date_range(all_reports, "Service_Date", time_filter)
            
        if tech_filter != "All Technicians":
            all_reports = all_reports[all_reports["Tech_Name"] == tech_filter]

        st.divider()

       # Aggregate Metrics safely
        tot_visited = len(all_reports)
        
        if not all_reports.empty and "Distance_Travelled_KM" in all_reports.columns:
            all_reports["Distance_Travelled_KM"] = pd.to_numeric(all_reports["Distance_Travelled_KM"], errors='coerce').fillna(0)
            tot_dist = all_reports["Distance_Travelled_KM"].sum()
        else:
            tot_dist = 0.0

        if not all_reports.empty and "Time_Taken_Hours" in all_reports.columns:
            all_reports["Time_Taken_Hours"] = pd.to_numeric(all_reports["Time_Taken_Hours"], errors='coerce').fillna(0)
            tot_time = all_reports["Time_Taken_Hours"].sum()
        else:
            tot_time = 0.0

        st.divider()
        st.markdown("### Technician Summary Table")
        
        if not all_reports.empty and "Tech_Name" in all_reports.columns:
            summary_grp = all_reports.groupby("Tech_Name").agg(
                Sites_Visited=("Report_ID", "count"),
                Total_KM=("Distance_Travelled_KM", "sum"),
                Total_Hours=("Time_Taken_Hours", "sum")
            ).reset_index()
            st.dataframe(summary_grp, use_container_width=True)
        else:
            st.info("No visit records matching selected criteria.")

    # TAB 2: MAP / Live Radar
    with mgr_tab2:
        st.subheader("Technician Fleet Live Radar")
        full_radar = pd.merge(st.session_state.tech_status_db, st.session_state.users_db[["User_ID", "Full_Name"]], left_on="Tech_ID", right_on="User_ID", how="left")
        st.dataframe(full_radar, use_container_width=True)
        
        st.divider()
        st.subheader("All Active Work Orders")
        st.dataframe(st.session_state.jobs_db, use_container_width=True)

    # TAB 3: Service Reports Log
    with mgr_tab3:
        st.subheader("📋 Field Service Visit Reports Log")
        st.dataframe(st.session_state.service_reports_db, use_container_width=True)

    # TAB 4: Contract Manager with PO Number & Next Visit Due
    with mgr_tab4:
        st.subheader("🗓️ AMC Client Contracts & PO Number Management")
        st.dataframe(st.session_state.amc_contracts_db, use_container_width=True)
        st.divider()
        st.markdown("### ✏️ Register / Update AMC Contract & PO Details")
        
        with st.form("edit_amc_contract_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                contract_no = st.text_input("AMC Contract Number*", placeholder="e.g. AMC-2026-88").strip()
                po_number = st.text_input("PO Number*", placeholder="e.g. PO-998877").strip()
                c_client_name = st.text_input("Client Name*", placeholder="e.g. Apex Industries").strip()
                visits_allowed = st.selectbox("Annual Allowed Visits Limit*", [2, 3, 4], index=2)
            with col_c2:
                contract_start = st.date_input("Contract Start Date", value=date.today())
                contract_end = st.date_input("Contract End Date", value=date.today() + pd.Timedelta(days=365))
                next_visit_due = st.date_input("Next Scheduled Visit Due*", value=date.today() + pd.Timedelta(days=90))
            
            if st.form_submit_button("Save / Update AMC Contract"):
                if not contract_no or not c_client_name or not po_number:
                    st.error("⚠️ Contract Number, PO Number, and Client Name are required.")
                else:
                    contracts_df = st.session_state.amc_contracts_db
                    if not contracts_df.empty and contract_no in contracts_df["AMC_Contract_No"].astype(str).values:
                        st.session_state.amc_contracts_db.loc[
                            st.session_state.amc_contracts_db["AMC_Contract_No"].astype(str) == contract_no,
                            ["PO_Number", "Client_Name", "Start_Date", "End_Date", "Allowed_Visits", "Next_Visit_Due"]
                        ] = [po_number, c_client_name, str(contract_start), str(contract_end), visits_allowed, str(next_visit_due)]
                    else:
                        new_contract = {
                            "AMC_Contract_No": contract_no,
                            "PO_Number": po_number,
                            "Client_Name": c_client_name,
                            "Start_Date": str(contract_start),
                            "End_Date": str(contract_end),
                            "Allowed_Visits": visits_allowed,
                            "Next_Visit_Due": str(next_visit_due)
                        }
                        st.session_state.amc_contracts_db = pd.concat([st.session_state.amc_contracts_db, pd.DataFrame([new_contract])], ignore_index=True)
                    
                    save_sheet_data(st.session_state.amc_contracts_db, "AMCContracts")
                    st.toast(f"✅ Contract {contract_no} with PO {po_number} saved!")
                    st.rerun()

    # TAB 5: Create Tasks/Users
    with mgr_tab5:
        col_mgr_a, col_mgr_b = st.columns(2)
        
        with col_mgr_a:
            st.subheader("Dispatch New Task")
            with st.form("new_job_form"):
                j_id = f"JOB-{len(st.session_state.jobs_db) + 101}"
                client_name = st.text_input("Client Name")
                client_phone = st.text_input("Client Phone")
                address = st.text_input("Site Address")
                city = st.text_input("City")
                pincode = st.text_input("Pin Code", max_chars=6)
                issue = st.text_area("Service Notes")
                
                tech_list = st.session_state.users_db[st.session_state.users_db["Role"] == "Technician"]
                assigned_tech = st.selectbox(
                    "Assign Technician", 
                    options=tech_list["User_ID"].tolist(), 
                    format_func=lambda x: f"{x} - {tech_list[tech_list['User_ID']==x]['Full_Name'].values[0]}"
                )
                
                st.markdown("**Scheduled Date & Time**")
                sched_col1, sched_col2 = st.columns(2)
                with sched_col1:
                    sched_date = st.date_input("Scheduled Date", min_value=date.today(), value=date.today())
                with sched_col2:
                    sched_time = st.time_input("Scheduled Time", value=time(14, 0))
                
                if st.form_submit_button("Task Created"):
                    selected_datetime = datetime.combine(sched_date, sched_time)
                    if selected_datetime < datetime.now():
                        st.error("⚠️ Cannot schedule a task for a time that has already passed today.")
                    else:
                        scheduled_time_str = f"{sched_date.strftime('%d-%b-%Y')} at {sched_time.strftime('%I:%M %p')}"
                        new_job_entry = {
                            "Job_ID": j_id, "Assigned_Tech_ID": str(assigned_tech), "Client_Name": client_name,
                            "Client_Phone": client_phone, "Address": address, "City": city, "Pincode": pincode,
                            "Issue_Description": issue, "Status": "Assigned", "Scheduled_Time": scheduled_time_str
                        }
                        st.session_state.jobs_db = pd.concat([st.session_state.jobs_db, pd.DataFrame([new_job_entry])], ignore_index=True)
                        save_sheet_data(st.session_state.jobs_db, "Jobs")
                        st.toast(f"✅ Task Created ({j_id})!")
                        st.rerun()

        with col_mgr_b:
            st.subheader("Register System User")
            if st.session_state.user.get("Role") != "Admin":
                st.info("🔒 System User Registration is restricted. It can be created by Admin only.")
            else:
                with st.form("add_user_form"):
                    new_uid = st.text_input("User ID (e.g. TECH03)").strip().upper()
                    new_name = st.text_input("Full Name")
                    new_role = st.selectbox("Role", ["Technician", "Manager", "Admin"])
                    new_pass = st.text_input("Password", type="password").strip()
                    
                    if st.form_submit_button("Create Account"):
                        if new_uid in st.session_state.users_db["User_ID"].astype(str).values:
                            st.error("User ID already exists!")
                        else:
                            user_entry = {"User_ID": new_uid, "Full_Name": new_name, "Role": new_role, "Password": new_pass}
                            st.session_state.users_db = pd.concat([st.session_state.users_db, pd.DataFrame([user_entry])], ignore_index=True)
                            save_sheet_data(st.session_state.users_db, "Users")
                            st.toast(f"✅ Account for {new_name} created!")
                            st.rerun()
