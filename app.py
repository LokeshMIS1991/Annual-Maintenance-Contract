import streamlit as st
import pandas as pd
import datetime
import base64
import uuid
import io
import os
import urllib.parse
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="AMC & Field Technician Tracker",
    page_icon="🔧",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #F8FAFC;
    }
    h1, h2, h3 {
        color: #0F2C59 !important;
        font-weight: 700 !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #0F2C59 0%, #1E56A0 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1E56A0 0%, #0F2C59 100%) !important;
        box-shadow: 0 4px 12px rgba(15, 44, 89, 0.25) !important;
    }
    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border-left: 5px solid #10B981 !important;
        border-radius: 10px !important;
        padding: 15px 20px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
    }
    [data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #0F2C59 !important;
        font-weight: 800 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #E2E8F0;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        color: #0F2C59;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0F2C59 !important;
        color: white !important;
    }
    .checkin-card {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GOOGLE SHEETS AUTHENTICATION & CACHE
# ==========================================
@st.cache_resource(ttl=60)
def get_gspread_client():
    """Authenticates with Google Sheets API using Streamlit secrets."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    if "gsheets" in st.secrets and "service_account" in st.secrets["gsheets"]:
        creds_dict = dict(st.secrets["gsheets"]["service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet_url = st.secrets["gsheets"]["spreadsheet_url"]
        
        # Worksheet 0 for Field Visits, Worksheet 1 for Active Check-ins
        sh = client.open_by_url(spreadsheet_url)
        return sh
    else:
        st.error("Google Sheets configuration missing in `.streamlit/secrets.toml`!")
        st.stop()

def fetch_sheet_data(sh, index=0):
    """Retrieves records from a specified worksheet into a DataFrame."""
    try:
        worksheet = sh.get_worksheet(index)
        all_values = worksheet.get_all_values()
        if not all_values or len(all_values) < 2:
            return pd.DataFrame(), worksheet
        
        headers = all_values[0]
        data = all_values[1:]
        df = pd.DataFrame(data, columns=headers)
        df = df.loc[:, ~df.columns.duplicated()]
        return df, worksheet
    except Exception as e:
        st.error(f"Error accessing Google Worksheet [{index}]: {e}")
        return pd.DataFrame(), None

def save_visit_to_gsheets(worksheet, record_dict):
    """Appends dynamic record fields to the Google Sheet."""
    try:
        headers = worksheet.row_values(1)
        row = [str(record_dict.get(h, "")) for h in headers]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Failed to write to Google Sheet: {e}")
        return False

def update_checkin_sheet(worksheet, tech_name, city, area, status, email):
    """Updates or appends a technician's live location check-in status."""
    try:
        all_values = worksheet.get_all_values()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if len(all_values) <= 1:
            worksheet.append_row([tech_name, city, area, status, email, timestamp])
            return True
            
        for i, row in enumerate(all_values[1:], start=2):
            if row[0].strip().lower() == tech_name.strip().lower():
                worksheet.update(f"A{i}:F{i}", [[tech_name, city, area, status, email, timestamp]])
                return True
                
        worksheet.append_row([tech_name, city, area, status, email, timestamp])
        return True
    except Exception as e:
        st.error(f"Failed to update location check-in: {e}")
        return False

def generate_visit_id():
    """Generates an automated unique Visit ID."""
    return f"AMC-{datetime.date.today().year}-{uuid.uuid4().hex[:5].upper()}"

# Initialize Sheets Connections & Data
sh = get_gspread_client()
df_visits, sheet_visits = fetch_sheet_data(sh, 0)

try:
    df_checkins, sheet_checkins = fetch_sheet_data(sh, 1)
except:
    df_checkins, sheet_checkins = pd.DataFrame(), None

# Numerical conversions
if not df_visits.empty:
    df_visits['Total_Services_Included'] = pd.to_numeric(df_visits.get('Total_Services_Included', 0), errors='coerce').fillna(0).astype(int)
    df_visits['Services_Completed'] = pd.to_numeric(df_visits.get('Services_Completed', 0), errors='coerce').fillna(0).astype(int)
    df_visits['Pending_Services'] = df_visits['Total_Services_Included'] - df_visits['Services_Completed']
    df_visits['Pending_Services'] = df_visits['Pending_Services'].apply(lambda x: max(0, x))

# Map Coordinates Dictionary for Indian Cities (Extensible)
CITY_COORDINATES = {
    "surat": {"lat": 21.1702, "lon": 72.8311},
    "ahmedabad": {"lat": 23.0225, "lon": 72.5714},
    "vadodara": {"lat": 22.3072, "lon": 73.1812},
    "rajkot": {"lat": 22.3039, "lon": 70.8022},
    "mumbai": {"lat": 19.0760, "lon": 72.8777},
    "delhi": {"lat": 28.6139, "lon": 77.2090},
    "pune": {"lat": 18.5204, "lon": 73.8567},
    "jaipur": {"lat": 26.9124, "lon": 75.7873}
}

# ==========================================
# 3. SIDEBAR & ROLE ACCESS CONTROL
# ==========================================
st.sidebar.title("🔐 Role Access Mode")
user_role = st.sidebar.radio("Select Your Role:", ["Technician Entry", "Manager Portal", "Admin Dashboard"])

is_admin, is_manager = False, False

if user_role == "Admin Dashboard":
    admin_password_secret = st.secrets.get("admin_password", "admin123")
    pwd_input = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd_input == admin_password_secret:
        is_admin = True
        st.sidebar.success("🔓 Authenticated as Administrator")
    elif pwd_input:
        st.sidebar.error("❌ Incorrect Admin Password")
        st.stop()
    else:
        st.sidebar.warning("⚠️ Enter password to unlock Admin controls.")
        st.stop()

elif user_role == "Manager Portal":
    manager_password_secret = st.secrets.get("manager_password", "manager123")
    pwd_input = st.sidebar.text_input("Enter Manager Password", type="password")
    if pwd_input == manager_password_secret:
        is_manager = True
        st.sidebar.success("🔓 Authenticated as Manager")
    elif pwd_input:
        st.sidebar.error("❌ Incorrect Manager Password")
        st.stop()
    else:
        st.sidebar.warning("⚠️ Enter password to unlock Manager controls.")
        st.stop()

# ==========================================
# 4. BRANDED HEADER
# ==========================================
header_title_col, header_logo_col = st.columns([3, 1])

with header_title_col:
    st.title("AMC & Field Technician Tracker")
    st.markdown("<p style='color: #475569; font-size: 1.1rem; margin-top: -10px;'>Sidharth Shutter & Automation — Proximity Dispatch System</p>", unsafe_allow_html=True)

with header_logo_col:
    for ext in ["Company Logo.jpeg", "Company Logo.jpg", "Company Logo.png"]:
        if os.path.exists(ext):
            st.image(ext, use_container_width=True)
            break

st.divider()

# ==========================================
# 5. DASHBOARD METRICS
# ==========================================
today = pd.Timestamp.today().normalize()

if not df_visits.empty:
    if 'Next_Service_Due_Date' in df_visits.columns:
        df_visits['Next_Service_Due_Date_DT'] = pd.to_datetime(df_visits['Next_Service_Due_Date'], errors='coerce')
    else:
        df_visits['Next_Service_Due_Date_DT'] = pd.NaT

    active_count = len(df_visits[df_visits['Contract_Status'] == 'Active']) if 'Contract_Status' in df_visits.columns else 0
    expiring_count = len(df_visits[df_visits['Contract_Status'] == 'Expiring Soon']) if 'Contract_Status' in df_visits.columns else 0

    pending_df = df_visits[
        (df_visits.get('Contract_Status') == 'Pending Service') | 
        (df_visits['Pending_Services'] > 0) |
        ((df_visits['Next_Service_Due_Date_DT'].notna()) & (df_visits['Next_Service_Due_Date_DT'] <= today))
    ].copy()
    
    if not pending_df.empty and 'Client_Name' in pending_df.columns:
        latest_pending_per_client = pending_df.sort_values('Date_of_Visit').groupby(['Client_Name', 'Product_Name']).last().reset_index()
    else:
        latest_pending_per_client = pd.DataFrame()

    pending_count = len(latest_pending_per_client)
    breakdown_count = len(df_visits[df_visits['Visit_Type'] == 'Breakdown Call / Emergency Repair']) if 'Visit_Type' in df_visits.columns else 0
else:
    active_count, expiring_count, pending_count, breakdown_count = 0, 0, 0, 0
    latest_pending_per_client = pd.DataFrame()

# Active Checked-in Technicians Count
active_techs_count = 0
if not df_checkins.empty and 'Status' in df_checkins.columns:
    active_techs_count = len(df_checkins[df_checkins['Status'] == 'Available'])

if is_admin or is_manager:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active Contracts", active_count)
    c2.metric("Clients Pending", pending_count)
    c3.metric("Expiring Soon", expiring_count)
    c4.metric("Breakdown Calls", breakdown_count)
    c5.metric("Available Techs", active_techs_count)
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Clients Pending", pending_count)
    c2.metric("Breakdown Calls", breakdown_count)
    c3.metric("Techs Checked-In", active_techs_count)

st.divider()

# ==========================================
# 6. ROLE INTERFACES & WORKFLOWS
# ==========================================

# ------------------------------------------
# A. ADMIN VIEW
# ------------------------------------------
if is_admin:
    st.subheader("📊 Administrative Control Center & Operational Records")
    
    if df_visits.empty:
        st.info("No records stored in Google Sheets.")
    else:
        f_col1, f_col2 = st.columns([2, 1])
        with f_col1:
            search_visit_id = st.text_input("🔍 Search by Visit ID or Client", "").strip()
        with f_col2:
            status_filter = st.selectbox("Filter Status", ["All", "Active", "Inactive", "Expiring Soon", "Pending Service"])
            
        filtered_df = df_visits.copy()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Contract_Status'] == status_filter]

        if search_visit_id:
            filtered_df = filtered_df[
                filtered_df['Visit_ID'].astype(str).str.contains(search_visit_id, case=False, na=False) |
                filtered_df['Client_Name'].astype(str).str.contains(search_visit_id, case=False, na=False)
            ]

        hidden_cols = ['Job_Sheet_Photo_Base64', 'Next_Service_Due_Date_DT']
        display_cols = [c for c in filtered_df.columns if c not in hidden_cols]
        st.dataframe(filtered_df[display_cols], use_container_width=True)

# ------------------------------------------
# B. MANAGER PORTAL (MAP + DISPATCH + ENTRY)
# ------------------------------------------
elif is_manager:
    tab_map, tab_entry, tab_records = st.tabs([
        "📍 Live Technician Radar Map", 
        "📝 Register New Call / Service", 
        "📊 All Records & History"
    ])

    # --- TAB 1: RADAR MAP & PROXIMITY DISPATCH ---
    with tab_map:
        st.subheader("📍 Live Field Technician Locations & Local Matching")
        
        if df_checkins.empty:
            st.warning("No technician location check-ins recorded yet.")
        else:
            m_col1, m_col2 = st.columns([2, 1])
            
            with m_col1:
                st.markdown("**Active Technician Positions Map**")
                
                # Build Map Dataframe
                map_records = []
                for idx, row in df_checkins.iterrows():
                    c_name = str(row.get('City', '')).strip().lower()
                    if c_name in CITY_COORDINATES:
                        coords = CITY_COORDINATES[c_name]
                        map_records.append({
                            "Technician": row.get('Technician_Name', 'Unknown'),
                            "City": row.get('City', ''),
                            "Area": row.get('Area', ''),
                            "Status": row.get('Status', 'Available'),
                            "lat": coords['lat'],
                            "lon": coords['lon']
                        })
                
                if map_records:
                    map_df = pd.DataFrame(map_records)
                    st.map(map_df, latitude='lat', longitude='lon', zoom=6)
                else:
                    st.info("Map coordinates unavailable for checked-in cities. See tabular view on the right.")

            with m_col2:
                st.markdown("**Technicians Checked-In Nearby**")
                st.dataframe(df_checkins[['Technician_Name', 'City', 'Area', 'Status', 'Last_Updated']], use_container_width=True)

        st.divider()
        st.subheader("⚡ Quick Dispatch Alert Generator")
        
        target_city = st.text_input("Enter Request City (e.g., Surat, Gujarat)", "Surat")
        client_issue = st.text_area("Request Brief / Issue Description", "Breakdown reported at Main Warehouse. Motorized Shutter stuck.")
        
        if target_city.strip() and not df_checkins.empty:
            matched_techs = df_checkins[df_checkins['City'].astype(str).str.strip().str.lower() == target_city.strip().lower()]
            
            if not matched_techs.empty:
                st.success(f"🎯 Found {len(matched_techs)} technician(s) active in `{target_city}`!")
                for _, t_row in matched_techs.iterrows():
                    t_name = t_row.get('Technician_Name', '')
                    t_email = t_row.get('Email', '')
                    
                    st.markdown(f"👉 **{t_name}** ({t_row.get('Area', 'General Area')}) — *Status:* `{t_row.get('Status')}`")
                    
                    if t_email:
                        subject = urllib.parse.quote(f"EMERGENCY SERVICE DISPATCH: {target_city.upper()}")
                        body = urllib.parse.quote(f"Hello {t_name},\n\nNew service job in your current area ({target_city}):\n{client_issue}\n\nPlease proceed immediately.")
                        mailto_link = f"mailto:{t_email}?subject={subject}&body={body}"
                        st.markdown(f"📧 [Click to Send Email Alert directly to {t_name}]({mailto_link})")
            else:
                st.info(f"No technicians currently checked into `{target_city}`. Check standard task roster.")

    # --- TAB 2: MANAGER SERVICE ENTRY ---
    with tab_entry:
        st.subheader("Register AMC Visit / Emergency Call (Manager Mode)")
        auto_id = generate_visit_id()
        st.info(f"**Automated Visit ID:** `{auto_id}`")
        
        c_left, c_right = st.columns(2)
        with c_left:
            client_name = st.text_input("Client Name *", key="mgr_cname")
            company_name = st.text_input("Company Name", key="mgr_comp")
            city_name = st.text_input("City / Location *", "Surat", key="mgr_city")
            phone_number = st.text_input("Phone Number", key="mgr_phone")
            address = st.text_area("Address", key="mgr_addr")
            
            contract_start_date = st.date_input("Contract Start Date", today.date())
            contract_end_date = st.date_input("Contract End Date", today.date() + datetime.timedelta(days=365))
            
            visit_type = st.selectbox("Visit Type *", ["Preventive Maintenance (PM)", "Breakdown Call / Emergency Repair", "Installation"], key="mgr_vtype")
            reason_for_visit = st.text_input("Reason / Issue", "Routine Maintenance", key="mgr_reason")

        with c_right:
            technician_name = st.text_input("Assigned Technician Name *", key="mgr_tech")
            date_of_visit = st.date_input("Date of Visit", today.date(), key="mgr_vdate")
            product_name = st.selectbox("Product Name *", ["Motorized Rolling Shutter", "Automatic Boom Barrier", "High-Speed Industrial Door", "Sliding Gate"], key="mgr_prod")
            
            service_freq = st.selectbox("Service Frequency (Visits/Year)", [2, 3, 4], index=2, key="mgr_freq")
            total_services = int(service_freq)
            
            freq_days_map = {2: 180, 3: 120, 4: 90}
            next_service_due = st.date_input("Next Service Due Date", date_of_visit + datetime.timedelta(days=freq_days_map.get(service_freq, 90)))
            contract_status = st.selectbox("Contract Status", ["Active", "Inactive", "Expiring Soon", "Pending Service"])
            uploaded_photo = st.file_uploader("Job Sheet Photo", type=["jpg", "jpeg", "png"], key="mgr_photo")

        remarks = st.text_area("Remarks", key="mgr_remarks")
        
        if st.button("Save Service Record (Manager)", key="mgr_save_btn"):
            if not client_name.strip() or not technician_name.strip():
                st.warning("Client Name and Technician Name are required!")
            else:
                base64_photo = ""
                if uploaded_photo:
                    base64_photo = base64.b64encode(uploaded_photo.read()).decode('utf-8')
                    
                record = {
                    "Visit_ID": auto_id,
                    "Client_Name": client_name.strip(),
                    "Company_Name": company_name,
                    "City": city_name.strip(),
                    "Date_of_Visit": str(date_of_visit),
                    "Address": address,
                    "Phone_Number": phone_number,
                    "Technician_Name": technician_name.strip(),
                    "Visit_Type": visit_type,
                    "Reason_for_Visit": reason_for_visit,
                    "Product_Name": product_name,
                    "Service_Frequency": service_freq,
                    "Contract_Start_Date": str(contract_start_date),
                    "Contract_End_Date": str(contract_end_date),
                    "Next_Service_Due_Date": str(next_service_due),
                    "Total_Services_Included": total_services,
                    "Services_Completed": 1,
                    "Remarks": remarks,
                    "Job_Sheet_Photo_Base64": base64_photo,
                    "Contract_Status": contract_status
                }
                
                if save_visit_to_gsheets(sheet_visits, record):
                    st.success(f"✅ Visit `{auto_id}` saved successfully!")
                    st.cache_resource.clear()
                    st.rerun()

    # --- TAB 3: RECORDS HISTORY ---
    with tab_records:
        st.dataframe(df_visits, use_container_width=True)

# ------------------------------------------
# C. TECHNICIAN PORTAL
# ------------------------------------------
else:
    tab_checkin, tab_entry, tab_history = st.tabs([
        "📍 Technician City Check-In", 
        "📝 Add New Field Visit", 
        "📊 Recent Visit History"
    ])

    # --- TAB 1: LOCATION CHECK-IN ---
    with tab_checkin:
        st.subheader("📍 Update Your Current Working Location")
        st.caption("Checking in lets the office assign you urgent local service requests in your immediate vicinity.")
        
        with st.form("tech_checkin_form"):
            t_name = st.text_input("Your Name *", placeholder="e.g. Aaryan Sharma")
            t_email = st.text_input("Your Email (For Dispatch Alerts)", placeholder="aaryan@company.com")
            t_city = st.selectbox("Current City *", ["Surat", "Ahmedabad", "Vadodara", "Rajkot", "Mumbai", "Delhi", "Pune", "Jaipur", "Other"])
            t_area = st.text_input("Specific Area / Landmark", placeholder="e.g. Ring Road / Zone 3")
            t_status = st.radio("Availability Status", ["Available", "On Job / Busy", "Finished for Day"])
            
            submit_checkin = st.form_submit_button("📍 Submit Location Check-In")
            
            if submit_checkin:
                if not t_name.strip() or not t_city.strip():
                    st.error("Name and City are required to check in!")
                else:
                    if sheet_checkins is None:
                        st.error("Check-In Worksheet is missing in Google Sheets. Please ensure Worksheet 2 exists.")
                    else:
                        if update_checkin_sheet(sheet_checkins, t_name.strip(), t_city, t_area, t_status, t_email):
                            st.success(f"✅ Location Updated! Marked as **{t_status}** in **{t_city}**.")
                            st.cache_resource.clear()
                            st.rerun()

        if not df_checkins.empty:
            st.divider()
            st.markdown("**Current Active Technicians On Field:**")
            st.dataframe(df_checkins[['Technician_Name', 'City', 'Area', 'Status', 'Last_Updated']], use_container_width=True)

    # --- TAB 2: FIELD VISIT ENTRY ---
    with tab_entry:
        st.subheader("Register AMC Visit / Emergency Call")
        auto_id = generate_visit_id()
        st.info(f"**Automated Visit ID:** `{auto_id}`")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            client_name = st.text_input("Client Name *", placeholder="Enter client/customer name")
            company_name = st.text_input("Company Name")
            city_name = st.text_input("City / Area *", "Surat")
            phone_number = st.text_input("Phone Number")
            address = st.text_area("Client Address")
            
            st.markdown("---")
            visit_type = st.selectbox("Visit Type *", ["Preventive Maintenance (PM)", "Breakdown Call / Emergency Repair", "Installation / Retrofit"])
            reason_for_visit = st.text_input("Reason / Reported Issue", value="Routine Maintenance")
            
        with col_right:
            technician_name = st.text_input("Technician Name *")
            date_of_visit = st.date_input("Date of Visit", today.date())
            product_name = st.selectbox("Product Name *", ["Motorized Rolling Shutter", "Automatic Boom Barrier", "High-Speed Industrial Door", "Sliding Gate / Fire Door", "Other"])
            service_freq = st.selectbox("Service Frequency (Visits/Year)", [2, 3, 4], index=2)
            total_services = int(service_freq)
            
            freq_days_map = {2: 180, 3: 120, 4: 90}
            default_next_due = date_of_visit + datetime.timedelta(days=freq_days_map.get(service_freq, 90))
            
            next_service_due = default_next_due
            contract_status = "Active"
            uploaded_photo = st.file_uploader("Upload Job Sheet Photo", type=["jpg", "jpeg", "png"])
        
        remarks = st.text_area("Technician Remarks / Parts Used")
        
        if st.button("Save Record to Google Sheets"):
            if not client_name.strip() or not technician_name.strip():
                st.warning("⚠️ Client Name and Technician Name are required!")
            else:
                base64_photo = ""
                if uploaded_photo is not None:
                    base64_photo = base64.b64encode(uploaded_photo.read()).decode('utf-8')
                
                record = {
                    "Visit_ID": auto_id,
                    "Client_Name": client_name.strip(),
                    "Company_Name": company_name,
                    "City": city_name.strip(),
                    "Date_of_Visit": str(date_of_visit),
                    "Address": address,
                    "Phone_Number": phone_number,
                    "Technician_Name": technician_name.strip(),
                    "Visit_Type": visit_type,
                    "Reason_for_Visit": reason_for_visit,
                    "Product_Name": product_name,
                    "Service_Frequency": service_freq,
                    "Contract_Start_Date": str(today.date()),
                    "Contract_End_Date": str(today.date() + datetime.timedelta(days=365)),
                    "Next_Service_Due_Date": str(next_service_due),
                    "Total_Services_Included": total_services,
                    "Services_Completed": 1,
                    "Remarks": remarks,
                    "Job_Sheet_Photo_Base64": base64_photo,
                    "Contract_Status": contract_status
                }
                
                if save_visit_to_gsheets(sheet_visits, record):
                    st.success(f"✅ Visit `{auto_id}` registered for {client_name.strip()}!")
                    st.cache_resource.clear()
                    st.rerun()

    # --- TAB 3: TECHNICIAN HISTORY ---
    with tab_history:
        st.subheader("🔍 Recent Visits")
        if not df_visits.empty:
            tech_hidden = ['Job_Sheet_Photo_Base64', 'Next_Service_Due_Date_DT', 'Contract_Start_Date', 'Contract_End_Date', 'Contract_Status']
            display_cols = [c for c in df_visits.columns if c not in tech_hidden]
            st.dataframe(df_visits[display_cols], use_container_width=True)
