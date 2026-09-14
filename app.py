import streamlit as st
import pandas as pd
import datetime
import base64
import uuid
import io
import os
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="Annual Maintenance Contract Tracker",
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GOOGLE SHEETS AUTHENTICATION
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
        sheet = client.open_by_url(spreadsheet_url).get_worksheet(0)
        return sheet
    else:
        st.error("Google Sheets configuration missing in `.streamlit/secrets.toml`!")
        st.stop()

def fetch_all_visits(sheet):
    """Retrieves all records from Google Sheets into a DataFrame."""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")
        return pd.DataFrame()

def save_visit_to_gsheets(sheet, record_dict):
    """Appends dynamic record fields to the Google Sheet."""
    try:
        headers = sheet.row_values(1)
        row = [str(record_dict.get(h, "")) for h in headers]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Failed to append row to Google Sheet: {e}")
        return False

def generate_visit_id():
    """Generates an automated unique Visit ID."""
    return f"AMC-{datetime.date.today().year}-{uuid.uuid4().hex[:5].upper()}"

# Initialize Connection & Load Data
sheet = get_gspread_client()
df = fetch_all_visits(sheet)

# Ensure essential numerical types on data read
if not df.empty:
    df['Total_Services_Included'] = pd.to_numeric(df.get('Total_Services_Included', 0), errors='coerce').fillna(0).astype(int)
    df['Services_Completed'] = pd.to_numeric(df.get('Services_Completed', 0), errors='coerce').fillna(0).astype(int)
    df['Pending_Services'] = df['Total_Services_Included'] - df['Services_Completed']
    df['Pending_Services'] = df['Pending_Services'].apply(lambda x: max(0, x))

# ==========================================
# 3. BRANDED HEADER
# ==========================================
header_title_col, header_logo_col = st.columns([3, 1])

with header_title_col:
    st.title("Annual Maintenance Contract Tracker")
    st.markdown("<p style='color: #475569; font-size: 1.1rem; margin-top: -10px;'>Sidharth Shutter & Automation — Service Portal</p>", unsafe_allow_html=True)

with header_logo_col:
    logo_path = None
    for ext in ["Company Logo.jpeg", "Company Logo.jpg", "Company Logo.png"]:
        if os.path.exists(ext):
            logo_path = ext
            break
            
    if logo_path:
        st.image(logo_path, use_container_width=True)

st.divider()

# ==========================================
# 4. AUTOMATED BUSINESS METRICS & DASHBOARD
# ==========================================
today = pd.Timestamp.today().normalize()

if not df.empty:
    if 'Next_Service_Due_Date' in df.columns:
        df['Next_Service_Due_Date_DT'] = pd.to_datetime(df['Next_Service_Due_Date'], errors='coerce')
    else:
        df['Next_Service_Due_Date_DT'] = pd.NaT

    # Status Counts
    active_count = len(df[df['Contract_Status'] == 'Active']) if 'Contract_Status' in df.columns else 0
    inactive_count = len(df[df['Contract_Status'] == 'Inactive']) if 'Contract_Status' in df.columns else 0
    expiring_count = len(df[df['Contract_Status'] == 'Expiring Soon']) if 'Contract_Status' in df.columns else 0

    # Auto-flag Pending Services (Due Date <= Today or Status == Pending Service OR Pending_Services > 0)
    pending_df = df[
        (df.get('Contract_Status') == 'Pending Service') | 
        (df['Pending_Services'] > 0) |
        ((df['Next_Service_Due_Date_DT'].notna()) & 
         (df['Next_Service_Due_Date_DT'] <= today))
    ].copy()
    
    # Keep only the latest record per client to calculate accurate pending counts
    if not pending_df.empty and 'Client_Name' in pending_df.columns:
        latest_pending_per_client = pending_df.sort_values('Date_of_Visit').groupby(['Client_Name', 'Product_Name']).last().reset_index()
    else:
        latest_pending_per_client = pd.DataFrame()

    pending_count = len(latest_pending_per_client)

    if 'Visit_Type' in df.columns:
        breakdown_df = df[df['Visit_Type'] == 'Breakdown Call / Emergency Repair']
    else:
        breakdown_df = pd.DataFrame()
    breakdown_count = len(breakdown_df)

else:
    active_count, inactive_count, expiring_count, pending_count, breakdown_count = 0, 0, 0, 0, 0
    pending_df, breakdown_df, latest_pending_per_client = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Main Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Active Contracts", active_count)
c2.metric("Clients Pending Services", pending_count)
c3.metric("Expiring Soon", expiring_count)
c4.metric("Breakdown Calls", breakdown_count)

st.write("")

# Action Alert Expander (Per-Client Pending Breakdown)
if not latest_pending_per_client.empty:
    with st.expander("🚨 Action Required: Client Pending Service Breakdown", expanded=False):
        st.warning(f"**Clients with Remaining Pending Visits ({len(latest_pending_per_client)})**")
        
        display_cols = [c for c in ['Client_Name', 'Company_Name', 'Product_Name', 'Next_Service_Due_Date', 'Services_Completed', 'Total_Services_Included', 'Pending_Services', 'Phone_Number'] if c in latest_pending_per_client.columns]
        st.dataframe(
            latest_pending_per_client[display_cols].rename(columns={
                'Services_Completed': 'Completed',
                'Total_Services_Included': 'Total Contracted',
                'Pending_Services': 'Remaining Pending Visits'
            }), 
            use_container_width=True
        )

st.divider()

# ==========================================
# 5. ENTRY FORM & RECORDS HISTORY TABS
# ==========================================
tab1, tab2 = st.tabs(["📝 Add New Field Visit", "📊 Visit History & Records"])

# --- TAB 1: AUTOMATED FORM ENTRY ---
with tab1:
    st.subheader("Register AMC Visit / Emergency Call")
    
    auto_id = generate_visit_id()
    st.info(f"**Automated Visit ID:** `{auto_id}`")
    
    col_left, col_right = st.columns(2)
    
    # Extract Client list for quick lookup automation
    existing_clients = sorted(df['Client_Name'].dropna().unique().tolist()) if not df.empty and 'Client_Name' in df.columns else []
    
    with col_left:
        client_selection_mode = st.radio("Client Input Mode", ["Existing Client", "New Client"], horizontal=True)
        
        if client_selection_mode == "Existing Client" and existing_clients:
            client_name = st.selectbox("Select Client Name *", existing_clients)
            client_records = df[df['Client_Name'] == client_name] if not df.empty else pd.DataFrame()
            
            default_company = client_records['Company_Name'].iloc[-1] if not client_records.empty and 'Company_Name' in client_records.columns else ""
            default_phone = client_records['Phone_Number'].iloc[-1] if not client_records.empty and 'Phone_Number' in client_records.columns else ""
            default_address = client_records['Address'].iloc[-1] if not client_records.empty and 'Address' in client_records.columns else ""
        else:
            client_name = st.text_input("Client Name *")
            default_company, default_phone, default_address = "", "", ""

        company_name = st.text_input("Company Name", value=default_company)
        phone_number = st.text_input("Phone Number", value=default_phone)
        address = st.text_area("Client Address", value=default_address)
        
        st.markdown("---")
        visit_type = st.selectbox(
            "Visit Type *",
            ["Preventive Maintenance (PM)", "Breakdown Call / Emergency Repair", "Installation / Retrofit"]
        )
        reason_for_visit = st.text_input("Reason / Reported Issue", value="Routine Maintenance")
        
    with col_right:
        technician_name = st.text_input("Technician Name *")
        date_of_visit = st.date_input("Date of Visit", today.date())
        
        product_name = st.selectbox(
            "Product Name *",
            ["Motorized Rolling Shutter", "Automatic Boom Barrier", "High-Speed Industrial Door", "Sliding Gate / Fire Door", "Other"]
        )
        
        service_freq = st.selectbox("Service Frequency (Visits/Year)", [2, 3, 4], index=2)
        total_services = int(service_freq)
        
        # Calculate Automated Progress Lookup based on Client + Product
        prev_completed = 0
        if not df.empty and client_name and 'Client_Name' in df.columns and 'Product_Name' in df.columns:
            matched = df[(df['Client_Name'].str.lower() == client_name.lower()) & (df['Product_Name'] == product_name)]
            if not matched.empty:
                prev_completed = int(matched['Services_Completed'].iloc[-1])
        
        auto_completed = prev_completed + 1
        if auto_completed > total_services:
            auto_completed = total_services
            
        auto_pending = total_services - auto_completed
        
        st.write(f"📊 **Automated Progress Status:** Completed `{auto_completed}` of `{total_services}` services (`{auto_pending}` Pending)")
        
        freq_days_map = {2: 180, 3: 120, 4: 90}
        default_next_due = date_of_visit + datetime.timedelta(days=freq_days_map.get(service_freq, 90))
        next_service_due = st.date_input("Next Service Due Date", default_next_due)
        
        contract_status = st.selectbox("Contract Status", ["Active", "Inactive", "Expiring Soon", "Pending Service"])
        uploaded_photo = st.file_uploader("Upload Job Sheet Photo", type=["jpg", "jpeg", "png"])
    
    remarks = st.text_area("Technician Remarks / Parts Used")
    
    if st.button("Save Record to Google Sheets"):
        if not client_name or not technician_name:
            st.warning("⚠️ Client Name and Technician Name are required!")
        else:
            base64_photo = ""
            if uploaded_photo is not None:
                image_bytes = uploaded_photo.read()
                base64_photo = base64.b64encode(image_bytes).decode('utf-8')
            
            record = {
                "Visit_ID": auto_id,
                "Client_Name": client_name,
                "Company_Name": company_name,
                "Date_of_Visit": str(date_of_visit),
                "Address": address,
                "Phone_Number": phone_number,
                "Technician_Name": technician_name,
                "Visit_Type": visit_type,
                "Reason_for_Visit": reason_for_visit,
                "Product_Name": product_name,
                "Service_Frequency": service_freq,
                "Next_Service_Due_Date": str(next_service_due),
                "Total_Services_Included": total_services,
                "Services_Completed": auto_completed,
                "Remarks": remarks,
                "Job_Sheet_Photo_Base64": base64_photo,
                "Contract_Status": contract_status
            }
            
            if save_visit_to_gsheets(sheet, record):
                st.success(f"✅ Visit `{auto_id}` registered! ({auto_completed}/{total_services} Completed - {auto_pending} Pending)")
                st.cache_resource.clear()
                st.rerun()

# --- TAB 2: HISTORY & SEARCH BY VISIT ID ---
with tab2:
    st.subheader("🔍 Visit Search & Historical Records")
    
    if df.empty:
        st.info("No records currently stored in Google Sheets.")
    else:
        f_col1, f_col2 = st.columns([2, 1])
        with f_col1:
            search_visit_id = st.text_input("🔍 Search by Visit ID (e.g., AMC-2026-XXXXX)", "").strip()
        with f_col2:
            status_filter = st.selectbox("Filter Status", ["All", "Active", "Inactive", "Expiring Soon", "Pending Service"])

        filtered_df = df.copy()
        
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Contract_Status'] == status_filter]

        if search_visit_id:
            filtered_df = filtered_df[filtered_df['Visit_ID'].astype(str).str.contains(search_visit_id, case=False, na=False)]

        display_cols = [c for c in filtered_df.columns if c not in ['Job_Sheet_Photo_Base64', 'Next_Service_Due_Date_DT']]
        st.dataframe(filtered_df[display_cols], use_container_width=True)

        st.divider()
        st.subheader("📋 Detailed Visit Inspection & Job Sheet")

        if search_visit_id:
            exact_match = df[df['Visit_ID'].astype(str).str.lower() == search_visit_id.lower()]
            
            if exact_match.empty:
                st.warning(f"No visit record found matching Visit ID: `{search_visit_id}`")
            else:
                row = exact_match.iloc[0]
                tot = int(row.get('Total_Services_Included', 0))
                comp = int(row.get('Services_Completed', 0))
                pend = max(0, tot - comp)
                
                with st.expander(f"📌 Complete Details for Visit ID: {row['Visit_ID']}", expanded=True):
                    d_col1, d_col2 = st.columns(2)
                    
                    with d_col1:
                        st.markdown(f"**Client Name:** {row.get('Client_Name', 'N/A')}")
                        st.markdown(f"**Company Name:** {row.get('Company_Name', 'N/A')}")
                        st.markdown(f"**Date of Visit:** {row.get('Date_of_Visit', 'N/A')}")
                        st.markdown(f"**Phone Number:** {row.get('Phone_Number', 'N/A')}")
                        st.markdown(f"**Address:** {row.get('Address', 'N/A')}")
                        st.markdown(f"**Visit Type:** {row.get('Visit_Type', 'N/A')}")
                        
                    with d_col2:
                        st.markdown(f"**Technician Name:** {row.get('Technician_Name', 'N/A')}")
                        st.markdown(f"**Product Name:** {row.get('Product_Name', 'N/A')}")
                        st.markdown(f"**Contract Status:** {row.get('Contract_Status', 'N/A')}")
                        st.markdown(f"**Next Service Due:** {row.get('Next_Service_Due_Date', 'N/A')}")
                        st.markdown(f"**Services Breakdown:** {comp} Completed / {pend} Pending (Total {tot})")
                        st.markdown(f"**Remarks:** {row.get('Remarks', 'N/A')}")
                    
                    photo_b64 = str(row.get('Job_Sheet_Photo_Base64', ''))
                    if len(photo_b64) > 10:
                        st.subheader("🖼️ Uploaded Job Sheet Photo")
                        try:
                            img_data = base64.b64decode(photo_b64)
                            img = Image.open(io.BytesIO(img_data))
                            st.image(img, caption=f"Job Sheet Photo for {row['Visit_ID']}", width=450)
                        except Exception as e:
                            st.error(f"Error rendering image: {e}")
                    else:
                        st.info("No job sheet photo was uploaded for this visit.")
        else:
            st.caption("👈 Enter a specific **Visit ID** in the search bar above to view complete visit details and its associated Job Sheet photo.")
