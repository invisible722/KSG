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

@st.cache_data(ttl=5)
def load_data():
    """Tải dữ liệu từ Google Sheet."""
    try:
        # Lấy toàn bộ dữ liệu bao gồm cả các dòng trống phía sau để xác định đúng vị trí
        data = SHEET.get_all_records()
        df = pd.DataFrame(data, columns=COLUMNS)
        df['Thời gian Check in'] = pd.to_datetime(df['Thời gian Check in'], errors='coerce')
        df['Thời gian Check out'] = pd.to_datetime(df['Thời gian Check out'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {e}")
        return pd.DataFrame(columns=COLUMNS)

def append_check_in_to_sheet(user_email, now):
    """Ghi bản ghi Check In mới vào dòng cuối cùng thực tế của Sheet."""
    load_data.clear()
    
    # 1. Tính toán STT dựa trên dòng cuối cùng có dữ liệu
    all_values = SHEET.get_all_values()
    last_row_index = len(all_values)
    
    # 2. Lấy STT lớn nhất hiện có để tránh trùng lặp hoặc nhảy số
    stt_column = SHEET.col_values(1)[1:] # Lấy cột A bỏ tiêu đề
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    # 3. Tạo dòng mới
    new_row = [new_stt, user_email, now.strftime('%Y-%m-%d %H:%M:%S'), '', '']
    
    # 4. Sử dụng append_row để Google Sheets tự tìm dòng trống tiếp theo
    SHEET.append_row(new_row, value_input_option='USER_ENTERED')

def update_check_out_in_sheet(pandas_index, now, note):
    """Cập nhật giờ Check Out dựa trên index của DataFrame."""
    load_data.clear()
    
    # Vị trí dòng trên Google Sheet = Index của Pandas + 2 (1 cho tiêu đề, 1 cho bắt đầu từ 1)
    sheet_row_number = int(pandas_index) + 2 
    
    # Cập nhật cột 4 (Check out) và cột 5 (Ghi chú)
    SHEET.update_cell(sheet_row_number, 4, now.strftime('%Y-%m-%d %H:%M:%S'))
    SHEET.update_cell(sheet_row_number, 5, note)

# --- STREAMLIT UI ---

st.set_page_config(layout="wide", page_title="Hệ thống Chấm công")
st.title("⏰ Hệ thống Chấm công Google Sheets")

user_email = st.text_input(
    "📧 **Email người dùng**",
    key='user_email_input',
    value=st.session_state.get('last_user_email', ''),
    placeholder="Nhập email để chấm công..."
)
st.session_state.last_user_email = user_email
st.markdown("---")

col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("🟢 CHECK IN", use_container_width=True):
        if not user_email:
            st.warning("⚠️ Vui lòng nhập Email.")
        else:
            now = datetime.now()
            append_check_in_to_sheet(user_email, now)
            st.toast(f"✅ Đã Check In cho {user_email}")
            st.rerun()

with col2:
    if st.button("🔴 CHECK OUT", use_container_width=True):
        if not user_email:
            st.warning("⚠️ Vui lòng nhập Email.")
        else:
            current_data = load_data()
            # Tìm dòng Check-in cuối cùng của người này mà chưa có Check-out
            user_records = current_data[
                (current_data['Tên người dùng'] == user_email) & 
                (pd.isna(current_data['Thời gian Check out']))
            ]
            
            if not user_records.empty:
                last_idx = user_records.index[-1]
                note_val = st.session_state.get('work_note_input_widget', '')
                update_check_out_in_sheet(last_idx, datetime.now(), note_val)
                
                if 'work_note_input_widget' in st.session_state:
                    st.session_state['work_note_input_widget'] = ""
                st.toast("✅ Đã Check Out thành công")
                st.rerun()
            else:
                st.toast("⚠️ Bạn không có phiên Check In nào đang mở.", icon="⚠️")

with col3:
    st.text_input(
        "📝 **Ghi chú (Lưu khi Check Out)**", 
        key='work_note_input_widget'
    )

st.markdown("---")
st.subheader("📊 Bảng dữ liệu hiện tại")
display_df = load_data().copy()

# Định dạng hiển thị
for col in ['Thời gian Check in', 'Thời gian Check out']:
    display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

st.dataframe(display_df, use_container_width=True, hide_index=True)
