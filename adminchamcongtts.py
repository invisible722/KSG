import streamlit as st
import pandas as pd
import gspread
import json
import base64
import pytz
from datetime import datetime

# --- 1. CẤU HÌNH ---
st.set_page_config(layout="wide", page_title="Quản lý Chấm công")
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 2. KẾT NỐI (Dùng secrets) ---
try:
    decoded = json.loads(base64.b64decode(st.secrets["base64_service_account"]).decode('utf-8'))
    gc = gspread.service_account_from_dict(decoded)
    sh = gc.open_by_key(st.secrets["sheet_id"]).worksheet(st.secrets["worksheet_name"])
except Exception as e:
    st.error(f"Lỗi kết nối Sheet: {e}")
    st.stop()

# --- 3. ĐĂNG NHẬP ---
if 'admin_ok' not in st.session_state: st.session_state.admin_ok = False

if not st.session_state.admin_ok:
    with st.container(border=True):
        st.title("🔐 Đăng nhập hệ thống")
        u = st.text_input("Email")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("Vào hệ thống"):
            if "@koshigroup.vn" in u and p == "Koshi@123":
                st.session_state.admin_ok = True
                st.session_state.mail = u
                st.rerun()
            else: st.error("Sai tài khoản!")
    st.stop()

# --- 4. GIAO DIỆN CHÍNH (KHÔNG DÙNG TAB ĐỂ TRÁNH LỖI) ---
st.title("🔑 Phê duyệt & Quản lý Chấm công")

# Tải dữ liệu tươi
data = sh.get_all_values()
df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()

# --- KHỐI BỘ LỌC TỔNG (LUÔN HIỂN THỊ) ---
with st.container(border=True):
    st.markdown("### 🔍 BỘ LỌC TÌM KIẾM")
    c1, c2, c3 = st.columns([2, 2, 1])
    
    with c1:
        f_date = st.date_input("1. Lọc theo ngày:", value=datetime.now(vn_tz))
        str_date = f_date.strftime('%Y-%m-%d')
    
    with c2:
        # Lấy danh sách tên từ cột 'Tên người dùng'
        if not df.empty and 'Tên người dùng' in df.columns:
            list_names = ["Tất cả"] + sorted(df['Tên người dùng'].unique().tolist())
        else:
            list_names = ["Tất cả"]
        f_user = st.selectbox("2. Lọc theo nhân viên:", list_names)
    
    with c3:
        st.write("") # Căn lề
        if st.button("🔄 Làm mới", use_container_width=True):
            st.rerun()

st.divider()

# --- PHẦN 1: XỬ LÝ PHÊ DUYỆT ---
st.header("⏳ Yêu cầu chờ phê duyệt")

if not df.empty:
    # Lọc danh sách chờ duyệt
    pending = df[df['Tình trạng'] == "Chờ duyệt"].copy()
    
    if not pending.empty:
        # Chuẩn hóa ngày
        pending['date_check'] = pending['Thời gian Check in'].str[:10]
        
        # Áp dụng bộ lọc
        mask = (pending['date_check'] == str_date)
        if f_user != "Tất cả":
            mask = mask & (pending['Tên người dùng'] == f_user)
        
        res = pending[mask]
        
        if res.empty:
            st.info(f"Không có yêu cầu nào của **{f_user}** vào ngày **{str_date}**")
        else:
            for idx, r in res.iterrows():
                real_row = idx + 2
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.subheader(f"👤 {r['Tên người dùng']}")
                        st.write(f"🕒 **Vào:** {r['Thời gian Check in']} | **Ra:** {r['Thời gian Check out']}")
                        st.write(f"📍 **Ghi chú:** {r['Ghi chú']}")
                    
                    with col_btn:
                        st.write("")
                        if st.button("✅ DUYỆT", key=f"a_{real_row}", use_container_width=True):
                            now = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
                            sh.update_cell(real_row, 6, "Đã duyệt ✅")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.toast("Đã duyệt!")
                            st.rerun()
                            
                        if st.button("❌ TỪ CHỐI", key=f"r_{real_row}", use_container_width=True, type="primary"):
                            now = datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
                            sh.update_cell(real_row, 6, "Từ chối ❌")
                            sh.update_cell(real_row, 7, f"{st.session_state.mail} ({now})")
                            st.toast("Đã từ chối!")
                            st.rerun()
    else:
        st.success("Không còn yêu cầu nào cần duyệt.")

st.divider()

# --- PHẦN 2: LỊCH SỬ ---
st.header("📜 Toàn bộ lịch sử")
if not df.empty:
    # Áp dụng bộ lọc nhân viên cho bảng lịch sử bên dưới luôn
    hist_df = df.copy()
    if f_user != "Tất cả":
        hist_df = hist_df[hist_df['Tên người dùng'] == f_user]
    
    st.dataframe(hist_df.iloc[::-1], use_container_width=True, hide_index=True)

# --- NÚT ĐĂNG XUẤT ---
st.sidebar.button("Đăng xuất", on_click=lambda: st.session_state.update({"admin_ok": False}))
