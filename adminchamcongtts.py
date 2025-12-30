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

# --- 2. KẾT NỐI GOOGLE SHEETS ---
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
    st.title("🔐 Đăng nhập hệ thống")
    with st.form("login_form"):
        u = st.text_input("Email Admin")
        p = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Vào hệ thống"):
            if "@koshigroup.vn" in u and p == "Koshi@123":
                st.session_state.admin_logged = True
                st.session_state.mail = u
                st.rerun()
            else: st.error("Sai tài khoản!")
    st.stop()

# --- 4. TẢI DỮ LIỆU ---
data = sh.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()

# --- 5. BỘ LỌC TẠI SIDEBAR (LUÔN XUẤT HIỆN) ---
st.sidebar.header("🔍 BỘ LỌC CHUNG")

# Bộ lọc Ngày
f_date = st.sidebar.date_input("1. Lọc theo ngày:", value=datetime.now(vn_tz))
str_date = f_date.strftime('%Y-%m-%d')

# Bộ lọc Tên
if not df.empty:
    list_names = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
else:
    list_names = ["Tất cả"]
f_user = st.sidebar.selectbox("2. Lọc theo nhân viên:", list_names)

st.sidebar.divider()
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.admin_logged = False
    st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.title("🔑 Phê duyệt & Quản lý Chấm công")

# Hiển thị trạng thái lọc để Admin dễ theo dõi
st.info(f"📅 Ngày đang chọn: **{str_date}** | 👤 Nhân viên: **{f_user}**")

# Tách thành 2 Tab như cũ
tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử & Bộ lọc"])

# --- TAB 1: PHÊ DUYỆT ---
with tab1:
    if not df.empty:
        pending = df[df['Tình trạng'] == "Chờ duyệt"].copy()
        if not pending.empty:
            # Lọc theo Sidebar
            pending['date_only'] = pending['Thời gian Check in'].str[:10]
            mask = (pending['date_only'] == str_date)
            if f_user != "Tất cả":
                mask = mask & (pending['Tên người dùng'] == f_user)
            
            res = pending[mask]
            
            if res.empty:
                st.warning("Không có yêu cầu chờ duyệt nào khớp với bộ lọc bên trái.")
            else:
                for idx, r in res.iterrows():
                    real_row = idx + 2
                    with st.container(border=True):
                        st.markdown(f"### 👤 {r['Tên người dùng']}")
                        st.write(f"🕒 {r['Thời gian Check in']} | 📝 {r['Ghi chú']}")
                        
                        c1, c2 = st.columns(2)
                        if c1.button("✅ DUYỆT", key=f"ok_{real_row}"):
                            now = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
                            sh.update_cell(real_row, 6, "Đã duyệt ✅")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
                        if c2.button("❌ TỪ CHỐI", key=f"no_{real_row}", type="primary"):
                            now = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
                            sh.update_cell(real_row, 6, "Từ chối ❌")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
        else:
            st.success("Tất cả yêu cầu đã được phê duyệt!")

# --- TAB 2: LỊCH SỬ ---
with tab2:
    st.subheader("📜 Dữ liệu hệ thống")
    hist_df = df.copy()
    
    # Áp dụng bộ lọc Sidebar vào bảng lịch sử
    if f_user != "Tất cả":
        hist_df = hist_df[hist_df['Tên người dùng'] == f_user]
    
    # Lọc lịch sử theo ngày (không bắt buộc nhưng giúp bảng gọn hơn)
    hist_df['d'] = hist_df['Thời gian Check in'].str[:10]
    hist_df = hist_df[hist_df['d'] == str_date]
    
    st.dataframe(hist_df.iloc[::-1], use_container_width=True, hide_index=True)
