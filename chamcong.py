import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz

# Thiết lập múi giờ Việt Nam
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# Lấy thời gian hiện tại theo giờ VN
now_vn = datetime.now(vn_tz)

# Định dạng thời gian để ghi vào sheet
formatted_time = now_vn.strftime('%Y-%m-%d %H:%M:%S')

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
        df['Thời gian Check in'] = pd.to_datetime(df['Thời gian Check in'], errors='coerce')
        df['Thời gian Check out'] = pd.to_datetime(df['Thời gian Check out'], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame(columns=COLUMNS)

def find_next_available_row():
    # Chỉ đếm những dòng có dữ liệu thực sự ở cột B (Email)
    # Loại bỏ hoàn toàn các ô trống hoặc chỉ có dấu cách
    col_b = SHEET.col_values(2)
    filled_rows = [row for row in col_b if row.strip()]
    return len(filled_rows) + 1

def append_check_in_to_sheet(user_email, now):
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_vn = datetime.now(vn_tz) # Lấy giờ VN ngay lúc này
    
    # KIỂM TRA CUỐI CÙNG TRƯỚC KHI GHI
    clean_email = str(user_email).strip()
    if not clean_email:
        return False

    load_data.clear()
    next_row = find_next_available_row() + 1
    
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    new_row = [new_stt, clean_email, now_vn.strftime('%Y-%m-%d %H:%M:%S'), '', '', 'Chờ duyệt']
    SHEET.update(f"A{next_row}:F{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now, note):
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_vn = datetime.now(vn_tz) # Lấy giờ VN ngay lúc này
    clean_email = str(user_email).strip()
    if not clean_email:
        return False

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

# --- STREAMLIT UI ---

st.set_page_config(layout="wide", page_title="Hệ thống Chấm công")
st.title("⏰ Hệ thống Chấm công")

# Xử lý Email đầu vào
raw_email = st.text_input("📧 Email người dùng", value=st.session_state.get('last_user_email', ''), placeholder="Nhập email hoặc Tên của bạn (vd: user@gmail.com hoặc Nguyễn Văn A)-Lưu ý tên Check in và Check out phải nhập giống nhau")
user_email = raw_email.strip() # Loại bỏ khoảng trắng thừa
st.session_state.last_user_email = user_email

st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("🟢 CHECK IN", use_container_width=True):
        if not user_email:
            st.error("❗ KHÔNG THỂ GHI: Ô Email đang trống.")
        else:
            if append_check_in_to_sheet(user_email, datetime.now()):
                st.toast("Check In thành công!")
                st.rerun()
            else:
                st.error("Lỗi dữ liệu thực thi.")

with col2:
    if st.button("🔴 CHECK OUT", use_container_width=True):
        if not user_email:
            st.error("❗ KHÔNG THỂ GHI: Ô Email đang trống.")
        else:
            note_val = st.session_state.get('work_note_input_widget', '')
            if update_check_out_in_sheet(user_email, datetime.now(), note_val):
                st.toast("Check Out thành công!")
                st.session_state['work_note_input_widget'] = ""
                st.rerun()
            else:
                st.error("Không tìm thấy phiên Check In chưa đóng.")

with col3:

    # Note input field

    note = st.text_input(

        "📝 **Ghi chú Địa điểm làm việc (sẽ được lưu khi Check Out)**", 

        key='work_note_input_widget', 

        placeholder="VD: Làm việc tại văn phòng/remote"

    )



st.markdown("---")
df_display = load_data()
if not df_display.empty:
    # Hiển thị dữ liệu, lọc bỏ các dòng mà cột 'Tên người dùng' bị trống (nếu lỡ có dòng lỗi cũ)
    valid_df = df_display[df_display['Tên người dùng'].str.strip() != ""]
    st.dataframe(valid_df.iloc[::-1], use_container_width=True, hide_index=True)







