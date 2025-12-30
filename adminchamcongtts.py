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

# --- 4. TẢI DỮ LIỆU GỐC ---
data = sh.get_all_values()
df_full = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()

# --- 5. SIDEBAR: BỘ LỌC VÀ NÚT ÁP DỤNG ---
st.sidebar.header("🔍 BỘ LỌC CHUNG")

# Lưu trạng thái lọc vào session_state để không bị mất khi load lại
if 'applied_date' not in st.session_state:
    st.session_state.applied_date = datetime.now(vn_tz).strftime('%Y-%m-%d')
if 'applied_user' not in st.session_state:
    st.session_state.applied_user = "Tất cả"

# Widget nhập liệu (Chỉ mang tính chất chọn, chưa tác động ngay)
pick_date = st.sidebar.date_input("1. Lọc theo ngày:", value=datetime.strptime(st.session_state.applied_date, '%Y-%m-%d'))
user_list = ["Tất cả"] + sorted(df_full['Tên người dùng'].unique().tolist()) if not df_full.empty else ["Tất cả"]
pick_user = st.sidebar.selectbox("2. Lọc theo nhân viên:", user_list, index=user_list.index(st.session_state.applied_user) if st.session_state.applied_user in user_list else 0)

# NÚT BẮT BUỘC NHẤN ĐỂ LỌC
if st.sidebar.button("🚀 ÁP DỤNG LỌC", type="primary", use_container_width=True):
    st.session_state.applied_date = pick_date.strftime('%Y-%m-%d')
    st.session_state.applied_user = pick_user
    st.rerun() # Làm mới trang để áp dụng giá trị mới cho toàn bộ Tab

st.sidebar.divider()
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.admin_logged = False
    st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.title("🔑 Phê duyệt Chấm công")

# Lấy giá trị đã được CHỐT sau khi nhấn nút
curr_date = st.session_state.applied_date
curr_user = st.session_state.applied_user

tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử"])

# --- TAB 1: CHỜ PHÊ DUYỆT ---
with tab1:
    st.info(f"📅 Ngày: **{curr_date}** | 👤 Nhân viên: **{curr_user}**")
    if not df_full.empty:
        pending = df_full[df_full['Tình trạng'] == "Chờ duyệt"].copy()
        if not pending.empty:
            pending['d'] = pending['Thời gian Check in'].str[:10]
            mask = (pending['d'] == curr_date)
            if curr_user != "Tất cả": mask = mask & (pending['Tên người dùng'] == curr_user)
            res = pending[mask]
            
            if res.empty:
                st.warning("Không có yêu cầu nào.")
            else:
                for idx, r in res.iterrows():
                    real_row = idx + 2
                    with st.container(border=True):
                        st.markdown(f"### 👤 {r['Tên người dùng']}")
                        c1, c2 = st.columns(2)
                        with c1: st.success(f"🛫 **Vào:** {r['Thời gian Check in']}")
                        with c2: st.error(f"🛬 **Ra:** {r['Thời gian Check out']}")
                        
                        btn_a, btn_b = st.columns(2)
                        if btn_a.button("✅ DUYỆT", key=f"ok_{real_row}"):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Đã duyệt ✅")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
                        if btn_b.button("❌ TỪ CHỐI", key=f"no_{real_row}", type="primary"):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Từ chối ❌")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
        else: st.success("Hết yêu cầu!")

# --- TAB 2: LỊCH SỬ (ĐÃ FIX LỖI ĐỒNG BỘ) ---
with tab2:
    st.subheader(f"📜 Dữ liệu: {curr_user} ({curr_date})")
    if not df_full.empty:
        # Clone dữ liệu để xử lý
        history = df_full.copy()
        # Chuyển cột thời gian về dạng ngày để so sánh
        history['day_tmp'] = history['Thời gian Check in'].str[:10]
        
        # ÁP DỤNG LỌC TRIỆT ĐỂ
        mask_hist = (history['day_tmp'] == curr_date)
        if curr_user != "Tất cả":
            mask_hist = mask_hist & (history['Tên người dùng'] == curr_user)
        
        final_hist = history[mask_hist]
        
        if final_hist.empty:
            st.warning("Không tìm thấy dữ liệu lịch sử cho lựa chọn này.")
        else:
            # Hiện bảng, loại bỏ cột tạm và đảo ngược thứ tự
            st.dataframe(
                final_hist.drop(columns=['day_tmp']).iloc[::-1], 
                use_container_width=True, 
                hide_index=True
            )
    else:
        st.write("Dữ liệu trống.")
