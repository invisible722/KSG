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

df = load_data()
tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử & Bộ lọc"])

# --- TAB 1: PHÊ DUYỆT ---
with tab1:
    st.subheader("🔍 Lọc yêu cầu chờ duyệt")
    
    # Lấy danh sách nhân viên để lọc (Lấy từ toàn bộ DF để dropdown luôn có dữ liệu)
    all_employee_names = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
    
    # KHU VỰC BỘ LỌC - Đặt ngoài điều kiện if để luôn hiển thị
    c1, c2 = st.columns(2)
    with c1:
        filter_date = st.date_input("Chọn ngày:", value=datetime.now(vn_tz), key="final_p_date")
    with c2:
        filter_user = st.selectbox("Chọn nhân viên:", all_employee_names, key="final_p_user")

    # XỬ LÝ DỮ LIỆU
    target_date_str = filter_date.strftime('%Y-%m-%d')
    pending = df[df['Tình trạng'] == "Chờ duyệt"].copy()
    
    if not pending.empty:
        pending['only_date'] = pending['Thời gian Check in'].str[:10]
        
        # Lọc 1: Ngày
        mask = (pending['only_date'] == target_date_str)
        # Lọc 2: Tên (nếu không chọn Tất cả)
        if filter_user != "Tất cả":
            mask = mask & (pending['Tên người dùng'] == filter_user)
            
        final_pending = pending[mask]

        if final_pending.empty:
            st.info(f"Không có yêu cầu nào của **{filter_user}** trong ngày **{target_date_str}**.")
        else:
            st.warning(f"Có {len(final_pending)} yêu cầu chờ duyệt:")
            for idx, row in final_pending.iterrows():
                real_row = idx + 2
                with st.container(border=True):
                    st.markdown(f"### 👤 {row['Tên người dùng']}")
                    st.write(f"📍 **Ghi chú:** {row['Ghi chú']}")
                    st.write(f"🕒 **Vào:** {row['Thời gian Check in']} | **Ra:** {row['Thời gian Check out']}")
                    
                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        if st.button("✅ DUYỆT", key=f"v_app_{real_row}", use_container_width=True):
                            if process_action(real_row, st.session_state.admin_email, "Đã duyệt ✅"):
                                st.toast("Đã duyệt!")
                                st.rerun()
                    with btn_c2:
                        if st.button("❌ TỪ CHỐI", key=f"v_rej_{real_row}", use_container_width=True, type="primary"):
                            if process_action(real_row, st.session_state.admin_email, "Từ chối ❌"):
                                st.toast("Đã từ chối!")
                                st.rerun()
    else:
        st.success("Hiện tại không có yêu cầu nào đang chờ phê duyệt trên hệ thống.")

# --- TAB 2: LỊCH SỬ ---
with tab2:
    st.subheader("📜 Toàn bộ lịch sử")
    all_users_hist = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
    
    h1, h2 = st.columns(2)
    u_hist = h1.selectbox("Lọc nhân viên:", all_users_hist, key="h_user")
    n_hist = h2.text_input("Tìm ghi chú:", key="h_note")
    
    hist_df = df.copy()
    if u_hist != "Tất cả":
        hist_df = hist_df[hist_df['Tên người dùng'] == u_hist]
    if n_hist:
        hist_df = hist_df[hist_df['Ghi chú'].str.contains(n_hist, case=False, na=False)]
        
    st.dataframe(hist_df.iloc[::-1], use_container_width=True, hide_index=True)
