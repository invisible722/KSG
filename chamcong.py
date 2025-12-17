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
    st.error("Lỗi: Không tìm thấy thông tin cấu hình trong Streamlit Secrets (sheet_id, worksheet_name, base64_service_account).")
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
    """Tải dữ liệu an toàn từ Google Sheet."""
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
    """Tìm dòng thực sự trống tiếp theo dựa trên cột Tên người dùng (Cột B)."""
    # Lấy toàn bộ cột B, loại bỏ các giá trị rỗng để đếm số dòng đã có dữ liệu
    col_b_values = list(filter(None, SHEET.col_values(2))) 
    return len(col_b_values) + 1

def append_check_in_to_sheet(user_email, now):
    """Ghi Check In vào dòng mới nhất."""
    load_data.clear()
    
    # Xác định dòng kế tiếp để ghi
    next_row = find_next_available_row() + 1
    
    # Tính số thứ tự (STT) dựa trên cột A
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    new_row = [new_stt, user_email, now.strftime('%Y-%m-%d %H:%M:%S'), '', '']
    
    # Ghi chính xác vào dòng next_row
    SHEET.update(f"A{next_row}:E{next_row}", [new_row], value_input_option='USER_ENTERED')

def update_check_out_in_sheet(user_email, now, note):
    """Tìm dòng Check In cuối cùng của user để cập nhật Check Out."""
    load_data.clear()
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    target_row = -1
    # Duyệt ngược để tìm dòng mới nhất chưa có thời gian Check out
    for i in range(len(emails) - 1, 0, -1):
        if emails[i] == user_email:
            if i >= len(checkouts) or checkouts[i] == "" or checkouts[i] is None:
                target_row = i + 1
                break
    
    if target_row != -1:
        SHEET.update_cell(target_row, 4, now.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, note)
        return True
    return False

# --- STREAMLIT UI ---

st.set_page_config(layout="wide", page_title="Hệ thống Chấm công Fix")
st.title("⏰ Hệ thống Chấm công Google Sheets")

# 1. NHẬP EMAIL VÀ KIỂM TRA DỮ LIỆU
user_email = st.text_input(
    "📧 **Email người dùng**", 
    value=st.session_state.get('last_user_email', ''),
    placeholder="Bắt buộc nhập email để chấm công..."
)
st.session_state.last_user_email = user_email

# Điều kiện kiểm tra Email ngay tại giao diện chính
if not user_email:
    st.error("❗ **YÊU CẦU NHẬP DỮ LIỆU:** Vui lòng nhập Email trước khi thực hiện Check In hoặc Check Out.")
    # Ngưng các xử lý bên dưới nếu không có email
    st.stop() 

st.markdown("---")

# --- NÚT BẤM VÀ GHI CHÚ ---
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("🟢 CHECK IN", use_container_width=True):
        now = datetime.now()
        append_check_in_to_sheet(user_email, now)
        st.toast(f"✅ Check In thành công: {user_email}")
        st.rerun()

with col2:
    if st.button("🔴 CHECK OUT", use_container_width=True):
        note_val = st.session_state.get('work_note_input_widget', '')
        success = update_check_out_in_sheet(user_email, datetime.now(), note_val)
        
        if success:
            st.toast("✅ Check Out thành công!")
            st.session_state['work_note_input_widget'] = ""
            st.rerun()
        else:
            st.warning("⚠️ Không tìm thấy phiên Check In nào chưa hoàn thành của bạn.")

with col3:
    st.text_input("📝 Ghi chú công việc", key='work_note_input_widget', placeholder="Lưu khi Check Out")

st.markdown("---")

# --- HIỂN THỊ DỮ LIỆU ---
st.subheader("📊 Nhật ký chấm công (Mới nhất lên đầu)")
data = load_data()
if not data.empty:
    # Định dạng hiển thị ngày tháng
    display_df = data.copy()
    for col in ['Thời gian Check in', 'Thời gian Check out']:
        display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
    
    # Đảo ngược để dòng mới nhất lên trên cùng của bảng hiển thị
    st.dataframe(display_df.iloc[::-1], use_container_width=True, hide_index=True)
