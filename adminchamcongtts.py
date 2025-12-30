import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Admin - Quản lý Chấm công")

# Thiết lập múi giờ Việt Nam
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 2. KẾT NỐI GOOGLE SHEETS ---
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

# Định nghĩa các cột chuẩn (7 cột)
COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt']

# --- 3. FUNCTIONS ---

def load_data():
    try:
        # Lấy dữ liệu tươi từ Sheet (không dùng cache để tránh lỗi hiển thị)
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=COLUMNS)
        
        data = all_values[1:]
        headers = all_values[0]
        df = pd.DataFrame(data, columns=headers)
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame(columns=COLUMNS)

def process_entry(row_index, admin_email, status_text):
    """
    Hàm xử lý cập nhật trạng thái Duyệt hoặc Từ chối vào Sheet
    """
    try:
        now_vn = datetime.now(vn_tz)
        formatted_time = now_vn.strftime('%Y-%m-%d %H:%M:%S')
        
        # Cập nhật cột F (Cột 6): Tình trạng
        SHEET.update_cell(row_index, 6, status_text)
        
        # Cập nhật cột G (Cột 7): Người duyệt (Email + Thời gian)
        info_admin = f"{admin_email} ({formatted_time})"
        SHEET.update_cell(row_index, 7, info_admin)
        return True
    except Exception as e:
        st.error(f"Lỗi khi cập nhật Sheet: {e}")
        return False

# --- 4. GIAO DIỆN ĐĂNG NHẬP ---

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 Đăng nhập Quản trị")
    with st.form("login_form"):
        admin_user = st.text_input("Email quản trị (Gmail)", placeholder="example@koshigroup.vn")
        admin_pass = st.text_input("Mật khẩu hệ thống", type="password")
        submit = st.form_submit_button("Đăng nhập")
        
        if submit:
            # Kiểm tra đăng nhập (Thay đổi thông tin tại đây nếu cần)
            if "@koshigroup.vn" in admin_user and admin_pass == "Koshi@123": 
                st.session_state.admin_logged_in = True
                st.session_state.admin_email = admin_user
                st.rerun()
            else:
                st.error("Email không thuộc hệ thống hoặc sai mật khẩu!")
    st.stop()

# --- 5. GIAO DIỆN CHÍNH (SAU LOGIN) ---

# Sidebar quản lý tài khoản
st.sidebar.markdown(f"### 👤 Admin: \n**{st.session_state.admin_email}**")
if st.sidebar.button("Đăng xuất"):
    st.session_state.admin_logged_in = False
    st.rerun()

st.title("🔑 Hệ thống Phê duyệt Chấm công")

# Tải dữ liệu
df = load_data()

tab_pending, tab_history = st.tabs(["⏳ Chờ phê duyệt", "📜 Toàn bộ lịch sử"])

# --- TAB: CHỜ PHÊ DUYỆT ---
with tab_pending:
    # Lọc các dòng có trạng thái 'Chờ duyệt'
    pending_df = df[df['Tình trạng'] == "Chờ duyệt"]
    
    if pending_df.empty:
        st.success("✅ Hiện tại không có yêu cầu nào cần xử lý.")
    else:
        st.info(f"Đang có **{len(pending_df)}** yêu cầu cần phản hồi.")
        
        for index, row in pending_df.iterrows():
            # Tọa độ dòng thực tế trên Sheet = index dataframe + 2
            real_row_idx = index + 2
            
            # Tạo khung hiển thị cho từng yêu cầu
            with st.container(border=True):
                col_info, col_actions = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"#### 👤 Nhân viên: {row['Tên người dùng']}")
                    st.write(f"📥 **Check In:** {row['Thời gian Check in']}")
                    st.write(f"📤 **Check Out:** {row['Thời gian Check out']}")
                    st.write(f"📝 **Ghi chú:** {row['Ghi chú']}")
                
                with col_actions:
                    st.write("**Xác nhận:**")
                    
                    # NÚT DUYỆT
                    if st.button("✅ DUYỆT", key=f"app_{real_row_idx}", use_container_width=True):
                        if process_entry(real_row_idx, st.session_state.admin_email, "Đã duyệt ✅"):
                            st.toast("Đã phê duyệt thành công!")
                            st.rerun()
                    
                    # NÚT TỪ CHỐI
                    if st.button("❌ TỪ CHỐI", key=f"rej_{real_row_idx}", use_container_width=True):
                        if process_entry(real_row_idx, st.session_state.admin_email, "Từ chối ❌"):
                            st.toast("Đã từ chối yêu cầu!", icon="⚠️")
                            st.rerun()

# --- TAB: LỊCH SỬ ---
with tab_history:
    st.write("### Danh sách lịch sử chấm công")
    # Hiển thị dữ liệu mới nhất lên đầu
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

    # Nút làm mới dữ liệu
    if st.button("🔄 Làm mới dữ liệu"):
        st.rerun()
