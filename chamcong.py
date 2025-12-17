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

@st.cache_data(ttl=2) # Giảm TTL để cập nhật nhanh hơn
def load_data():
    """Tải dữ liệu an toàn."""
    try:
        # Lấy tất cả giá trị để đếm dòng chính xác nhất
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1: # Chỉ có tiêu đề hoặc trống
            return pd.DataFrame(columns=COLUMNS)
        
        # Chuyển thành DataFrame (bỏ dòng tiêu đề)
        df = pd.DataFrame(all_values[1:], columns=COLUMNS)
        
        # Ép kiểu dữ liệu
        df['Thời gian Check in'] = pd.to_datetime(df['Thời gian Check in'], errors='coerce')
        df['Thời gian Check out'] = pd.to_datetime(df['Thời gian Check out'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame(columns=COLUMNS)

def find_next_available_row():
    """Tìm dòng thực sự trống tiếp theo (tránh lỗi ghi đè lên dòng 2)."""
    str_list = list(filter(None, SHEET.col_values(2))) # Lấy cột 'Tên người dùng' (Cột B)
    return len(str_list) + 1

def append_check_in_to_sheet(user_email, now):
    """Ghi Check In vào dòng mới nhất dựa trên cột Tên người dùng."""
    load_data.clear()
    
    # 1. Tìm dòng trống thực tế dựa trên cột B (Email) để tránh ghi đè
    next_row = find_next_available_row() + 1
    
    # 2. Tính số thứ tự mới
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    # 3. Dữ liệu mới
    new_row = [new_stt, user_email, now.strftime('%Y-%m-%d %H:%M:%S'), '', '']
    
    # 4. Ghi trực tiếp vào dòng next_row thay vì dùng append_row (vốn hay bị lỗi định dạng bảng)
    SHEET.update(f"A{next_row}:E{next_row}", [new_row], value_input_option='USER_ENTERED')

def update_check_out_in_sheet(user_email, now, note):
    """Tìm đúng dòng cuối cùng của user này để update thay vì dùng index hên xui."""
    load_data.clear()
    
    # Lấy toàn bộ cột B để tìm user
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    # Duyệt ngược từ dưới lên để tìm dòng mới nhất của user chưa checkout
    target_row = -1
    for i in range(len(emails) - 1, 0, -1): # i chạy từ cuối lên đầu
        if emails[i] == user_email:
            # Kiểm tra xem dòng này đã checkout chưa (cột D)
            # Nếu độ dài checkouts ngắn hơn i, nghĩa là ô đó trống
            if i >= len(checkouts) or checkouts[i] == "" or checkouts[i] is None:
                target_row = i + 1 # Chuyển về index của Google Sheet (bắt đầu từ 1)
                break
    
    if target_row != -1:
        SHEET.update_cell(target_row, 4, now.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, note)
        return True
    return False

# --- STREAMLIT UI ---

st.set_page_config(layout="wide", page_title="Fix Chấm Công")
st.title("⏰ Hệ thống Chấm công (Phiên bản Fix Lỗi)")

user_email = st.text_input("📧 Email người dùng", value=st.session_state.get('last_user_email', ''))
st.session_state.last_user_email = user_email

col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("🟢 CHECK IN", use_container_width=True):
        # BỔ SUNG: Kiểm tra dữ liệu Email trước khi lưu
        if user_email.strip(): # Kiểm tra email có dữ liệu và không chỉ toàn dấu cách
            append_check_in_to_sheet(user_email, datetime.now())
            st.toast("Check In thành công!")
            st.rerun()
        else:
            st.error("⚠️ Vui lòng nhập Email người dùng trước khi Check In!")

with col2:
    if st.button("🔴 CHECK OUT", use_container_width=True):
        if user_email.strip():
            note_val = st.session_state.get('work_note_input_widget', '')
            success = update_check_out_in_sheet(user_email, datetime.now(), note_val)
            if success:
                st.toast("Check Out thành công!")
                st.session_state['work_note_input_widget'] = ""
                st.rerun()
            else:
                st.error("Không tìm thấy dòng Check In chưa đóng của bạn!")
        else:
            st.error("⚠️ Vui lòng nhập Email người dùng trước khi Check Out!")

with col3:
    st.text_input("📝 Ghi chú", key='work_note_input_widget')

st.markdown("---")
df_display = load_data()
if not df_display.empty:
    st.dataframe(df_display.iloc[::-1], use_container_width=True, hide_index=True) # Đảo ngược để xem dòng mới nhất lên đầu
