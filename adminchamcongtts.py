import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Admin - Quản lý Chấm công")
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
    st.error(f"Lỗi cấu hình: {e}")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt']

# --- 3. FUNCTIONS ---

def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1: return pd.DataFrame(columns=COLUMNS)
        return pd.DataFrame(all_values[1:], columns=all_values[0])
    except:
        return pd.DataFrame(columns=COLUMNS)

def process_action(row_idx, admin_email, status_label):
    try:
        now_str = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
        # Cập nhật cột F (6) và G (7)
        SHEET.update_cell(row_idx, 6, status_label)
        SHEET.update_cell(row_idx, 7, f"{admin_email} ({now_str})")
        return True
    except:
        return False

# --- 4. LOGIN ---
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 Đăng nhập Quản trị")
    with st.form("login"):
        user = st.text_input("Email", placeholder="admin@koshigroup.vn")
        pw = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Vào hệ thống"):
            if "@koshigroup.vn" in user and pw == "Koshi@123":
                st.session_state.admin_logged_in = True
                st.session_state.admin_email = user
                st.rerun()
            else: st.error("Sai tài khoản!")
    st.stop()

# --- 5. GIAO DIỆN CHÍNH ---
st.sidebar.write(f"Đang dùng: {st.session_state.admin_email}")
if st.sidebar.button("Thoát"):
    st.session_state.admin_logged_in = False
    st.rerun()

st.title("🔑 Phê duyệt Chấm công")
df = load_data()

tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử"])

with tab1:
    # Lọc danh sách chờ duyệt
    pending = df[df['Tình trạng'] == "Chờ duyệt"]
    
    if pending.empty:
        st.success("Hết yêu cầu chờ duyệt!")
    else:
        for idx, row in pending.iterrows():
            real_row = idx + 2
            # Tạo một khung bao quanh mỗi yêu cầu
            with st.container(border=True):
                st.markdown(f"### 👤 {row['Tên người dùng']}")
                st.write(f"📍 **Ghi chú:** {row['Ghi chú']}")
                st.write(f"🕒 **Vào:** {row['Thời gian Check in']} | **Ra:** {row['Thời gian Check out']}")
                
                # CHIA CỘT NÚT BẤM (ÉP HIỆN 2 NÚT)
                col_app, col_rej = st.columns(2)
                
                with col_app:
                    if st.button("✅ DUYỆT", key=f"v_approve_{real_row}", use_container_width=True):
                        if process_action(real_row, st.session_state.admin_email, "Đã duyệt ✅"):
                            st.success("Đã duyệt!")
                            st.rerun()
                
                with col_rej:
                    # Nút từ chối dùng màu đỏ (primary) để nổi bật
                    if st.button("❌ TỪ CHỐI", key=f"v_reject_{real_row}", use_container_width=True, type="primary"):
                        if process_action(real_row, st.session_state.admin_email, "Từ chối ❌"):
                            st.warning("Đã từ chối!")
                            st.rerun()

with tab2:
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
