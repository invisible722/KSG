import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# 1. Cấu hình trang & Múi giờ
st.set_page_config(layout="wide", page_title="Admin Koshi")
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# 2. Kết nối Sheet (Dùng secrets)
try:
    decoded_creds = json.loads(base64.b64decode(st.secrets["base64_service_account"]).decode('utf-8'))
    gc = gspread.service_account_from_dict(decoded_creds)
    sh = gc.open_by_key(st.secrets["sheet_id"]).worksheet(st.secrets["worksheet_name"])
except Exception as e:
    st.error(f"Lỗi kết nối: {e}")
    st.stop()

# 3. Hàm xử lý
def update_sheet(row, status, admin):
    now = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
    sh.update_cell(row, 6, status) # Cột F
    sh.update_cell(row, 7, f"{admin} ({now})") # Cột G

# 4. Đăng nhập
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    with st.form("Login"):
        u = st.text_input("Email")
        p = st.text_input("Pass", type="password")
        if st.form_submit_button("Vào"):
            if "@koshigroup.vn" in u and p == "Koshi@123":
                st.session_state.auth = True
                st.session_state.email = u
                st.rerun()
    st.stop()

# 5. Giao diện chính
st.title("🔑 QUẢN LÝ CHẤM CÔNG")

# Tải dữ liệu tươi (không cache)
data = sh.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()

# TẠO BỘ LỌC NGAY TẠI ĐÂY - KHÔNG ĐẶT TRONG TAB, KHÔNG ĐẶT TRONG IF
st.markdown("### 🔍 BỘ LỌC TỔNG")
c1, c2 = st.columns(2)
with c1:
    sel_date = st.date_input("Chọn ngày", value=datetime.now(vn_tz))
    str_date = sel_date.strftime('%Y-%m-%d')
with c2:
    names = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist()) if not df.empty else ["Tất cả"]
    sel_user = st.selectbox("Chọn nhân viên", names)

st.divider()

# Chia Tab
t1, t2 = st.tabs(["⏳ Chờ Duyệt", "📜 Lịch sử"])

with t1:
    if not df.empty:
        # Lọc Chờ duyệt + Ngày + Tên
        pending = df[df['Tình trạng'] == "Chờ duyệt"].copy()
        if not pending.empty:
            pending['d'] = pending['Thời gian Check in'].str[:10]
            mask = (pending['d'] == str_date)
            if sel_user != "Tất cả": mask = mask & (pending['Tên người dùng'] == sel_user)
            
            res = pending[mask]
            if res.empty:
                st.info("Không có yêu cầu nào khớp bộ lọc.")
            else:
                for idx, r in res.iterrows():
                    with st.container(border=True):
                        st.write(f"👤 **{r['Tên người dùng']}** | 🕒 {r['Thời gian Check in']}")
                        col_a, col_b = st.columns(2)
                        if col_a.button("✅ DUYỆT", key=f"ok_{idx}"):
                            update_sheet(idx+2, "Đã duyệt ✅", st.session_state.email)
                            st.rerun()
                        if col_b.button("❌ TỪ CHỐI", key=f"no_{idx}", type="primary"):
                            update_sheet(idx+2, "Từ chối ❌", st.session_state.email)
                            st.rerun()
        else:
            st.success("Hết yêu cầu chờ duyệt.")

with t2:
    st.dataframe(df.iloc[::-1], use_container_width=True)
