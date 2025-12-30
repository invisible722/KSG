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

# --- TAB 1: PHÊ DUYỆT (FIX LỖI HIỂN THỊ LỌC KÉP) ---
with tab1:
    st.subheader("🔍 Bộ lọc yêu cầu")
    
    # Lấy danh sách nhân viên ĐANG chờ duyệt để đưa vào selectbox
    pending_all_raw = df[df['Tình trạng'] == "Chờ duyệt"].copy()
    list_employees_pending = ["Tất cả"] + sorted(pending_all_raw['Tên người dùng'].unique().tolist())
    
    # Hiển thị bộ lọc
    col_date, col_user = st.columns(2)
    with col_date:
        filter_date = st.date_input("1. Lọc theo ngày:", value=datetime.now(vn_tz), key="p_date_v2")
    with col_user:
        selected_user_p = st.selectbox("2. Lọc theo tên nhân viên:", list_employees_pending, key="p_user_v2")

    # Logic lọc dữ liệu
    if not pending_all_raw.empty:
        # Chuẩn hóa ngày để so sánh
        target_date_str = filter_date.strftime('%Y-%m-%d')
        pending_all_raw['only_date'] = pending_all_raw['Thời gian Check in'].str[:10]
        
        # Bắt đầu lọc
        mask = (pending_all_raw['only_date'] == target_date_str)
        
        if selected_user_p != "Tất cả":
            mask = mask & (pending_all_raw['Tên người dùng'] == selected_user_p)
            
        final_pending = pending_all_raw[mask]
        
        # HIỂN THỊ KẾT QUẢ
        if final_pending.empty:
            st.info(f"Không tìm thấy yêu cầu 'Chờ duyệt' nào của **{selected_user_p}** trong ngày **{target_date_str}**.")
        else:
            st.warning(f"Tìm thấy {len(final_pending)} yêu cầu:")
            for idx, row in final_pending.iterrows():
                real_row = idx + 2
                with st.container(border=True):
                    st.markdown(f"### 👤 {row['Tên người dùng']}")
                    st.write(f"📍 **Ghi chú:** {row['Ghi chú']}")
                    st.write(f"🕒 **Vào:** {row['Thời gian Check in']} | **Ra:** {row['Thời gian Check out']}")
                    
                    c_app, c_rej = st.columns(2)
                    with c_app:
                        if st.button("✅ DUYỆT", key=f"v_app_{real_row}", use_container_width=True):
                            if process_action(real_row, st.session_state.admin_email, "Đã duyệt ✅"):
                                st.toast("Đã phê duyệt!")
                                st.rerun()
                    with c_rej:
                        if st.button("❌ TỪ CHỐI", key=f"v_rej_{real_row}", use_container_width=True, type="primary"):
                            if process_action(real_row, st.session_state.admin_email, "Từ chối ❌"):
                                st.toast("Đã từ chối!")
                                st.rerun()
    else:
        st.success("Hệ thống sạch! Không có yêu cầu nào đang chờ phê duyệt.")

# --- TAB 2: LỊCH SỬ ---
with tab2:
    st.subheader("📜 Toàn bộ lịch sử")
    # Tái sử dụng danh sách nhân viên từ toàn bộ dữ liệu
    all_users = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
    
    c1, c2 = st.columns(2)
    user_filter = c1.selectbox("Lọc nhân viên:", all_users, key="hist_user")
    note_filter = c2.text_input("Tìm ghi chú:", key="hist_note")
    
    hist_df = df.copy()
    if user_filter != "Tất cả":
        hist_df = hist_df[hist_df['Tên người dùng'] == user_filter]
    if note_filter:
        hist_df = hist_df[hist_df['Ghi chú'].str.contains(note_filter, case=False, na=False)]
        
    st.dataframe(hist_df.iloc[::-1], use_container_width=True, hide_index=True)
