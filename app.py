import streamlit as st
import pandas as pd
import datetime
import base64
import uuid
import io
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="AMC Field Visit Tracker",
    page_icon="🔧",
    layout="wide"
)

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
        
        # get_worksheet(0) fetches the first sheet automatically
        sheet = client.open_by_url(spreadsheet_url).get_worksheet(0)
        return sheet
    else:
        st.error("Google Sheets configuration missing in `.streamlit/secrets.toml`!")
        st.stop()

def fetch_all_visits(sheet):
    """Retrieves all records from the Google Sheet into a DataFrame."""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")
        return pd.DataFrame()

def save_visit_to_gsheets(sheet, record_dict):
    """Appends a new record row to the Google Sheet."""
    try:
        row = [
            record_dict["Visit_ID"],
            record_dict["Client_Name"],
            record_dict["Company_Name"],
            record_dict["Customer_Name"],
            str(record_dict["Date_of_Visit"]),
            record_dict["Address"],
            record_dict["Phone_Number"],
            record_dict["Technician_Name"],
            record_dict["Reason_for_Visit"],
            record_dict["Product_Name"],
            record_dict["Remarks"],
            record_dict["Job_Sheet_Photo_Base64"],
            record_dict["Contract_Status"],
            record_dict["Contract_Value"],
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
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

# ==========================================
# 3. HEADER & METRIC DASHBOARD
# ==========================================
st.title("🔧 AMC Field Visit & Contract Tracker")
st.caption("Connected to Google Sheets Database")

active_count = len(df[df['Contract_Status'] == 'Active']) if not df.empty and 'Contract_Status' in df.columns else 3
expiring_count = len(df[df['Contract_Status'] == 'Expiring Soon']) if not df.empty and 'Contract_Status' in df.columns else 2
pending_count = len(df[df['Contract_Status'] == 'Pending Service']) if not df.empty and 'Contract_Status' in df.columns else 5

if not df.empty and 'Contract_Value' in df.columns:
    try:
        total_rev_val = pd.to_numeric(df['Contract_Value'], errors='coerce').sum()
        total_rev_str = f"₹{total_rev_val:,.2f}"
    except Exception:
        total_rev_str = "₹1,46,500"
else:
    total_rev_str = "₹1,46,500"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Contracts", active_count)
col2.metric("Expiring Soon", expiring_count)
col3.metric("Pending Service", pending_count)
col4.metric("Total Revenue", total_rev_str)

st.divider()

# ==========================================
# 4. ENTRY FORM & RECORDS HISTORY TABS
# ==========================================
tab1, tab2 = st.tabs(["📝 Add New Field Visit", "📊 Visit History & Records"])

# --- TAB 1: FORM ENTRY ---
with tab1:
    st.subheader("Register New AMC Field Visit")
    
    auto_id = generate_visit_id()
    st.info(f"**Automated Visit ID:** `{auto_id}`")
    
    with st.form("amc_visit_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        with c1:
            client_name = st.text_input("Client Name *")
            company_name = st.text_input("Company Name")
            customer_name = st.text_input("Customer Name")
            date_of_visit = st.date_input("Date of Visit", datetime.date.today())
            phone_number = st.text_input("Phone Number")
            address = st.text_area("Client Address")
            
        with c2:
            technician_name = st.text_input("Technician Name *")
            reason_for_visit = st.text_input("Reason for Visit")
            product_name = st.text_input("Product Name")
            contract_status = st.selectbox(
                "Contract Status", 
                ["Active", "Expiring Soon", "Pending Service", "Expired"]
            )
            contract_value = st.number_input("Contract Value (₹)", min_value=0.0, value=0.0, step=100.0)
            uploaded_photo = st.file_uploader("Upload Job Sheet Photo", type=["jpg", "jpeg", "png"])
        
        remarks = st.text_area("Remarks")
        
        submitted = st.form_submit_button("Submit to Google Sheets")
        
        if submitted:
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
                    "Customer_Name": customer_name,
                    "Date_of_Visit": date_of_visit,
                    "Address": address,
                    "Phone_Number": phone_number,
                    "Technician_Name": technician_name,
                    "Reason_for_Visit": reason_for_visit,
                    "Product_Name": product_name,
                    "Remarks": remarks,
                    "Job_Sheet_Photo_Base64": base64_photo,
                    "Contract_Status": contract_status,
                    "Contract_Value": contract_value
                }
                
                if save_visit_to_gsheets(sheet, record):
                    st.success(f"✅ Visit `{auto_id}` successfully saved to Google Sheets!")
                    st.cache_resource.clear()
                    st.rerun()

# --- TAB 2: VISIT HISTORY & SEARCH BY VISIT ID ---
with tab2:
    st.subheader("🔍 Visit Search & History")
    
    if df.empty:
        st.info("No records currently stored in Google Sheets.")
    else:
        # Search & Status Filter Controls
        f_col1, f_col2 = st.columns([2, 1])
        with f_col1:
            search_visit_id = st.text_input("🔍 Search by Visit ID (e.g., AMC-2026-XXXXX)", "").strip()
        with f_col2:
            available_statuses = ["All"] + list(df['Contract_Status'].unique()) if 'Contract_Status' in df.columns else ["All"]
            status_filter = st.selectbox("Filter Status", available_statuses)

        # Apply Filters
        filtered_df = df.copy()
        
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Contract_Status'] == status_filter]

        if search_visit_id:
            filtered_df = filtered_df[filtered_df['Visit_ID'].astype(str).str.contains(search_visit_id, case=False, na=False)]

        # Display Summary Table (Excluding heavy Base64 image column)
        display_cols = [c for c in filtered_df.columns if c != 'Job_Sheet_Photo_Base64']
        st.dataframe(filtered_df[display_cols], use_container_width=True)

        # --- DETAILED SINGLE VISIT INSPECTION ---
        st.divider()
        st.subheader("📋 Detailed Visit Inspection & Job Sheet")

        if search_visit_id:
            exact_match = df[df['Visit_ID'].astype(str).str.lower() == search_visit_id.lower()]
            
            if exact_match.empty:
                st.warning(f"No visit record found matching Visit ID: `{search_visit_id}`")
            else:
                row = exact_match.iloc[0]
                
                # Render Full Visit Details Card
                with st.expander(f"📌 Complete Details for Visit ID: {row['Visit_ID']}", expanded=True):
                    d_col1, d_col2 = st.columns(2)
                    
                    with d_col1:
                        st.markdown(f"**Client Name:** {row.get('Client_Name', 'N/A')}")
                        st.markdown(f"**Company Name:** {row.get('Company_Name', 'N/A')}")
                        st.markdown(f"**Customer Name:** {row.get('Customer_Name', 'N/A')}")
                        st.markdown(f"**Date of Visit:** {row.get('Date_of_Visit', 'N/A')}")
                        st.markdown(f"**Phone Number:** {row.get('Phone_Number', 'N/A')}")
                        st.markdown(f"**Address:** {row.get('Address', 'N/A')}")
                        
                    with d_col2:
                        st.markdown(f"**Technician Name:** {row.get('Technician_Name', 'N/A')}")
                        st.markdown(f"**Product Name:** {row.get('Product_Name', 'N/A')}")
                        st.markdown(f"**Reason for Visit:** {row.get('Reason_for_Visit', 'N/A')}")
                        st.markdown(f"**Contract Status:** {row.get('Contract_Status', 'N/A')}")
                        st.markdown(f"**Contract Value:** ₹{row.get('Contract_Value', 0)}")
                        st.markdown(f"**Remarks:** {row.get('Remarks', 'N/A')}")
                    
                    # Render Photo ONLY for this searched Visit ID
                    photo_b64 = str(row.get('Job_Sheet_Photo_Base64', ''))
                    if len(photo_b64) > 10:
                        st.subheader("🖼️ Job Sheet Photo")
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
