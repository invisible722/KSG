import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz

# --- CẤU HÌNH GOOGLE SHEETS ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
except Exception:
    st.error("Lỗi: Không tìm thấy cấu hình trong Streamlit Secrets.")
    st.stop()

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
    load_data.clear()
    next_row = find_next_available_row() + 1
    
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    new_row = [new_stt, clean_email, now_vn.strftime('%Y-%m-%d %H:%M:%S'), '', '', 'Chờ duyệt', '']
    SHEET.update(f"A{next_row}:G{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now_vn, note):
    # KHÓA BẢO VỆ CUỐI CÙNG
    if not note or str(note).strip() == "":
        return False
        
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
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, note)
        return True
    return False

# --- UI ---
st.set_page_config(layout="wide", page_title="Chấm công Nhân viên")
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

st.title("⏰ Hệ thống Chấm công")

with st.form("attendance_form"):
    email_input = st.text_input("📧 Email / Tên người dùng", value=st.session_state.get('last_user_email', ''))
    note_input = st.text_input("📝 Ghi chú Địa điểm (Bắt buộc khi Check Out)")
    
    col_in, col_out = st.columns(2)
    btn_in = col_in.form_submit_button("🟢 CHECK IN", use_container_width=True)
    btn_out = col_out.form_submit_button("🔴 CHECK OUT", use_container_width=True)

user_email = email_input.strip()
st.session_state.last_user_email = user_email

if btn_in:
    if not user_email:
        st.error("Vui lòng nhập Email!")
    else:
        if append_check_in_to_sheet(user_email, datetime.now(vn_tz)):
            st.success("Check In thành công!")
            st.rerun()

if btn_out:
    final_note = note_input.strip()
    if not user_email:
        st.error("Vui lòng nhập Email!")
    elif not final_note:
        st.error("❌ LỖI: Bạn phải nhập ghi chú địa điểm mới được phép Check Out!")
        st.stop()
    else:
        if update_check_out_in_sheet(user_email, datetime.now(vn_tz), final_note):
            st.success("Check Out thành công!")
            st.rerun()
        else:
            st.error("Không tìm thấy phiên Check In đang mở.")

st.markdown("---")
df = load_data()
st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
