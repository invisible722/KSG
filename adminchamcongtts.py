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

# --- 5. SIDEBAR: BỘ LỌC VÀ NÚT ÁP DỤNG (ĐẢM BẢO HIỂN THỊ) ---
st.sidebar.title("🔍 BỘ LỌC CHUNG")

# Khởi tạo giá trị lọc mặc định nếu chưa có
if 'curr_date' not in st.session_state:
    st.session_state.curr_date = datetime.now(vn_tz).strftime('%Y-%m-%d')
if 'curr_user' not in st.session_state:
    st.session_state.curr_user = "Tất cả"

# Các ô nhập liệu ở Sidebar
new_date = st.sidebar.date_input("1. Lọc theo ngày:", value=datetime.strptime(st.session_state.curr_date, '%Y-%m-%d'))
user_list = ["Tất cả"] + sorted(df_full['Tên người dùng'].unique().tolist()) if not df_full.empty else ["Tất cả"]
new_user = st.sidebar.selectbox("2. Lọc theo nhân viên:", user_list, index=user_list.index(st.session_state.curr_user) if st.session_state.curr_user in user_list else 0)

# NÚT ÁP DỤNG LỌC (MÀU ĐỎ NỔI BẬT)
if st.sidebar.button("🚀 ÁP DỤNG LỌC", type="primary", use_container_width=True):
    st.session_state.curr_date = new_date.strftime('%Y-%m-%d')
    st.session_state.curr_user = new_user
    st.rerun()

st.sidebar.divider()
if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    st.session_state.admin_logged = False
    st.rerun()

# --- 6. GIAO DIỆN CHÍNH ---
st.title("🔑 Phê duyệt & Quản lý Chấm công")

# Lấy giá trị đã chốt từ session_state
applied_date = st.session_state.curr_date
applied_user = st.session_state.curr_user

# Thanh trạng thái hiển thị rõ ràng
st.info(f"📍 Đang hiển thị dữ liệu của: **{applied_user}** vào ngày **{applied_date}**")

tab1, tab2 = st.tabs(["⏳ Chờ phê duyệt", "📜 Lịch sử"])

# --- TAB 1: PHÊ DUYỆT ---
with tab1:
    if not df_full.empty:
        # Lọc danh sách Chờ duyệt
        pending = df_full[df_full['Tình trạng'] == "Chờ duyệt"].copy()
        if not pending.empty:
            pending['date_only'] = pending['Thời gian Check in'].str[:10]
            # Lọc theo Ngày & Người dùng đã ÁP DỤNG
            mask = (pending['date_only'] == applied_date)
            if applied_user != "Tất cả":
                mask = mask & (pending['Tên người dùng'] == applied_user)
            
            res = pending[mask]
            
            if res.empty:
                st.warning(f"Không có yêu cầu chờ duyệt nào cho {applied_user} vào {applied_date}")
            else:
                st.write(f"Tìm thấy **{len(res)}** yêu cầu:")
                for idx, r in res.iterrows():
                    real_row = idx + 2
                    with st.container(border=True):
                        st.markdown(f"### 👤 {r['Tên người dùng']}")
                        c1, c2 = st.columns(2)
                        with c1: st.success(f"🛫 **Vào:** {r['Thời gian Check in']}")
                        with c2: st.error(f"🛬 **Ra:** {r['Thời gian Check out']}")
                        if r['Ghi chú']: st.info(f"📝 **Ghi chú:** {r['Ghi chú']}")
                        
                        btn_ok, btn_no = st.columns(2)
                        if btn_ok.button("✅ DUYỆT", key=f"ok_{real_row}", use_container_width=True):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Đã duyệt ✅")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
                        if btn_no.button("❌ TỪ CHỐI", key=f"no_{real_row}", use_container_width=True, type="primary"):
                            now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
                            sh.update_cell(real_row, 6, "Từ chối ❌")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.rerun()
        else:
            st.success("Tất cả yêu cầu đã được xử lý.")

# --- TAB 2: LỊCH SỬ (ĐÃ FIX LỖI LỌC) ---
with tab2:
    st.subheader("📜 Dữ liệu hệ thống")
    if not df_full.empty:
        # Tạo bản sao và lọc theo đúng tiêu chí Sidebar đã Áp dụng
        hist_df = df_full.copy()
        hist_df['date_tmp'] = hist_df['Thời gian Check in'].str[:10]
        
        # Lọc ngày
        hist_df = hist_df[hist_df['date_tmp'] == applied_date]
        
        # Lọc nhân viên
        if applied_user != "Tất cả":
            hist_df = hist_df[hist_df['Tên người dùng'] == applied_user]
            
        if hist_df.empty:
            st.warning("Không có dữ liệu lịch sử nào khớp với bộ lọc.")
        else:
            # Hiện bảng (Xóa cột tạm và đảo ngược thứ tự)
            st.dataframe(
                hist_df.drop(columns=['date_tmp']).iloc[::-1],
                use_container_width=True,
                hide_index=True
            )
