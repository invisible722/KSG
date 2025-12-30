import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Admin - Quản lý Chấm công")

# Thiết lập múi giờ Việt Nam
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# --- KẾT NỐI GOOGLE SHEETS ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
    
    decoded_json_bytes = base64.b64decode(BASE64_CREDS)
    CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi cấu hình/kết nối: {e}")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt']

# --- FUNCTIONS ---

def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=COLUMNS)
        
        data = all_values[1:]
        headers = all_values[0]
        df = pd.DataFrame(data, columns=headers)
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()

# Hàm xử lý chung cho cả Duyệt và Từ chối
def process_entry(row_index, admin_email, status):
    try:
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now_vn = datetime.now(vn_tz)
        formatted_time = now_vn.strftime('%Y-%m-%d %H:%M:%S')
        
        # Cập nhật cột F (Tình trạng)
        SHEET.update_cell(row_index, 6, status)
        # Cập nhật cột G (Người duyệt + Thời gian)
        info_admin = f"{admin_email} ({formatted_time})"
        SHEET.update_cell(row_index, 7, info_admin)
        return True
    except:
        return False

# --- GIAO DIỆN ĐĂNG NHẬP ---

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 Đăng nhập Quản trị")
    with st.form("login_form"):
        admin_user = st.text_input("Email quản trị (Gmail)", placeholder="example@koshigroup.vn")
        admin_pass = st.text_input("Mật khẩu truy cập hệ thống", type="password")
        submit = st.form_submit_button("Đăng nhập")
        
        if submit:
            if "@koshigroup.vn" in admin_user and admin_pass == "Koshi@123": 
                st.session_state.admin_logged_in = True
                st.session_state.admin_email = admin_user
                st.rerun()
            else:
                st.error("Email không hợp lệ hoặc sai mật khẩu!")
    st.stop()

# --- GIAO DIỆN SAU KHI ĐĂNG NHẬP ---

st.sidebar.write(f"👤 Admin: **{st.session_state.admin_email}**")
if st.sidebar.button("Đăng xuất"):
    st.session_state.admin_logged_in = False
    st.rerun()

st.title("🔑 Hệ thống Phê duyệt Chấm công")

df = load_data()
tab_pending, tab_history = st.tabs(["⏳ Chờ phê duyệt", "📜 Toàn bộ lịch sử"])

with tab_pending:
    # Đảm bảo lọc đúng cột 'Tình trạng'
    pending_df = df[df['Tình trạng'] == "Chờ duyệt"]
    
    if pending_df.empty:
        st.success("Không có yêu cầu nào cần xử lý.")
    else:
        for index, row in pending_df.iterrows():
            real_row_index = index + 2
            
            with st.expander(f"Yêu cầu từ: {row['Tên người dùng']}"):
                col_info, col_btn1, col_btn2 = st.columns([3, 1, 1])
                
                with col_info:
                    st.write(f"**Check In:** {row['Thời gian Check in']}")
                    st.write(f"**Check Out:** {row['Thời gian Check out']}")
                    st.write(f"**Ghi chú:** {row['Ghi chú']}")
                
                # Nút Phê duyệt
                with col_btn1:
                    if st.button("PHÊ DUYỆT ✅", key=f"app_{real_row_index}", use_container_width=True):
                        if process_entry(real_row_index, st.session_state.admin_email, "Đã duyệt ✅"):
                            st.success("Đã phê duyệt!")
                            st.rerun()
                
                # Nút Từ chối
                with col_btn2:
                    if st.button("TỪ CHỐI ❌", key=f"rej_{real_row_index}", use_container_width=True):
                        if process_entry(real_row_index, st.session_state.admin_email, "Từ chối ❌"):
                            st.warning("Đã từ chối yêu cầu!")
                            st.rerun()

with tab_history:
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
