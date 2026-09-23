import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import zoneinfo
import urllib.parse
import os
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------------------------------------------------------
# 0. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AMC Tracker Portal", 
    page_icon="🛠️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 1. HELPER FUNCTIONS & LOGO RESOLUTION
# -----------------------------------------------------------------------------

def get_logo_path():
    for name in ["Company Logo.jpeg", "Company Logo.png", "Company Logo.jpg", "logo.png"]:
        if os.path.exists(name):
            return name
    return None

def make_google_maps_link(address, city, pincode=""):
    query = urllib.parse.quote(f"{address}, {city} {pincode}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={query}"

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
# 2. GOOGLE SHEETS CONNECTION
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

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# -----------------------------------------------------------------------------
# 3. CHECKLIST DATA CONFIGURATION
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
# 4. BRANDED UI STYLING
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    .stApp { background-color: #F4F6F9 !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #0F3D7A !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #0F3D7A !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .sidebar-logo-sub { color: #00A859; font-weight: 800; font-size: 0.85rem; letter-spacing: 1.5px; text-align: center; margin-top: 4px; }
    
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 30px 28px 24px 28px !important;
        box-shadow: 0px 8px 20px rgba(15, 61, 122, 0.08) !important;
        max-width: 420px !important;
        margin: 20px auto !important;
    }

    .login-subtitle {
        text-align: center; color: #556B82; font-size: 0.95rem; font-weight: 700;
        letter-spacing: 0.5px; margin-top: 4px; margin-bottom: 20px; text-transform: uppercase;
    }

    .stTextInput > label { color: #0F3D7A !important; font-weight: 700 !important; font-size: 0.92rem !important; }

    div[data-testid="stFormSubmitButton"] > button {
        background-color: #00A859 !important; color: #FFFFFF !important;
        border-radius: 8px !important; font-weight: 800 !important; font-size: 0.98rem !important;
        height: 44px !important; border: none !important; width: 100% !important;
        margin-top: 10px !important; box-shadow: 0 4px 10px rgba(0, 168, 89, 0.25) !important;
    }
    
    div[data-testid="stFormSubmitButton"] > button:hover { background-color: #008F4C !important; }

    .equipment-box {
        background-color: #FFFFFF; border-left: 5px solid #0F3D7A;
        border-radius: 8px; padding: 12px 18px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .equipment-title { color: #0F3D7A !important; font-weight: 700; margin: 0 0 10px 0; font-size: 1.25rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. AUTHENTICATION & LOGIN FORM
# -----------------------------------------------------------------------------

def render_login_form():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    
    with col2:
        with st.form("main_login_form", clear_on_submit=False):
            logo_path = get_logo_path()
            if logo_path:
                l_col1, l_col2, l_col3 = st.columns([0.1, 3.8, 0.1])
                with l_col2:
                    st.image(logo_path, use_container_width=True)
            else:
                st.markdown("<h2 style='text-align:center; color:#0F3D7A; font-weight:800; margin-bottom:5px;'>SIDHARTH</h2><p style='text-align:center; color:#0F3D7A; font-size:0.85rem; font-weight:700; letter-spacing:1px; margin-top:-10px;'>SHUTTER & AUTOMATION</p>", unsafe_allow_html=True)

            st.markdown("<p class='login-subtitle'>AMC Tracker Portal</p>", unsafe_allow_html=True)

            user_id_input = st.text_input("Username / Name", placeholder="Enter User Name", key="login_userid")

            chk_col1, chk_col2 = st.columns(2)
            with chk_col1:
                show_password = st.checkbox("Show Password", key="show_pwd_toggle")
            with chk_col2:
                st.checkbox("Remember Me", key="remember_me_toggle")

            pwd_type = "text" if show_password else "password"
            password_input = st.text_input("Password / PIN", type=pwd_type, placeholder="Enter password", key="login_password")

            submit_button = st.form_submit_button("🔑 LOGIN TO DASHBOARD", use_container_width=True)

            if submit_button:
                u_val = user_id_input.strip() if user_id_input else ""
                p_val = password_input.strip() if password_input else ""
                
                if not u_val or not p_val:
                    st.warning("⚠️ Please enter both Username and Password.")
                else:
                    users_df = st.session_state.users_db
                    matched_user = users_df[
                        (
                            (users_df["User_ID"].astype(str).str.strip().str.lower() == u_val.lower()) |
                            (users_df["Full_Name"].astype(str).str.strip().str.lower() == u_val.lower())
                        ) & 
                        (users_df["Password"].astype(str).str.strip() == p_val)
                    ]
                    
                    if not matched_user.empty:
                        user_info = matched_user.iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["user_id"] = str(user_info["User_ID"])
                        st.session_state["user_name"] = str(user_info["Full_Name"])
                        st.session_state["user_role"] = str(user_info["Role"])
                        st.session_state["user"] = {
                            "User_ID": str(user_info["User_ID"]),
                            "Full_Name": str(user_info["Full_Name"]),
                            "Role": str(user_info["Role"])
                        }
                        st.success(f"Welcome back, {user_info['Full_Name']}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Username or Password. Please try again.")

if not st.session_state.get("authenticated", False):
    render_login_form()
    st.stop()

# -----------------------------------------------------------------------------
# 6. SIDEBAR NAV & USER INFO
# -----------------------------------------------------------------------------

with st.sidebar:
    logo_path = get_logo_path()
    if logo_path:
        sb_c1, sb_c2, sb_c3 = st.columns([1, 2, 1])
        with sb_c2:
            st.image(logo_path, width=140)
    else:
        st.markdown("<h3 style='color: #0F3D7A; text-align:center;'>⚙️ SIDHARTH</h3>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-logo-sub'>AMC TRACKER PORTAL</div>", unsafe_allow_html=True)
    st.divider()

    logged_name = st.session_state.get("user_name", "User")
    logged_role = st.session_state.get("user_role", "Technician")

    st.markdown(f"**Logged User:** {logged_name}")
    st.markdown(f"**Role:** `{logged_role}`")
    
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.user_role = None
        st.rerun()

# -----------------------------------------------------------------------------
# 7. TECHNICIAN DASHBOARD
# -----------------------------------------------------------------------------

if logged_role == "Technician":
    tech_id = str(st.session_state.get("user_id", ""))
    tech_name = str(st.session_state.get("user_name", ""))

    st.markdown(f"<h1>🛠️ AMC Tracker Portal — <span style='color:#64748B;'>{tech_name}</span></h1>", unsafe_allow_html=True)

    tech_tab1, tech_tab2, tech_tab3, tech_tab4 = st.tabs([
        "📋 Assigned Work Orders", 
        "📝 Submit Service Report",
        "📍 Update Live Status", 
        "📈 My Reports & Progress History"
    ])

    # TAB 1: Assigned Work Orders
    with tech_tab1:
        st.subheader("📋 Your Assigned Field Tasks")
        my_jobs = st.session_state.jobs_db[st.session_state.jobs_db["Assigned_Tech_ID"].astype(str) == tech_id]
        
        if my_jobs.empty:
            st.info("🎉 No active or pending work orders assigned to you.")
        else:
            for _, job in my_jobs.iterrows():
                with st.expander(f"📍 {job['Job_ID']} — {job['Client_Name']} ({job['Status']})"):
                    st.write(f"**Address:** {job['Address']}, {job['City']} - {job['Pincode']}")
                    st.write(f"**Issue Description:** {job['Issue_Description']}")
                    st.write(f"**Scheduled Time:** {job.get('Scheduled_Time', 'N/A')}")
                    
                    maps_url = make_google_maps_link(job['Address'], job['City'], job['Pincode'])
                    st.markdown(f"[🗺️ Open Directions in Google Maps]({maps_url})", unsafe_allow_html=True)
                    
                    if job['Status'] != "Completed":
                        if st.button(f"Start Service Report for {job['Job_ID']}", key=f"start_{job['Job_ID']}"):
                            st.session_state.selected_job_for_report = job['Job_ID']
                            st.toast(f"Selected {job['Job_ID']}. Switch to 'Submit Service Report' tab.", icon="📝")

    # TAB 2: Service Report Form
    with tech_tab2:
        st.subheader("📝 Submit Field Service Visit Report")
        
        pending_tech_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"].astype(str) == tech_id) & 
            (st.session_state.jobs_db["Status"] != "Completed")
        ]
        
        if pending_tech_jobs.empty:
            st.info("🎉 No pending tasks found for you to submit a report for.")
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

                st.markdown("### 3. Work Done, Site Photo & Obstacles")
                rpt_work_done = st.text_area("Detailed Action Taken / Work Done*", placeholder="Describe parts replaced, adjustments made, greasing performed...")
                
                media_col1, media_col2 = st.columns(2)
                with media_col1:
                    site_photo_file = st.file_uploader("📷 Upload Site Photo", type=["jpg", "jpeg", "png"], key=f"uploader_{selected_job_id}")
                
                with media_col2:
                    problems_faced_input = st.text_area("⚠️ Problems / Challenges Faced", placeholder="e.g. Power supply delay...", key=f"problems_{selected_job_id}")

                st.divider()

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
                input_status = st.radio("Current Activity Status", status_options, index=selected_idx, horizontal=True)
                
            with c2:
                input_next_city = st.text_input("Next Target City", value=n_city)
                input_next_pin = st.text_input("Next Target Pin Code", value=n_pin, max_chars=6)
                input_eta = st.text_input("Estimated Time of Arrival (ETA)", value=eta_val, placeholder="e.g. 02:30 PM")

            submit_status = st.form_submit_button("📡 Broadcast My Status")
            
            if submit_status:
                try:
                    local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                    now_str = datetime.now(local_tz).strftime("%Y-%m-%d %I:%M %p")
                except Exception:
                    now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

                status_entry = {
                    "Tech_ID": tech_id,
                    "Current_City": input_curr_city,
                    "Current_Pincode": input_curr_pin,
                    "Current_Status": input_status,
                    "Next_City": input_next_city,
                    "Next_Pincode": input_next_pin,
                    "ETA": input_eta,
                    "Last_Updated": now_str
                }
                
                # Check if technician status already exists, then update or append
                df_ts = st.session_state.tech_status_db
                if tech_id in df_ts["Tech_ID"].astype(str).values:
                    idx = df_ts[df_ts["Tech_ID"].astype(str) == tech_id].index[0]
                    for k, v in status_entry.items():
                        df_ts.loc[idx, k] = v
                else:
                    df_ts = pd.concat([df_ts, pd.DataFrame([status_entry])], ignore_index=True)
                
                st.session_state.tech_status_db = df_ts
                save_sheet_data(df_ts, "TechStatus")
                st.success("✅ Location & Status broadcasted successfully!")

    # TAB 4: Reports History
    with tech_tab4:
        st.subheader("📈 My Submitted Reports & History")
        my_reports = st.session_state.service_reports_db[st.session_state.service_reports_db["Tech_ID"].astype(str) == tech_id]
        
        if my_reports.empty:
            st.info("No service reports submitted yet.")
        else:
            st.dataframe(my_reports, use_container_width=True)

# Admin Dashboard fallback
else:
    st.title("📊 AMC Tracker Portal — Admin View")
    st.write("Welcome to Admin Dashboard! All service reports and live technician tracking are active.")
    st.subheader("Summary of Service Reports")
    st.dataframe(st.session_state.service_reports_db, use_container_width=True)
