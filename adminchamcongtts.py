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
st.sidebar.write(f"👤 Admin: **{st.session_state.admin_email}**")
if st.sidebar.button("Đăng xuất"):
    st.session_state.admin_logged_in = False
    st.rerun()

st.title("🔑 Phê duyệt & Quản lý Chấm công")

# Tải dữ liệu
df = load_data()

tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử & Bộ lọc"])

# --- TAB 1: PHÊ DUYỆT (Bổ sung lọc ngày) ---
with tab1:
    st.subheader("🔍 Lọc yêu cầu chờ duyệt")
    
    # 1. Bộ lọc ngày cho Tab 1
    col_date1, col_date2 = st.columns([1, 1])
    with col_date1:
        # Chọn ngày muốn xem (Mặc định là hôm nay)
        filter_date = st.date_input("Chọn ngày:", value=datetime.now(vn_tz), key="pending_date_filter")
        target_date_str = filter_date.strftime('%Y-%m-%d')
    
    # 2. Xử lý dữ liệu chờ duyệt
    pending = df[df['Tình trạng'] == "Chờ duyệt"].copy()
    
    if not pending.empty:
        # Lấy phần ngày (10 ký tự đầu) từ cột 'Thời gian Check in'
        pending['only_date'] = pending['Thời gian Check in'].str[:10]
        # Lọc theo ngày đã chọn
        pending_filtered = pending[pending['only_date'] == target_date_str]
    else:
        pending_filtered = pd.DataFrame()

    # 3. Hiển thị danh sách
    if pending_filtered.empty:
        st.info(f"Không có yêu cầu nào đang chờ duyệt trong ngày {target_date_str}.")
    else:
        st.warning(f"Có {len(pending_filtered)} yêu cầu chờ duyệt ngày {target_date_str}:")
        for idx, row in pending_filtered.iterrows():
            # Tính dòng thực tế trên Sheet (index gốc trong df + 2)
            real_row = idx + 2
            
            with st.container(border=True):
                st.markdown(f"### 👤 {row['Tên người dùng']}")
                st.write(f"📍 **Ghi chú:** {row['Ghi chú']}")
                st.write(f"🕒 **Vào:** {row['Thời gian Check in']} | **Ra:** {row['Thời gian Check out']}")
                
                col_app, col_rej = st.columns(2)
                with col_app:
                    if st.button("✅ DUYỆT", key=f"v_approve_{real_row}", use_container_width=True):
                        if process_action(real_row, st.session_state.admin_email, "Đã duyệt ✅"):
                            st.toast("Đã phê duyệt!")
                            st.rerun()
                with col_rej:
                    if st.button("❌ TỪ CHỐI", key=f"v_reject_{real_row}", use_container_width=True, type="primary"):
                        if process_action(real_row, st.session_state.admin_email, "Từ chối ❌"):
                            st.toast("Đã từ chối!")
                            st.rerun()

# --- TAB 2: LỊCH SỬ & BỘ LỌC TÊN ---
with tab2:
    st.subheader("🔍 Tìm kiếm lịch sử")
    list_employees = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
    
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        selected_user = st.selectbox("Lọc theo nhân viên:", list_employees)
    with col_f2:
        search_note = st.text_input("Tìm từ khóa ghi chú:", placeholder="Ví dụ: Koshi...")

    filtered_df = df.copy()
    if selected_user != "Tất cả":
        filtered_df = filtered_df[filtered_df['Tên người dùng'] == selected_user]
    if search_note:
        filtered_df = filtered_df[filtered_df['Ghi chú'].str.contains(search_note, case=False, na=False)]

    st.dataframe(filtered_df.iloc[::-1], use_container_width=True, hide_index=True)
    
    if st.button("🔄 Làm mới dữ liệu", key="refresh_btn"):
        st.rerun()
