import streamlit as st
import pandas as pd
from datetime import datetime, date
import zoneinfo
import urllib.parse
import os
import io
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & BASE STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AMC Annual Maintenance Tracker", 
    page_icon="🛠️", 
    layout="wide"
)

st.markdown("""
<style>
    .login-container { 
        border: 2px solid #1565C0; 
        border-radius: 12px; 
        padding: 24px; 
        background-color: #FFFFFF;
        max-width: 400px; 
        margin: 40px auto; 
    }
    .section-banner {
        background-color: #F1F5F9;
        border-left: 6px solid #1565C0;
        border-radius: 4px;
        padding: 10px 16px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .section-banner-title {
        color: #0F172A !important;
        font-weight: 700;
        font-size: 1.15rem;
        margin: 0;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. GOOGLE SHEETS & DRIVE CONNECTION
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
        "Report_ID", "Job_ID", "Tech_ID", "Tech_Name", "Client_Name", "Site_Location", 
        "AMC_Contract_No", "Category", "Equipment_Type", "Make_Model", "Door_Size", "Qty", 
        "Condition", "Checklist_Data", "Service_Date", "Visit_Number", "Next_Service_Due_Date", 
        "Remarks", "Submitted_At", "Physical_Sheet_URL", "Site_Photos_URLs"
    ]
    for i in range(1, 19):
        service_report_cols.extend([f"Q{i}_Choice", f"Q{i}_Remark"])

    default_columns = {
        "Users": ["User_ID", "Full_Name", "Role", "Password"],
        "Jobs": ["Job_ID", "Assigned_Tech_ID", "Client_Name", "Client_Phone", "Address", "City", "Pincode", "Issue_Description", "Status", "Scheduled_Time"],
        "TechStatus": ["Tech_ID", "Current_City", "Current_Pincode", "Current_Status", "Next_City", "Next_Pincode", "ETA", "Last_Updated"],
        "ServiceReports": service_report_cols,
        "AMCContracts": ["AMC_Contract_No", "Client_Name", "Start_Date", "End_Date", "Allowed_Visits"]
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

# Session State Persistence Initializations
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
# 3. CATEGORIZED EQUIPMENT CONFIGURATION
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
    },
    "Sectional Door": {
        "types": [
            "Industrial Sectional Door",
            "Residential Overhead Door",
            "Insulated Sectional Door",
            "Vision / Full-Glazed Door",
            "Other"
        ],
        "checklist": [
            "Door Panels (Damage, Alignment, Cracks)",
            "Torsion / Extension Spring Tension & Condition",
            "Spring Anti-Drop Safety Device",
            "Steel Lifting Cables (Fraying, Wear, Tension)",
            "Cable Failure Safety Device (Bottom Bracket)",
            "Side Vertical & Horizontal Guide Tracks",
            "Track Rollers, Hinges & Shaft Bearings",
            "Drive Motor Unit & Gearbox Condition",
            "Control Panel & Electrical Wiring",
            "Limit Switches (Open / Close Stop Positions)",
            "Safety Edge / Safety Light Curtains",
            "Infrared Safety Photocells",
            "Remote Control & Push Button Switches",
            "Manual Emergency Release (Chain / Declutch)",
            "Rubber Bottom, Side & Top Weather Seals",
            "Lubrication (Springs, Bearings, Rollers, Hinges)",
            "Smooth Operation, Noise & Vibration Check",
            "Final Functional & Auto-Reverse Safety Test"
        ]
    },
    "Automatic Gate Barrier": {
        "types": [
            "Electromechanical Gate Barrier",
            "Hydraulic Gate Barrier",
            "Articulated Arm Barrier",
            "Other"
        ],
        "checklist": [
            "Barrier Housing / Cabinet (Physical Condition & Lock)",
            "Barrier Boom Arm Condition & Alignment",
            "Balancing Spring Tension & Adjustment",
            "Motor & Gearbox / Hydraulic Pump Unit",
            "Drive Lever, Mechanical Stops & Bearings",
            "Control Panel & Microprocessor Board Settings",
            "Electrical Wiring, Terminations & Grounding",
            "Limit Switches (Open / Close Positioning)",
            "Inductive Loop Detector & Ground Loops",
            "Safety Photocells / Light Beams",
            "Boom Rubber Safety Edge / LED Warning Lights",
            "Access Control Integration (RFID / Card Reader / UHF)",
            "Push Button Station & Remote Keyfobs",
            "Manual Emergency Release Key Mechanism",
            "Lubrication of Pivot Joints & Internal Linkages",
            "Anchor Bolts & Foundation Stability",
            "Abnormal Noise, Vibration & Slowdown Speed",
            "Final Functional Test & Safety Auto-Reverse Check"
        ]
    },
    "Sliding Gate": {
        "types": [
            "Tracked Sliding Gate",
            "Cantilever Sliding Gate",
            "Telescopic Sliding Gate",
            "Heavy Industrial Sliding Gate",
            "Other"
        ],
        "checklist": [
            "Gate Leaf Physical Condition & Frame Structural Integrity",
            "Bottom Track Rail / Cantilever Carriage Wheels Condition",
            "Top Guide Rollers & Guide Channel Alignment",
            "Gear Rack & Pinion Tooth Engagement & Alignment",
            "Sliding Gate Motor Unit & Oil Level / Gearbox",
            "Mechanical Physical End Stops (Open & Close Positions)",
            "Limit Switches / Magnetic Limit Sensors",
            "Control Board Wiring, Fuses & Earth Connections",
            "Infrared Safety Photocells Alignment & Cleanliness",
            "Safety Edge Bumper & Obstacle Sensitivity Force Adjustment",
            "Flashing Warning Lamp & Audible Buzzer Operation",
            "Push Button Station, Key Switch & Keyfob Operation",
            "Access Control Integration (GSM / Intercom / Card Reader)",
            "Manual Key Release Mechanism & Declutch Operation",
            "Greasing of Rack, Wheels, Rollers & Bearings",
            "Foundation Bolts & Motor Mounting Base Stability",
            "Gate Travel Smoothness, Noise & Vibration Check",
            "Final Functional Test & Safety Auto-Reverse Test"
        ]
    }
}

if "active_category" not in st.session_state:
    st.session_state.active_category = list(EQUIPMENT_DATA.keys())[0]

# -----------------------------------------------------------------------------
# 4. HELPER FUNCTIONS & GOOGLE DRIVE UPLOADER
# -----------------------------------------------------------------------------
def upload_photos_to_drive(file_list, folder_name="AMC_Site_Photos"):
    """Uploads files to a target Google Drive folder and returns direct share links."""
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    drive_service = build("drive", "v3", credentials=credentials)

    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    folders = results.get("files", [])

    if folders:
        folder_id = folders[0]["id"]
    else:
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
        folder_id = folder.get("id")

    uploaded_links = []

    for file in file_list:
        file_metadata = {
            "name": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.name}",
            "parents": [folder_id]
        }
        media = MediaIoBaseUpload(io.BytesIO(file.getvalue()), mimetype=file.type, resumable=True)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        drive_service.permissions().create(
            fileId=uploaded_file.get("id"),
            body={"role": "reader", "type": "anyone"}
        ).execute()

        uploaded_links.append(uploaded_file.get("webViewLink"))

    return uploaded_links

def make_google_maps_link(address, city, pincode=""):
    query = urllib.parse.quote(f"{address}, {city} {pincode}".strip())
    return f"https://www.google.com/maps/search/?api=1&query={query}"

def get_logo_path():
    for name in ["Company Logo.jpeg", "Company Logo.png", "Company Logo.jpg"]:
        if os.path.exists(name):
            return name
    return None

@st.dialog("📊 Task Progress Summary")
def show_task_summary_popup(tech_name, total_cnt, completed_cnt, pending_cnt):
    st.write(f"### Performance Overview for **{tech_name}**")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Assigned", total_cnt)
    col2.metric("Completed", completed_cnt, delta=f"{completed_cnt} Done", delta_color="normal")
    col3.metric("Pending", pending_cnt, delta=f"-{pending_cnt} Remaining", delta_color="inverse")
    
    st.divider()
    if total_cnt > 0:
        completion_pct = int((completed_cnt / total_cnt) * 100)
        st.write(f"**Completion Rate:** {completion_pct}%")
        st.progress(completion_pct / 100)
    else:
        st.info("No work orders recorded for this technician.")

# -----------------------------------------------------------------------------
# 5. LOGIN SCREEN
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    logo_path = get_logo_path()
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #1565C0; margin:0;'>⚙️ SIDHARTH</h2>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align:center; color:#1565C0; margin-bottom: 20px;'>AMC Tracker</h3>", unsafe_allow_html=True)
    user_id_input = st.text_input("User ID", placeholder="e.g. TECH01").strip().upper()
    password_input = st.text_input("Password", type="password", placeholder="Enter password").strip()
    
    if st.button("Sign In", type="primary", use_container_width=True):
        user_df = st.session_state.users_db
        match = user_df[(user_df["User_ID"].astype(str) == user_id_input) & (user_df["Password"].astype(str) == password_input)]
        if not match.empty:
            st.session_state.user = match.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("❌ Invalid User ID or Password")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -----------------------------------------------------------------------------
# 6. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    logo_path = get_logo_path()
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h3 style='color: #1565C0; text-align:center;'>⚙️ SIDHARTH</h3>", unsafe_allow_html=True)
    st.markdown("<div style='color: #10B981; font-weight: 800; font-size: 0.95rem; text-align: center;'>AMC TRACKER</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"**Logged User:** {st.session_state.user['Full_Name']}")
    st.markdown(f"**Role:** `{st.session_state.user['Role']}`")
    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# -----------------------------------------------------------------------------
# 7. MAIN TECHNICIAN DASHBOARD
# -----------------------------------------------------------------------------
if st.session_state.user["Role"] == "Technician":
    tech_id = str(st.session_state.user["User_ID"])
    tech_name = st.session_state.user["Full_Name"]

    st.markdown(f"<h1>🛠️ Technician Dashboard — <span style='color:#64748B;'>{tech_name}</span></h1>", unsafe_allow_html=True)

    all_tech_jobs = st.session_state.jobs_db[st.session_state.jobs_db["Assigned_Tech_ID"].astype(str) == tech_id]
    total_tasks = len(all_tech_jobs)
    completed_tasks = len(all_tech_jobs[all_tech_jobs["Status"] == "Completed"])
    pending_tasks = total_tasks - completed_tasks

    summary_col1, summary_col2 = st.columns([3, 1])
    with summary_col2:
        if st.button("📊 View Task Summary"):
            show_task_summary_popup(tech_name, total_tasks, completed_tasks, pending_tasks)

    tech_tab1, tech_tab2, tech_tab3, tech_tab4 = st.tabs([
        "📋 Assigned Work Orders", 
        "📝 Submit Client Service Report",
        "📍 Update Status & Destination", 
        "📜 Service History"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Assigned Work Orders
    # -------------------------------------------------------------------------
    with tech_tab1:
        st.subheader("Assigned Maintenance Tasks")
        tech_jobs = all_tech_jobs[all_tech_jobs["Status"] != "Completed"]
        
        if tech_jobs.empty:
            st.info("🎉 No pending maintenance visits assigned to you.")
        else:
            for idx, job in tech_jobs.iterrows():
                pincode_str = f" - {job['Pincode']}" if "Pincode" in job and pd.notna(job["Pincode"]) else ""
                st.markdown(f"#### 🔵 [{job['Job_ID']}] {job['Client_Name']} — {job['City']}{pincode_str} (`{job['Status']}`)")
                col_a, col_b = st.columns([2, 1])
                
                with col_a:
                    st.markdown(f"**Address:** {job['Address']}, {job['City']} {pincode_str}")
                    st.markdown(f"**Client Contact:** [{job['Client_Phone']}](tel:{job['Client_Phone']})")
                    st.markdown(f"**Task Description:** {job['Issue_Description']}")
                    st.markdown(f"**Scheduled Time:** {job['Scheduled_Time']}")
                    maps_url = make_google_maps_link(job['Address'], job['City'], job.get('Pincode', ''))
                    st.markdown(f"[📍 **Open Route in Google Maps**]({maps_url})")

                with col_b:
                    status_list = ["Assigned", "In Transit", "On Site", "Completed"]
                    current_status = job["Status"] if job["Status"] in status_list else "Assigned"
                    new_status = st.selectbox("Job Status", status_list, index=status_list.index(current_status), key=f"status_{job['Job_ID']}")
                    
                    btn_save, btn_report = st.columns(2)
                    with btn_save:
                        if st.button("Save Status", key=f"btn_{job['Job_ID']}"):
                            st.session_state.jobs_db.loc[st.session_state.jobs_db["Job_ID"] == job["Job_ID"], "Status"] = new_status
                            save_sheet_data(st.session_state.jobs_db, "Jobs")
                            st.toast(f"✅ Status updated for {job['Job_ID']}!")
                            st.rerun()
                    with btn_report:
                        if st.button("📝 Submit Report", key=f"btn_rpt_{job['Job_ID']}"):
                            st.session_state.selected_job_for_report = job["Job_ID"]
                            st.toast(f"Selected {job['Job_ID']} for service report!")
                st.divider()

    # -------------------------------------------------------------------------
    # TAB 2: Service Report Form (Option 1: Site Photos & Option 2: Filled Form Photo)
    # -------------------------------------------------------------------------
    with tech_tab2:
        st.subheader("📝 Submit Client Service Report")
        
        pending_tech_jobs = st.session_state.jobs_db[
            (st.session_state.jobs_db["Assigned_Tech_ID"].astype(str) == tech_id) & 
            (st.session_state.jobs_db["Status"] != "Completed")
        ]
        
        if pending_tech_jobs.empty:
            st.info("🎉 No pending tasks found. Select a task or assign a work order first.")
        else:
            job_options = pending_tech_jobs["Job_ID"].tolist()
            default_index = 0
            if st.session_state.selected_job_for_report in job_options:
                default_index = job_options.index(st.session_state.selected_job_for_report)
                
            selected_job_id = st.radio(
                "Select Assigned Job / Task*", 
                options=job_options, 
                index=default_index,
                horizontal=True,
                format_func=lambda x: f"{x} — {pending_tech_jobs[pending_tech_jobs['Job_ID'] == x]['Client_Name'].values[0]}"
            )
            
            selected_job = pending_tech_jobs[pending_tech_jobs["Job_ID"] == selected_job_id].iloc[0]
            auto_client_name = str(selected_job.get("Client_Name", ""))
            auto_address = f"{selected_job.get('Address', '')}, {selected_job.get('City', '')}".strip(", ")
            if selected_job.get("Pincode"):
                auto_address += f" - {selected_job.get('Pincode')}"

            contracts_df = st.session_state.amc_contracts_db
            contract_options = ["N/A"] + contracts_df["AMC_Contract_No"].astype(str).tolist() if not contracts_df.empty else ["N/A"]

            # Header Info
            h_col1, h_col2 = st.columns(2)
            with h_col1:
                st.text_input("Client Name", value=auto_client_name, disabled=True)
                selected_contract_no = st.selectbox("Link AMC Contract Number (Optional)", contract_options, key="select_amc_contract")
            with h_col2:
                rpt_visit_num_str = st.radio(
                    "AMC Visit Sequence*", 
                    ["Visit 1 of 4", "Visit 2 of 4", "Visit 3 of 4", "Visit 4 of 4"], 
                    horizontal=True,
                    key="select_visit_seq"
                )

            st.divider()

            # Inline Equipment Category Switcher
            st.markdown("### Select Equipment Category*")
            current_category = st.radio(
                "Category",
                options=list(EQUIPMENT_DATA.keys()),
                horizontal=True,
                key="active_category_radio",
                label_visibility="collapsed"
            )

            st.divider()

            category_data = EQUIPMENT_DATA[current_category]
            category_types = category_data["types"]
            category_checklist = category_data["checklist"]

            st.markdown(f"### 1. Equipment Details — **{current_category}**")

            # Inline Equipment Type Selector
            st.markdown("**Equipment Type***")
            eq_type = st.radio(
                "Equipment Type",
                options=category_types,
                horizontal=True,
                key=f"eq_type_radio_{current_category}",
                label_visibility="collapsed"
            )

            eq_col1, eq_col2, eq_col3, eq_col4 = st.columns([2.5, 2.5, 1.5, 2.5])
            with eq_col1:
                eq_make_model = st.text_input("Make / Model", placeholder="e.g. Sidharth", key=f"eq_make_{current_category}")
            with eq_col2:
                eq_size = st.text_input("Door / Gate Size", placeholder="e.g. 4000x4500 mm", key=f"eq_size_{current_category}")
            with eq_col3:
                eq_qty = st.number_input("Qty", min_value=1, value=1, key=f"eq_qty_{current_category}")
            with eq_col4:
                eq_condition = st.radio("Condition*", ["Good", "Requires Repair", "Critical", "Replaced"], horizontal=True, key=f"eq_cond_{current_category}")

            st.markdown("### General Visit Details")
            c_det1, c_det2 = st.columns(2)
            with c_det1:
                rpt_site_location = st.text_input("Site / Location*", value=auto_address, key=f"loc_{current_category}")
                rpt_service_date = st.date_input("Service Date", value=date.today(), key=f"sdate_{current_category}")
            with c_det2:
                rpt_next_due = st.date_input("Next Service Due Date", value=date.today() + pd.Timedelta(days=90), key=f"ndate_{current_category}")

            st.markdown(f"### 2. Preventive Maintenance Checklist ({current_category})")
            
            checklist_results = {}
            for idx, point in enumerate(category_checklist, 1):
                col_num, col_point, col_status, col_remark = st.columns([0.5, 4.0, 3.5, 4.0])
                with col_num:
                    st.write(f"**{idx}.**")
                with col_point:
                    st.write(point)
                with col_status:
                    status = st.radio(
                        "Status", 
                        ["Satisfactory", "Repaired On-Site", "Action Required", "Not Applicable"], 
                        horizontal=False, 
                        key=f"chk_{current_category}_{idx}",
                        label_visibility="collapsed"
                    )
                with col_remark:
                    remark = st.text_input(
                        "Remarks", 
                        placeholder="Action taken / Remark", 
                        key=f"rem_{current_category}_{idx}",
                        label_visibility="collapsed"
                    )
                
                checklist_results[f"Q{idx}"] = {
                    "choice": status, 
                    "remark": remark.strip() if remark.strip() else "N/A"
                }
                st.divider()

            st.markdown("### 3. Remarks & Recommendations")
            rpt_remarks = st.text_area("General Remarks*", placeholder="Overall observations, work executed, recommendations...", key=f"rem_area_{current_category}")

            # -----------------------------------------------------------------
            # PHOTO UPLOADS: Option 1 (Site Photos) & Option 2 (Form Filled Photo)
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("### 📷 Photo Attachments")

            col_img1, col_img2 = st.columns(2)
            
            # OPTION 1: Site Photos (4 to 8 required)
            with col_img1:
                st.markdown("#### Option 1: Site Photos*")
                site_photos = st.file_uploader(
                    "Attach 4 to 8 Site Photos (Equipment, Site Condition, Installation)", 
                    type=["jpg", "jpeg", "png"], 
                    accept_multiple_files=True, 
                    key=f"site_photos_{current_category}"
                )
                if site_photos:
                    if 4 <= len(site_photos) <= 8:
                        st.success(f"✅ {len(site_photos)} site photos selected.")
                    else:
                        st.warning(f"⚠️ Selected {len(site_photos)} photos. Please attach between 4 and 8 site photos.")

            # OPTION 2: Form Filled Photo (Physical Sheet)
            with col_img2:
                st.markdown("#### Option 2: Filled Form Photo")
                sheet_photo = st.file_uploader(
                    "Attach Photo of Physical Signed Service Form / Paper Sheet (Optional)", 
                    type=["jpg", "jpeg", "png"], 
                    accept_multiple_files=False, 
                    key=f"sheet_upload_{current_category}"
                )
                if sheet_photo:
                    st.success(f"✅ Filled form photo selected: `{sheet_photo.name}`")

            st.divider()

            if st.button("Submit Service Report", type="primary", key=f"submit_btn_{current_category}", use_container_width=True):
                if not rpt_site_location or not rpt_remarks:
                    st.error("⚠️ Please fill in all required text fields marked with *")
                elif not site_photos or len(site_photos) < 4 or len(site_photos) > 8:
                    st.error("⚠️ Please attach between 4 and 8 site photos under Option 1 before submitting.")
                else:
                    with st.spinner("📤 Uploading site photos and form scan to Google Drive... Please wait."):
                        sheet_link = ""
                        if sheet_photo:
                            uploaded_sheet = upload_photos_to_drive([sheet_photo], folder_name="AMC_Physical_Sheets")
                            if uploaded_sheet:
                                sheet_link = uploaded_sheet[0]

                        site_photo_links = upload_photos_to_drive(site_photos, folder_name="AMC_Site_Photos")
                        site_links_str = " | ".join(site_photo_links)

                    try:
                        local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                        submit_time_str = datetime.now(local_tz).strftime("%Y-%m-%d %I:%M %p")
                    except Exception:
                        submit_time_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

                    report_entry = {
                        "Report_ID": f"RPT-{len(st.session_state.service_reports_db) + 1001}",
                        "Job_ID": selected_job_id,
                        "Tech_ID": tech_id,
                        "Tech_Name": tech_name,
                        "Client_Name": auto_client_name,
                        "Site_Location": rpt_site_location,
                        "AMC_Contract_No": selected_contract_no,
                        "Category": current_category,
                        "Equipment_Type": eq_type,
                        "Make_Model": eq_make_model,
                        "Door_Size": eq_size,
                        "Qty": str(eq_qty),
                        "Condition": eq_condition,
                        "Checklist_Data": "Stored in Q1-Q18 columns",
                        "Service_Date": str(rpt_service_date),
                        "Visit_Number": rpt_visit_num_str,
                        "Next_Service_Due_Date": str(rpt_next_due),
                        "Remarks": rpt_remarks,
                        "Submitted_At": submit_time_str,
                        "Physical_Sheet_URL": sheet_link,
                        "Site_Photos_URLs": site_links_str
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
                    st.toast(f"✅ Service report & photos submitted successfully for {selected_job_id}!", icon="📄")
                    st.rerun()

    # -------------------------------------------------------------------------
    # TAB 3: Broadcast Location & Status
    # -------------------------------------------------------------------------
    with tech_tab3:
        st.subheader("Broadcast Live Location & Next Target")
        curr_rec = st.session_state.tech_status_db[st.session_state.tech_status_db["Tech_ID"].astype(str) == tech_id]
        
        c_curr_city = curr_rec["Current_City"].values[0] if not curr_rec.empty else ""
        c_curr_pin = curr_rec["Current_Pincode"].values[0] if not curr_rec.empty else ""
        c_curr_stat = curr_rec["Current_Status"].values[0] if not curr_rec.empty else "Available"
        c_next_city = curr_rec["Next_City"].values[0] if not curr_rec.empty else ""
        c_next_pin = curr_rec["Next_Pincode"].values[0] if not curr_rec.empty else ""
        c_eta = curr_rec["ETA"].values[0] if not curr_rec.empty else ""

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("##### 📍 Current Location")
            t_curr_city = st.text_input("Current City", value=c_curr_city, key="ts_curr_city")
            t_curr_pin = st.text_input("Current Pincode", value=c_curr_pin, key="ts_curr_pin")
            t_curr_stat = st.selectbox("Current Status", ["Available", "In Transit", "Working On Site", "Off Duty"], index=["Available", "In Transit", "Working On Site", "Off Duty"].index(c_curr_stat) if c_curr_stat in ["Available", "In Transit", "Working On Site", "Off Duty"] else 0, key="ts_curr_stat")
        
        with col_s2:
            st.markdown("##### 🎯 Next Destination (Optional)")
            t_next_city = st.text_input("Next City / Target Location", value=c_next_city, key="ts_next_city")
            t_next_pin = st.text_input("Next Pincode", value=c_next_pin, key="ts_next_pin")
            t_eta = st.text_input("Estimated Arrival Time (ETA)", value=c_eta, placeholder="e.g. 02:30 PM", key="ts_eta")

        if st.button("Update Location & Status", type="primary", use_container_width=True):
            try:
                local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                upd_time_str = datetime.now(local_tz).strftime("%Y-%m-%d %I:%M %p")
            except Exception:
                upd_time_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

            status_entry = {
                "Tech_ID": tech_id,
                "Current_City": t_curr_city,
                "Current_Pincode": t_curr_pin,
                "Current_Status": t_curr_stat,
                "Next_City": t_next_city,
                "Next_Pincode": t_next_pin,
                "ETA": t_eta,
                "Last_Updated": upd_time_str
            }
            
            df_status = st.session_state.tech_status_db
            df_status = df_status[df_status["Tech_ID"].astype(str) != tech_id]
            st.session_state.tech_status_db = pd.concat([df_status, pd.DataFrame([status_entry])], ignore_index=True)
            save_sheet_data(st.session_state.tech_status_db, "TechStatus")
            st.toast("✅ Location & Status successfully broadcasted!")
            st.rerun()

    # -------------------------------------------------------------------------
    # TAB 4: Service History
    # -------------------------------------------------------------------------
    with tech_tab4:
        st.subheader("📜 Submitted Service Reports History")
        tech_reports = st.session_state.service_reports_db[st.session_state.service_reports_db["Tech_ID"].astype(str) == tech_id]
        
        if tech_reports.empty:
            st.info("No submitted service reports found.")
        else:
            st.dataframe(tech_reports, use_container_width=True)
