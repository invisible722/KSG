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

# --- 3. FUNCTIONS ---
def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt'])
        return pd.DataFrame(all_values[1:], columns=all_values[0])
    except:
        return pd.DataFrame()

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
        if st.form_submit_button("Đăng nhập"):
            if "@koshigroup.vn" in user and pw == "Koshi@123":
                st.session_state.admin_logged_in = True
                st.session_state.admin_email = user
                st.rerun()
            else: st.error("Sai tài khoản!")
    st.stop()

# --- 5. GIAO DIỆN CHÍNH ---

# --- TẢI DỮ LIỆU ---
df_full = load_data()

# --- BỘ LỌC CỐ ĐỊNH TẠI SIDEBAR ---
st.sidebar.title("🔍 BỘ LỌC HỆ THỐNG")
st.sidebar.write(f"👤 Admin: **{st.session_state.admin_email}**")

# Widget lọc ngày
f_date = st.sidebar.date_input("1. Chọn ngày xem:", value=datetime.now(vn_tz))
str_date = f_date.strftime('%Y-%m-%d')

# Widget lọc tên
if not df_full.empty:
    list_names = ["Tất cả"] + sorted(df_full['Tên người dùng'].unique().tolist())
else:
    list_names = ["Tất cả"]
f_user = st.sidebar.selectbox("2. Chọn nhân viên:", list_names)

if st.sidebar.button("Đăng xuất"):
    st.session_state.admin_logged_in = False
    st.rerun()

# --- HIỂN THỊ NỘI DUNG CHÍNH ---
st.title("🔑 Phê duyệt & Quản lý Chấm công")
tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Toàn bộ lịch sử"])

# --- TAB 1: PHÊ DUYỆT ---
with tab1:
    st.info(f"📅 Đang xem ngày: **{str_date}** | 👤 Nhân viên: **{f_user}**")
    
    if not df_full.empty:
        # Lấy danh sách chờ duyệt
        pending = df_full[df_full['Tình trạng'] == "Chờ duyệt"].copy()
        
        if not pending.empty:
            # Chuẩn hóa cột ngày để lọc
            pending['date_only'] = pending['Thời gian Check in'].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})')
            
            # Thực hiện lọc theo Sidebar
            mask = (pending['date_only'] == str_date)
            if f_user != "Tất cả":
                mask = mask & (pending['Tên người dùng'] == f_user)
            
            final_df = pending[mask]
            
            if final_df.empty:
                st.write("👉 *Không tìm thấy yêu cầu chờ duyệt nào khớp với bộ lọc ở Sidebar.*")
            else:
                for idx, row in final_df.iterrows():
                    real_idx = idx + 2
                    with st.container(border=True):
                        st.markdown(f"### 👤 {row['Tên người dùng']}")
                        st.write(f"🕒 **Vào:** {row['Thời gian Check in']} | **Ra:** {row['Thời gian Check out']}")
                        st.write(f"📝 **Ghi chú:** {row['Ghi chú']}")
                        
                        btn_c1, btn_c2 = st.columns(2)
                        with btn_c1:
                            if st.button("✅ DUYỆT", key=f"app_{real_idx}", use_container_width=True):
                                if process_action(real_idx, st.session_state.admin_email, "Đã duyệt ✅"):
                                    st.toast("Đã duyệt thành công!")
                                    st.rerun()
                        with btn_c2:
                            if st.button("❌ TỪ CHỐI", key=f"rej_{real_idx}", use_container_width=True, type="primary"):
                                if process_action(real_idx, st.session_state.admin_email, "Từ chối ❌"):
                                    st.toast("Đã từ chối!")
                                    st.rerun()
        else:
            st.success("Tất cả yêu cầu đã được xử lý xong!")
    else:
        st.error("Không có dữ liệu.")

# --- TAB 2: LỊCH SỬ ---
with tab2:
    st.subheader("📜 Toàn bộ nhật ký")
    if not df_full.empty:
        st.dataframe(df_full.iloc[::-1], use_container_width=True, hide_index=True)
