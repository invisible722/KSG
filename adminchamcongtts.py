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
df_full = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()

# --- 5. BỘ LỌC TẠI SIDEBAR VỚI NÚT ÁP DỤNG ---
st.sidebar.header("🔍 BỘ LỌC CHUNG")

# Khởi tạo trạng thái lọc trong session_state nếu chưa có
if 'filter_date' not in st.session_state:
    st.session_state.filter_date = datetime.now(vn_tz).strftime('%Y-%m-%d')
if 'filter_user' not in st.session_state:
    st.session_state.filter_user = "Tất cả"

# Widgets nhập liệu
input_date = st.sidebar.date_input("1. Chọn ngày:", value=datetime.strptime(st.session_state.filter_date, '%Y-%m-%d'))
names = ["Tất cả"] + sorted(df_full['Tên người dùng'].unique().tolist()) if not df_full.empty else ["Tất cả"]
input_user = st.sidebar.selectbox("2. Chọn nhân viên:", names, index=names.index(st.session_state.filter_user) if st.session_state.filter_user in names else 0)

# NÚT ÁP DỤNG LỌC
if st.sidebar.button("🚀 ÁP DỤNG LỌC", use_container_width=True, type="primary"):
    st.session_state.filter_date = input_date.strftime('%Y-%m-%d')
    st.session_state.filter_user = input_user
    st.toast("Đã cập nhật dữ liệu theo bộ lọc!")

st.sidebar.divider()
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.admin_logged = False
    st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.title("🔑 Phê duyệt Chấm công")
tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử"])

# --- LẤY GIÁ TRỊ ĐÃ ĐƯỢC ÁP DỤNG ---
curr_date = st.session_state.filter_date
curr_user = st.session_state.filter_user

# --- TAB 1: PHÊ DUYỆT ---
with tab1:
    st.info(f"📅 Đang xem: **{curr_date}** | 👤 Nhân viên: **{curr_user}**")
    if not df_full.empty:
        pending = df_full[df_full['Tình trạng'] == "Chờ duyệt"].copy()
        if not pending.empty:
            pending['d'] = pending['Thời gian Check in'].str[:10]
            mask = (pending['d'] == curr_date)
            if curr_user != "Tất cả": mask = mask & (pending['Tên người dùng'] == curr_user)
            res = pending[mask]
            
            if res.empty:
                st.warning("Không có yêu cầu chờ duyệt nào khớp bộ lọc.")
            else:
                for idx, r in res.iterrows():
                    real_row = idx + 2
                    with st.container(border=True):
                        st.markdown(f"### 👤 {r['Tên người dùng']}")
                        c_in, c_out = st.columns(2)
                        with c_in: st.success(f"🛫 **Giờ vào:** {r['Thời gian Check in']}")
                        with c_out: st.error(f"🛬 **Giờ ra:** {r['Thời gian Check out']}")
                        if r['Ghi chú']: st.info(f"📝 **Ghi chú:** {r['Ghi chú']}")
                        
                        btn1, btn2 = st.columns(2)
                        if btn1.button("✅ DUYỆT", key=f"ok_{real_row}", use_container_width=True):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Đã duyệt ✅")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
                        if btn2.button("❌ TỪ CHỐI", key=f"no_{real_row}", use_container_width=True, type="primary"):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Từ chối ❌")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
        else: st.success("Hết yêu cầu chờ duyệt!")

# --- TAB 2: LỊCH SỬ (ĐÃ FIX LỌC THEO NÚT ÁP DỤNG) ---
with tab2:
    st.subheader(f"📜 Dữ liệu hệ thống ({curr_date})")
    if not df_full.empty:
        # Lọc dữ liệu dựa trên giá trị của nút Áp dụng
        hist = df_full.copy()
        hist['date_tmp'] = hist['Thời gian Check in'].str[:10]
        
        # Áp dụng lọc ngày
        hist = hist[hist['date_tmp'] == curr_date]
        
        # Áp dụng lọc tên
        if curr_user != "Tất cả":
            hist = hist[hist['Tên người dùng'] == curr_user]
            
        if hist.empty:
            st.warning(f"Không có dữ liệu lịch sử cho ngày {curr_date} với nhân viên {curr_user}")
        else:
            # Sắp xếp mới nhất lên đầu và ẩn cột tạm
            st.dataframe(hist.drop(columns=['date_tmp']).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.write("Dữ liệu trống.")
