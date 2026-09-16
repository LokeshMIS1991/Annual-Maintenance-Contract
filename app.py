import streamlit as st
import pandas as pd
from datetime import datetime, date, time
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
    default_columns = {
        "Users": ["User_ID", "Full_Name", "Role", "Password"],
        "Jobs": ["Job_ID", "Assigned_Tech_ID", "Client_Name", "Client_Phone", "Address", "City", "Pincode", "Issue_Description", "Status", "Scheduled_Time"],
        "TechStatus": ["Tech_ID", "Current_City", "Current_Pincode", "Current_Status", "Next_City", "Next_Pincode", "ETA", "Last_Updated"],
        "ServiceReports": ["Report_ID", "Tech_ID", "Tech_Name", "Client_Name", "Site_Location", "AMC_Contract_No", "Category", "Equipment_Type", "Make_Model", "Door_Size", "Qty", "Condition", "Checklist_Data", "Service_Date", "Visit_Number", "Next_Service_Due_Date", "Remarks", "Submitted_At"],
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
        return df
    except Exception:
        try:
            ws = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
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

# -----------------------------------------------------------------------------
# 4. BRANDED UI STYLING
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-highlight"] { background-color: #1565C0 !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #1565C0 !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #F8FAFC !important; }
    .sidebar-logo-sub { color: #10B981; font-weight: 800; font-size: 0.95rem; letter-spacing: 1.5px; text-align: center; margin-top: 6px; }
    
    .stButton > button, div[data-testid="stForm"] button { 
        background-color: #1565C0 !important; 
        color: #FFFFFF !important; 
        border-radius: 8px !important; 
        font-weight: 600 !important; 
        width: 100% !important; 
    }
    .stButton > button:hover, div[data-testid="stForm"] button:hover { background-color: #0D47A1 !important; }
    a { color: #1565C0 !important; }
    
    div[data-testid="stForm"] { 
        background-color: #FFFFFF; 
        border: 2px solid #1565C0; 
        border-radius: 16px; 
        padding: 24px; 
    }
    .login-container div[data-testid="stForm"] { padding: 20px 28px !important; max-width: 360px; margin: 0 auto; text-align: center; }

    div[data-baseweb="select"] {
        background-color: transparent !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. LOGIN SCREEN
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
            
            st.markdown("<h3 style='text-align:center; color:#0D47A1;'>AMC Tracker</h3>", unsafe_allow_html=True)
            user_id_input = st.text_input("User ID", placeholder="e.g. TECH01").strip().upper()
            password_input = st.text_input("Password", type="password", placeholder="Enter password").strip()
            
            if st.form_submit_button("Sign In"):
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
        st.markdown("<h3 style='color: #0D47A1; text-align:center;'>⚙️ SIDHARTH</h3>", unsafe_allow_html=True)
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
        "📝 Submit Client Service Report",
        "📍 Update Status & Destination", 
        "📜 Service History"
    ])

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
                    
                    if st.button("Save Status", key=f"btn_{job['Job_ID']}"):
                        st.session_state.jobs_db.loc[st.session_state.jobs_db["Job_ID"] == job["Job_ID"], "Status"] = new_status
                        save_sheet_data(st.session_state.jobs_db, "Jobs")
                        st.toast(f"✅ Status updated for {job['Job_ID']}!")
                        st.rerun()
                st.divider()

    # TAB 2: Dynamic Categorized Service Report Form
    with tech_tab2:
        st.subheader("📝 Submit Client Service Report")
        
        contracts_df = st.session_state.amc_contracts_db
        if contracts_df.empty:
            st.warning("⚠️ No active AMC contracts found in the database.")
        else:
            contract_options = contracts_df["AMC_Contract_No"].astype(str).tolist()
            
            c_header1, c_header2 = st.columns(2)
            with c_header1:
                selected_contract_no = st.selectbox("Select AMC Contract Number*", contract_options)
                selected_contract_info = contracts_df[contracts_df["AMC_Contract_No"].astype(str) == selected_contract_no].iloc[0]
                client_name_val = selected_contract_info.get("Client_Name", "")
                st.text_input("Client Name", value=client_name_val, disabled=True)
            
            with c_header2:
                # Category selection driving dynamic checklist fields
                selected_category = st.selectbox("Equipment Category*", ["Rolling Shutter", "High Speed Door"])
                try:
                    allowed_visits_max = int(selected_contract_info.get("Allowed_Visits", 4))
                except Exception:
                    allowed_visits_max = 4
                visit_choices = [f"Visit {i} of {allowed_visits_max}" for i in range(1, allowed_visits_max + 1)]
                rpt_visit_num_str = st.selectbox("AMC Visit Sequence*", visit_choices)

            st.divider()

            with st.form(f"service_report_form_{tech_id}"):
                st.markdown("### General Visit Details")
                c_det1, c_det2 = st.columns(2)
                with c_det1:
                    rpt_site_location = st.text_input("Site / Location*", placeholder="e.g. Unit 4, GIDC Estate")
                    rpt_service_date = st.date_input("Service Date", value=date.today())
                with c_det2:
                    rpt_next_due = st.date_input("Next Service Due Date", value=date.today() + pd.Timedelta(days=90))

                # Section 1: Equipment Details
                st.markdown("### 1. Equipment Details")
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

                # Section 2: Preventive Maintenance Checklist
                st.markdown(f"### 2. Preventive Maintenance Checklist ({selected_category})")
                
                checklist_results = {}
                checklist_items = EQUIPMENT_DATA[selected_category]["checklist"]
                
                # Render 18 Points
                for idx, point in enumerate(checklist_items, 1):
                    col_num, col_point, col_status, col_remark = st.columns([0.5, 4.5, 3, 4])
                    with col_num:
                        st.write(f"**{idx}.**")
                    with col_point:
                        st.write(point)
                    with col_status:
                        status = st.radio(
                            "Status", 
                            ["OK", "Not OK", "N/A"], 
                            horizontal=True, 
                            key=f"check_{selected_category}_{idx}",
                            label_visibility="collapsed"
                        )
                    with col_remark:
                        remark = st.text_input(
                            "Remarks", 
                            placeholder="Action taken / Remark", 
                            key=f"rem_{selected_category}_{idx}",
                            label_visibility="collapsed"
                        )
                    checklist_results[f"P{idx}_{point}"] = {"status": status, "remark": remark}
                    st.divider()

                # Section 3: Overall Remarks
                st.markdown("### 3. Remarks / Recommendations")
                rpt_remarks = st.text_area("General Remarks & Summary*", placeholder="Overall observations, recommendations...")

                submit_report = st.form_submit_button("Submit Service Report")
                
                if submit_report:
                    if not rpt_site_location or not rpt_remarks:
                        st.error("⚠️ Please fill in all required fields marked with *")
                    else:
                        try:
                            local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                            submit_time_str = datetime.now(local_tz).strftime("%Y-%m-%d %I:%M %p")
                        except Exception:
                            submit_time_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")

                        report_entry = {
                            "Report_ID": f"RPT-{len(st.session_state.service_reports_db) + 1001}",
                            "Tech_ID": tech_id,
                            "Tech_Name": tech_name,
                            "Client_Name": client_name_val,
                            "Site_Location": rpt_site_location,
                            "AMC_Contract_No": selected_contract_no,
                            "Category": selected_category,
                            "Equipment_Type": eq_type,
                            "Make_Model": eq_make_model,
                            "Door_Size": eq_size,
                            "Qty": str(eq_qty),
                            "Condition": eq_condition,
                            "Checklist_Data": str(checklist_results),
                            "Service_Date": str(rpt_service_date),
                            "Visit_Number": rpt_visit_num_str,
                            "Next_Service_Due_Date": str(rpt_next_due),
                            "Remarks": rpt_remarks,
                            "Submitted_At": submit_time_str
                        }
                        
                        st.session_state.service_reports_db = pd.concat([st.session_state.service_reports_db, pd.DataFrame([report_entry])], ignore_index=True)
                        save_sheet_data(st.session_state.service_reports_db, "ServiceReports")
                        st.toast("✅ Categorized Service report saved successfully!", icon="📄")
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

    # TAB 4: History
    with tech_tab4:
        st.subheader("My Service Record History")
        reports_df = st.session_state.service_reports_db
        if not reports_df.empty and "Tech_ID" in reports_df.columns:
            my_reports = reports_df[reports_df["Tech_ID"].astype(str) == tech_id]
            st.dataframe(my_reports, use_container_width=True)
        else:
            st.info("📜 No service reports submitted yet.")

# -----------------------------------------------------------------------------
# 8. MANAGER COMMAND DASHBOARD
# -----------------------------------------------------------------------------

elif st.session_state.user["Role"] in ["Manager", "Admin"]:
    st.markdown("<h1 style='color: #0D47A1;'>📡 Dispatch & AMC Control Center</h1>", unsafe_allow_html=True)

    mgr_tab1, mgr_tab2, mgr_tab3, mgr_tab4 = st.tabs([
        "MAP / Live Radar", 
        "📄 Client Service Reports",
        "📅 AMC Contract Manager",
        "➕ Create Task / User"
    ])

    with mgr_tab1:
        st.subheader("Technician Fleet Live Radar")
        full_radar = pd.merge(st.session_state.tech_status_db, st.session_state.users_db[["User_ID", "Full_Name"]], left_on="Tech_ID", right_on="User_ID", how="left")
        st.dataframe(full_radar, use_container_width=True)
        st.divider()
        st.subheader("All Active Work Orders")
        st.dataframe(st.session_state.jobs_db, use_container_width=True)

    with mgr_tab2:
        st.subheader("📋 Field Service Visit Reports Log")
        st.dataframe(st.session_state.service_reports_db, use_container_width=True)

    with mgr_tab3:
        st.subheader("🗓️ AMC Client Contracts Management")
        st.dataframe(st.session_state.amc_contracts_db, use_container_width=True)
        st.divider()
        st.markdown("### ✏️ Register / Update AMC Contract Limits")
        
        with st.form("edit_amc_contract_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                contract_no = st.text_input("AMC Contract Number*", placeholder="e.g. AMC-2026-88").strip()
                c_client_name = st.text_input("Client Name*", placeholder="e.g. Apex Industries").strip()
                visits_allowed = st.selectbox("Annual Allowed Visits Limit*", [2, 3, 4], index=2)
            with col_c2:
                contract_start = st.date_input("Contract Start Date", value=date.today())
                contract_end = st.date_input("Contract End Date", value=date.today() + pd.Timedelta(days=365))
            
            if st.form_submit_button("Save / Update AMC Contract"):
                if not contract_no or not c_client_name:
                    st.error("⚠️ Contract Number and Client Name are required.")
                else:
                    contracts_df = st.session_state.amc_contracts_db
                    if not contracts_df.empty and contract_no in contracts_df["AMC_Contract_No"].astype(str).values:
                        st.session_state.amc_contracts_db.loc[
                            st.session_state.amc_contracts_db["AMC_Contract_No"].astype(str) == contract_no,
                            ["Client_Name", "Start_Date", "End_Date", "Allowed_Visits"]
                        ] = [c_client_name, str(contract_start), str(contract_end), visits_allowed]
                    else:
                        new_contract = {
                            "AMC_Contract_No": contract_no,
                            "Client_Name": c_client_name,
                            "Start_Date": str(contract_start),
                            "End_Date": str(contract_end),
                            "Allowed_Visits": visits_allowed
                        }
                        st.session_state.amc_contracts_db = pd.concat([st.session_state.amc_contracts_db, pd.DataFrame([new_contract])], ignore_index=True)
                    
                    save_sheet_data(st.session_state.amc_contracts_db, "AMCContracts")
                    st.toast(f"✅ Contract {contract_no} saved!")
                    st.rerun()

    with mgr_tab4:
        col_mgr_a, col_mgr_b = st.columns(2)
        
        # Dispatch Task Column
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

        # Admin Only Registration
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
