import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# 1. Cấu hình
st.set_page_config(layout="wide", page_title="Hệ thống Admin")
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# 2. Kết nối Google Sheet
try:
    creds = json.loads(base64.b64decode(st.secrets["base64_service_account"]).decode('utf-8'))
    client = gspread.service_account_from_dict(creds)
    sheet = client.open_by_key(st.secrets["sheet_id"]).worksheet(st.secrets["worksheet_name"])
except Exception as e:
    st.error(f"Lỗi kết nối: {e}")
    st.stop()

# 3. Hàm xử lý cập nhật
def run_update(row_idx, status, admin_mail):
    now = datetime.now(vn_tz).strftime('%H:%M:%S %d-%m-%Y')
    sheet.update_cell(row_idx, 6, status) # Cột Tình trạng
    sheet.update_cell(row_idx, 7, f"{admin_mail} ({now})") # Cột Người duyệt

# 4. Kiểm tra Đăng nhập
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("Login_Form"):
        u = st.text_input("Email Admin")
        p = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Đăng nhập"):
            if "@koshigroup.vn" in u and p == "Koshi@123":
                st.session_state.logged_in = True
                st.session_state.admin_user = u
                st.rerun()
    st.stop()

# 5. GIAO DIỆN CHÍNH (Sau khi đăng nhập)
st.title("🔑 HỆ THỐNG PHÊ DUYỆT")

# Tải dữ liệu tươi
raw_data = sheet.get_all_values()
df = pd.DataFrame(raw_data[1:], columns=raw_data[0]) if len(raw_data) > 1 else pd.DataFrame()

# --- KHỐI BỘ LỌC CƯỠNG BỨC (LUÔN HIỆN TRÊN ĐẦU) ---
with st.container(border=True):
    st.markdown("#### 🔍 Bộ lọc tìm kiếm nhanh")
    col1, col2 = st.columns(2)
    with col1:
        # Lọc Ngày
        pick_date = st.date_input("Bước 1: Chọn ngày", value=datetime.now(vn_tz))
        target_day = pick_date.strftime('%Y-%m-%d')
    with col2:
        # Lọc Tên (Lấy từ toàn bộ nhân viên đã từng chấm công)
        all_staff = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist()) if not df.empty else ["Tất cả"]
        pick_user = st.selectbox("Bước 2: Chọn nhân viên", all_staff)

st.divider()

# --- CHIA TAB HIỂN THỊ ---
t_pending, t_history = st.tabs(["⏳ CHỜ DUYỆT", "📜 LỊCH SỬ"])

with t_pending:
    if not df.empty:
        # Lọc danh sách: Phải là 'Chờ duyệt' + Khớp ngày + Khớp tên
        pending_list = df[df['Tình trạng'] == "Chờ duyệt"].copy()
        
        if not pending_list.empty:
            # Xử lý cột ngày để lọc chính xác
            pending_list['day_only'] = pending_list['Thời gian Check in'].str[:10]
            
            # Áp dụng bộ lọc từ trên
            mask = (pending_list['day_only'] == target_day)
            if pick_user != "Tất cả":
                mask = mask & (pending_list['Tên người dùng'] == pick_user)
            
            final_view = pending_list[mask]
            
            if final_view.empty:
                st.info(f"Không có yêu cầu nào của **{pick_user}** trong ngày **{target_day}**")
            else:
                st.write(f"Tìm thấy **{len(final_view)}** yêu cầu cần duyệt:")
                for idx, r in final_view.iterrows():
                    real_row_num = idx + 2
                    with st.container(border=True):
                        st.subheader(f"👤 {r['Tên người dùng']}")
                        st.write(f"🕒 {r['Thời gian Check in']} → {r['Thời gian Check out']}")
                        st.write(f"📍 Ghi chú: {r['Ghi chú']}")
                        
                        btn_c1, btn_c2 = st.columns(2)
                        if btn_c1.button("✅ DUYỆT", key=f"ok_{real_row_num}", use_container_width=True):
                            run_update(real_row_num, "Đã duyệt ✅", st.session_state.admin_user)
                            st.rerun()
                        if btn_c2.button("❌ TỪ CHỐI", key=f"no_{real_row_num}", use_container_width=True, type="primary"):
                            run_update(real_row_num, "Từ chối ❌", st.session_state.admin_user)
                            st.rerun()
        else:
            st.success("Không có ai đang chờ duyệt.")
    else:
        st.error("Dữ liệu trống.")

with t_history:
    st.dataframe(df.iloc[::-1], use_container_width=True)
