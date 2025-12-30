import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# --- 1. CẤU HÌNH ---
st.set_page_config(layout="wide", page_title="Quản lý Chấm công Koshi")
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 2. KẾT NỐI ---
try:
    decoded = json.loads(base64.b64decode(st.secrets["base64_service_account"]).decode('utf-8'))
    gc = gspread.service_account_from_dict(decoded)
    sh = gc.open_by_key(st.secrets["sheet_id"]).worksheet(st.secrets["worksheet_name"])
except Exception as e:
    st.error(f"Lỗi kết nối: {e}")
    st.stop()

# --- 3. ĐĂNG NHẬP ---
if 'admin_logged' not in st.session_state: st.session_state.admin_logged = False

if not st.session_state.admin_logged:
    st.title("🔐 Đăng nhập Admin")
    with st.form("login_form"):
        u = st.text_input("Email")
        p = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập"):
            if "@koshigroup.vn" in u and p == "Koshi@123":
                st.session_state.admin_logged = True
                st.session_state.mail = u
                st.rerun()
            else: st.error("Sai tài khoản!")
    st.stop()

# --- 4. TẢI DỮ LIỆU ---
data = sh.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()

# --- 5. THANH BỘ LỌC CỐ ĐỊNH (SIDEBAR) ---
# Đưa toàn bộ bộ lọc vào đây để không bị lỗi hiển thị ở màn hình chính
st.sidebar.header("🔍 BỘ LỌC HỆ THỐNG")

# Bộ lọc 1: Ngày
f_date = st.sidebar.date_input("1. Chọn ngày xem:", value=datetime.now(vn_tz))
str_date = f_date.strftime('%Y-%m-%d')

# Bộ lọc 2: Nhân viên (Lấy từ toàn bộ danh sách)
if not df.empty:
    list_names = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
else:
    list_names = ["Tất cả"]
f_user = st.sidebar.selectbox("2. Chọn nhân viên:", list_names)

st.sidebar.divider()
if st.sidebar.button("🔄 Tải lại dữ liệu"):
    st.rerun()
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.admin_logged = False
    st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.title("🔑 Phê duyệt Chấm công")

# Hiển thị trạng thái lọc hiện tại
st.info(f"📅 Ngày: **{str_date}** | 👤 Nhân viên: **{f_user}**")

# --- PHẦN PHÊ DUYỆT ---
if not df.empty:
    pending = df[df['Tình trạng'] == "Chờ duyệt"].copy()
    
    if not pending.empty:
        # Lọc theo Ngày + Tên
        pending['date_only'] = pending['Thời gian Check in'].str[:10]
        mask = (pending['date_only'] == str_date)
        if f_user != "Tất cả":
            mask = mask & (pending['Tên người dùng'] == f_user)
            
        res = pending[mask]
        
        if res.empty:
            st.warning("Không có yêu cầu nào khớp với bộ lọc ở bên trái.")
        else:
            for idx, r in res.iterrows():
                real_row = idx + 2
                with st.container(border=True):
                    st.markdown(f"### 👤 {r['Tên người dùng']}")
                    st.write(f"🕒 {r['Thời gian Check in']} | 📝 {r['Ghi chú']}")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✅ DUYỆT", key=f"ok_{real_row}", use_container_width=True):
                        now = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
                        sh.update_cell(real_row, 6, "Đã duyệt ✅")
                        sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                        st.rerun()
                    if c2.button("❌ TỪ CHỐI", key=f"no_{real_row}", use_container_width=True, type="primary"):
                        now = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
                        sh.update_cell(real_row, 6, "Từ chối ❌")
                        sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                        st.rerun()
    else:
        st.success("Hết yêu cầu chờ duyệt!")

st.divider()
st.subheader("📜 Lịch sử gần đây")
st.dataframe(df.iloc[::-1].head(50), use_container_width=True, hide_index=True)
