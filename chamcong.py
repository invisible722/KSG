import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64

# --- CẤU HÌNH GOOGLE SHEETS ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
except Exception:
    st.error("Lỗi: Không tìm thấy thông tin cấu hình trong Streamlit Secrets.")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú'] 

# --- THIẾT LẬP KẾT NỐI ---
try:
    decoded_json_bytes = base64.b64decode(BASE64_CREDS)
    CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()

# --- FUNCTIONS ---

@st.cache_data(ttl=2)
def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(all_values[1:], columns=COLUMNS)
        df['Thời gian Check in'] = pd.to_datetime(df['Thời gian Check in'], errors='coerce')
        df['Thời gian Check out'] = pd.to_datetime(df['Thời gian Check out'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame(columns=COLUMNS)

def find_next_available_row():
    # Lấy cột B, lọc bỏ các ô thực sự rỗng
    col_b_values = list(filter(None, SHEET.col_values(2))) 
    return len(col_b_values) + 1

def append_check_in_to_sheet(user_email, now):
    # Bảo vệ cấp hàm: Tuyệt đối không ghi nếu email trống
    if not user_email or not str(user_email).strip():
        return False

    load_data.clear()
    next_row = find_next_available_row() + 1
    
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    new_row = [new_stt, user_email.strip(), now.strftime('%Y-%m-%d %H:%M:%S'), '', '']
    SHEET.update(f"A{next_row}:E{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now, note):
    if not user_email or not str(user_email).strip():
        return False

    load_data.clear()
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    target_row = -1
    clean_email = user_email.strip()
    for i in range(len(emails) - 1, 0, -1):
        if emails[i] == clean_email:
            if i >= len(checkouts) or not checkouts[i]:
                target_row = i + 1
                break
    
    if target_row != -1:
        SHEET.update_cell(target_row, 4, now.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, note)
        return True
    return False

# --- STREAMLIT UI ---

st.set_page_config(layout="wide", page_title="Hệ thống Chấm công")
st.title("⏰ Hệ thống Chấm công Google Sheets")

# Input Email
user_email = st.text_input("📧 Email người dùng", value=st.session_state.get('last_user_email', ''), placeholder="Nhập email...")
st.session_state.last_user_email = user_email

# --- CẢNH BÁO VÀ CHẶN THỰC THI (QUAN TRỌNG) ---
# Nếu người dùng nhấn nút mà email trống, st.stop() sẽ ngăn chặn mọi việc ghi dữ liệu bên dưới.
email_is_empty = not user_email or not user_email.strip()

st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("🟢 CHECK IN", use_container_width=True):
        if email_is_empty:
            st.error("❗ LỖI: Bạn chưa nhập Email. Hệ thống đã chặn việc ghi dòng trống.")
            st.stop() # Dừng ngay lập tức, không chạy hàm append bên dưới
        
        if append_check_in_to_sheet(user_email, datetime.now()):
            st.toast("Check In thành công!")
            st.rerun()

with col2:
    if st.button("🔴 CHECK OUT", use_container_width=True):
        if email_is_empty:
            st.error("❗ LỖI: Bạn chưa nhập Email.")
            st.stop()
            
        note_val = st.session_state.get('work_note_input_widget', '')
        if update_check_out_in_sheet(user_email, datetime.now(), note_val):
            st.toast("Check Out thành công!")
            st.session_state['work_note_input_widget'] = ""
            st.rerun()
        else:
            st.error("Không tìm thấy dòng Check In chưa đóng của bạn!")

with col3:
    st.text_input("📝 Ghi chú", key='work_note_input_widget')

st.markdown("---")
df_display = load_data()
if not df_display.empty:
    st.dataframe(df_display.iloc[::-1], use_container_width=True, hide_index=True)
