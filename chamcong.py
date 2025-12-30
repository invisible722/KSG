import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz  # Thư viện xử lý múi giờ

# --- CẤU HÌNH GOOGLE SHEETS ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
except Exception:
    st.error("Lỗi: Không tìm thấy cấu hình trong Streamlit Secrets.")
    st.stop()

# Cập nhật đủ 7 cột như yêu cầu của bạn
COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt'] 

# --- KẾT NỐI ---
try:
    decoded_json_bytes = base64.b64decode(BASE64_CREDS)
    CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi kết nối: {e}")
    st.stop()

# --- FUNCTIONS ---

@st.cache_data(ttl=2)
def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(all_values[1:], columns=COLUMNS)
        return df
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

def find_next_available_row():
    col_b = SHEET.col_values(2)
    filled_rows = [row for row in col_b if row.strip()]
    return len(filled_rows) + 1

def append_check_in_to_sheet(user_email, now_vn):
    clean_email = str(user_email).strip()
    if not clean_email: return False

    load_data.clear()
    next_row = find_next_available_row() + 1
    
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    # Ghi đủ 6 cột đầu, cột 7 để trống
    new_row = [new_stt, clean_email, now_vn.strftime('%Y-%m-%d %H:%M:%S'), '', '', 'Chờ duyệt']
    SHEET.update(f"A{next_row}:F{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now_vn, note):
    clean_email = str(user_email).strip()
    load_data.clear()
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    target_row = -1
    for i in range(len(emails) - 1, 0, -1):
        if emails[i].strip() == clean_email:
            if i >= len(checkouts) or not checkouts[i].strip():
                target_row = i + 1
                break
    
    if target_row != -1:
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S')) # Cột D
        SHEET.update_cell(target_row, 5, note) # Cột E
        return True
    return False

# --- STREAMLIT UI ---
st.set_page_config(layout="wide", page_title="Hệ thống Chấm công")
st.title("⏰ Hệ thống Chấm công")

# Thiết lập múi giờ Việt Nam
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# DÙNG FORM ĐỂ KIỂM SOÁT DỮ LIỆU NHẬP
with st.form("my_attendance_form"):
    st.write("### Nhập thông tin của bạn")
    
    email_input = st.text_input("📧 Email / Tên người dùng", 
                                value=st.session_state.get('last_user_email', ''),
                                placeholder="Nhập tên để hệ thống tìm đúng dòng của bạn")
    
    note_input = st.text_input("📝 Ghi chú Địa điểm làm việc (BẮT BUỘC KHI CHECK OUT)", 
                               placeholder="VD: Làm tại văn phòng / Remote")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        btn_in = st.form_submit_button("🟢 CHECK IN", use_container_width=True)
    with c2:
        btn_out = st.form_submit_button("🔴 CHECK OUT", use_container_width=True)

# XỬ LÝ SAU KHI BẤM NÚT
user_email = email_input.strip()
st.session_state.last_user_email = user_email
current_now = datetime.now(vn_tz)

if btn_in:
    if not user_email:
        st.error("❗ Vui lòng nhập Email/Tên trước khi Check In.")
    else:
        if append_check_in_to_sheet(user_email, current_now):
            st.success("Check In thành công!")
            st.rerun()

if btn_out:
    # KIỂM TRA ĐIỀU KIỆN GHI CHÚ NGHIÊM NGẶT
    if not user_email:
        st.error("❗ Vui lòng nhập Email/Tên.")
    elif not note_input.strip():
        # NẾU TRỐNG THÌ HIỆN THÔNG BÁO VÀ DỪNG LUÔN, KHÔNG CHẠY LỆNH GHI SHEET
        st.warning("⚠️ BẠN CHƯA NHẬP GHI CHÚ! Vui lòng nhập địa điểm làm việc để Check Out.")
    else:
        # CHỈ KHI CÓ GHI CHÚ MỚI GỌI HÀM CẬP NHẬT SHEET
        if update_check_out_in_sheet(user_email, current_now, note_input.strip()):
            st.success("Check Out thành công!")
            st.rerun()
        else:
            st.error("❌ Không tìm thấy lượt Check In nào đang mở cho tên này.")

# HIỂN THỊ DỮ LIỆU
st.markdown("---")
df_display = load_data()
if not df_display.empty:
    valid_df = df_display[df_display['Tên người dùng'].str.strip() != ""]
    st.dataframe(valid_df.iloc[::-1], use_container_width=True, hide_index=True)
