import io
import os
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sidharth AMC Tracker",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. HELPER FUNCTIONS & DATABASE SETUP
# -----------------------------------------------------------------------------
def get_logo_path():
    """Returns local path to logo if it exists."""
    possible_paths = ["logo.png", "logo.jpg", "logo.jpeg", "assets/logo.png"]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def upload_to_gdrive(file_obj, folder_id):
    """Uploads a Streamlit UploadedFile object directly to Google Drive."""
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info, 
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    
    drive_service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': file_obj.name,
        'parents': [folder_id]
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_obj.getbuffer()), 
        mimetype=file_obj.type, 
        resumable=True
    )

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    return uploaded_file.get('webViewLink')

# Mock Users Database setup
if "users_db" not in st.session_state:
    st.session_state.users_db = pd.DataFrame([
        {"User_ID": "TECH01", "Password": "123", "Name": "Technician 1", "Role": "Technician"}
    ])

# Target Google Drive Folder ID
GDRIVE_FOLDER_ID = st.secrets.get("GDRIVE_FOLDER_ID", "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE")

# -----------------------------------------------------------------------------
# 3. BRANDED UI STYLING
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-highlight"] { background-color: #1565C0 !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #1565C0 !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #F8FAFC !important; }
    .sidebar-logo-sub { color: #70B244; font-weight: 800; font-size: 0.95rem; letter-spacing: 1.5px; text-align: center; margin-top: 6px; }
    
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
        border: 1px solid #E2E8F0; 
        border-radius: 16px; 
        padding: 24px; 
    }
    
    /* Login Screen Card */
    .login-container div[data-testid="stForm"] { 
        padding: 32px 36px !important; 
        max-width: 400px; 
        margin: 0 auto; 
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04) !important;
        background-color: #FFFFFF !important;
    }

    .login-header-title {
        text-align: center; 
        color: #0D47A1; 
        margin: 10px 0 0 0;
        font-size: 1.8rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }

    .login-header-sub {
        text-align: center; 
        color: #70B244; /* Exact Green accent color */
        font-size: 1.1rem;
        font-weight: 800;
        letter-spacing: 1.5px;
        margin-top: 6px;
        margin-bottom: 20px;
        text-transform: uppercase;
    }

    div[data-baseweb="select"] { background-color: transparent !important; }
    div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
    }
    
    .equipment-box {
        background-color: #F8FAFC;
        border-left: 5px solid #0F172A;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 20px;
    }
    .equipment-title {
        color: #0F172A !important;
        font-weight: 700;
        margin: 0 0 10px 0;
        font-size: 1.25rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. LOGIN SCREEN
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([1, 1.2, 1])

    with col_center:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        with st.form("login_form"):
            logo_path = get_logo_path()
            if logo_path:
                st.image(logo_path, use_container_width=True)
            else:
                st.markdown("<div class='login-header-title'>⚙️ SIDHARTH</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='login-header-sub'>AMC TRACKER</div>", unsafe_allow_html=True)
            
            user_id_input = st.text_input("User ID", placeholder="e.g. TECH01").strip().upper()
            password_input = st.text_input("Password", type="password", placeholder="Enter password").strip()
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            
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
# 5. MAIN DASHBOARD UI
# -----------------------------------------------------------------------------
# Sidebar
with st.sidebar:
    logo_path = get_logo_path()
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("### ⚙️ SIDHARTH")
    st.markdown("<div class='sidebar-logo-sub'>AMC TRACKER</div>", unsafe_allow_html=True)
    st.divider()
    st.write(f"**Logged in as:** {st.session_state.user['Name']}")
    if st.button("Log Out"):
        st.session_state.user = None
        st.rerun()

# Main Header
top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.title("Technician Portal")
with top_col2:
    if st.button("📊 View Task Summary"):
        st.info("Task Summary Clicked")

# Tabs Layout
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Assigned Work Orders", 
    "📝 Submit Client Service Report", 
    "📍 Update Status & Destination", 
    "📜 Service History"
])

# -----------------------------------------------------------------------------
# TAB 1: ASSIGNED WORK ORDERS
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Assigned Work Orders")
    st.info("No pending work orders currently assigned.")

# -----------------------------------------------------------------------------
# TAB 2: SUBMIT CLIENT SERVICE REPORT (WITH GOOGLE DRIVE PHOTO UPLOAD)
# -----------------------------------------------------------------------------
with tab2:
    st.title("📝 Submit Client Service Report")
    
    with st.form("client_service_report_form"):
        st.markdown("#### **1. Service Details**")
        work_order_id = st.text_input("Work Order ID", placeholder="e.g. WO-1024")
        client_name = st.text_input("Client Name", placeholder="Enter Client Name")
        service_summary = st.text_area("Service Summary / Work Completed", placeholder="Describe service action taken...")
        
        st.markdown("---")
        st.markdown("#### **2. 📸 Service Photos**")
        
        uploaded_photos = st.file_uploader(
            "Attach photos (e.g., equipment condition, before/after, or parts installed)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="service_report_photos"
        )

        # Image Previews
        if uploaded_photos:
            st.markdown("**Preview Photos:**")
            cols = st.columns(min(len(uploaded_photos), 4))
            for idx, photo in enumerate(uploaded_photos):
                with cols[idx % 4]:
                    st.image(photo, caption=photo.name, use_container_width=True)

        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        submit_report = st.form_submit_button("Submit Service Report")

    # Form Submission Handler
    if submit_report:
        if not work_order_id or not client_name:
            st.error("Please fill in the required Work Order ID and Client Name.")
        else:
            photo_urls = []
            
            # Upload photos to Google Drive
            if uploaded_photos:
                with st.spinner("Uploading photos to Google Drive..."):
                    for photo in uploaded_photos:
                        try:
                            file_url = upload_to_gdrive(photo, GDRIVE_FOLDER_ID)
                            if file_url:
                                photo_urls.append(file_url)
                        except Exception as e:
                            st.error(f"Failed to upload photo {photo.name}: {e}")

            st.success(f"✅ Service Report for **{work_order_id}** submitted successfully!")
            if photo_urls:
                st.markdown(f"**Saved Photos ({len(photo_urls)}):**")
                for url in photo_urls:
                    st.markdown(f"- [View Photo in Google Drive]({url})")

# -----------------------------------------------------------------------------
# TAB 3: UPDATE STATUS & DESTINATION
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Update Status & Destination")
    st.selectbox("Current Status", ["En Route", "On Site", "Completed", "On Hold"])

# -----------------------------------------------------------------------------
# TAB 4: SERVICE HISTORY
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("Service History")
    st.write("Past completed reports will appear here.")
