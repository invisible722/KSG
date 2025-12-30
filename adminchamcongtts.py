import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# --- 1. CẤU HÌNH ---
st.set_page_config(layout="wide", page_title="Quản lý Koshi")
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
    with st.form("login"):
        u = st.text_input("Email")
        p = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Vào hệ thống"):
            if "@koshigroup.vn" in u and p == "Koshi@123":
                st.session_state.admin_logged = True
                st.session_state.mail = u
                st.rerun()
            else: st.error("Sai tài khoản")
    st.stop()

# --- 4. TẢI DỮ LIỆU ---
data = sh.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()

# --- 5. BỘ LỌC TẠI SIDEBAR ---
st.sidebar.header("🔍 BỘ LỌC")
f_date = st.sidebar.date_input("Chọn ngày:", value=datetime.now(vn_tz))
str_date = f_date.strftime('%Y-%m-%d')

if not df.empty:
    list_names = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
else:
    list_names = ["Tất cả"]
f_user = st.sidebar.selectbox("Chọn nhân viên:", list_names)

# --- 6. GIAO DIỆN CHÍNH ---
st.title("🔑 Phê duyệt Chấm công")

tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử"])

# --- TAB 1: PHÊ DUYỆT ---
with tab1:
    st.info(f"📅 Ngày: **{str_date}** | 👤 Nhân viên: **{f_user}**")
    
    if not df.empty:
        pending = df[df['Tình trạng'] == "Chờ duyệt"].copy()
        if not pending.empty:
            pending['d'] = pending['Thời gian Check in'].str[:10]
            mask = (pending['d'] == str_date)
            if f_user != "Tất cả": mask = mask & (pending['Tên người dùng'] == f_user)
            
            res = pending[mask]
            
            if res.empty:
                st.warning("Không có yêu cầu nào khớp bộ lọc.")
            else:
                for idx, r in res.iterrows():
                    real_row = idx + 2
                    with st.container(border=True):
                        # Hiển thị Tên nhân viên
                        st.markdown(f"### 👤 {r['Tên người dùng']}")
                        
                        # HIỂN THỊ GIỜ VÀO / GIỜ RA CHI TIẾT
                        col_time1, col_time2 = st.columns(2)
                        with col_time1:
                            st.success(f"🛫 **Giờ vào:** {r['Thời gian Check in']}")
                        with col_time2:
                            st.error(f"🛬 **Giờ ra:** {r['Thời gian Check out']}")
                        
                        # Ghi chú
                        st.markdown(f"📝 **Ghi chú:** {r['Ghi chú']}")
                        
                        # Nút bấm
                        c1, c2 = st.columns(2)
                        if c1.button("✅ DUYỆT", key=f"ok_{real_row}", use_container_width=True):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Đã duyệt ✅")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
                        if c2.button("❌ TỪ CHỐI", key=f"no_{real_row}", use_container_width=True, type="primary"):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Từ chối ❌")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
        else:
            st.success("Hết yêu cầu chờ duyệt!")

# --- TAB 2: LỊCH SỬ ---
with tab2:
    st.subheader("📜 Dữ liệu hệ thống")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
