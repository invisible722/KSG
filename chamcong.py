import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- CẤU HÌNH GOOGLE SHEETS (Đọc từ Streamlit Secrets) ---
# Đảm bảo các mục này đã được thiết lập trong st.secrets
try:
    SHEET_ID = st.secrets["sheet_id"] # SỬ DỤNG SHEET ID
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    CREDS_DICT = st.secrets["gservice_account"]
except Exception:
    st.error("Lỗi: Không tìm thấy thông tin xác thực trong Streamlit Secrets (sheet_id, worksheet_name, gservice_account). Vui lòng kiểm tra Bước 1.")
    st.stop()

# Định nghĩa các cột (PHẢI KHỚP VỚI TIÊU ĐỀ TRONG GOOGLE SHEET)
COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú'] 

# --- THIẾT LẬP KẾT NỐI ---
try:
    # Sử dụng service_account_from_dict để đọc trực tiếp từ dict secrets
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    
    # SỬ DỤNG open_by_key để kết nối bằng ID, đáng tin cậy hơn open(name)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets. Vui lòng kiểm tra ID Sheet, tên Worksheet '{WORKSHEET_NAME}', quyền truy cập (chia sẻ email dịch vụ) và file xác thực. Chi tiết lỗi: {e}")
    st.stop()


# --- HÀM TẢI VÀ GHI DỮ LIỆU ---

@st.cache_data(ttl=5) # Cache 5 giây để giảm tải cho API
def load_data():
    """Tải dữ liệu từ Google Sheet."""
    try:
        data = SHEET.get_all_records()
        df = pd.DataFrame(data, columns=COLUMNS)
        
        df['Thời gian Check in'] = pd.to_datetime(df['Thời gian Check in'], errors='coerce')
        df['Thời gian Check out'] = pd.to_datetime(df['Thời gian Check out'], errors='coerce')
        return df
    except Exception as e:
        st.error("Lỗi khi tải dữ liệu. Hãy đảm bảo Hàng 1 của Sheet1 chứa **CHÍNH XÁC** các tiêu đề: Số thứ tự, Tên người dùng, Thời gian Check in, Thời gian Check out, Ghi chú.")
        return pd.DataFrame(columns=COLUMNS)

def append_check_in_to_sheet(user_email, now):
    """Ghi dữ liệu Check In mới vào hàng cuối của Sheet."""
    load_data.clear() 
    
    current_data = SHEET.get_all_values() 
    new_index = len(current_data) 
    
    new_row = [new_index, user_email, now.strftime('%Y-%m-%d %H:%M:%S'), '', '']
    SHEET.append_row(new_row, value_input_option='USER_ENTERED')

def update_check_out_in_sheet(row_index, now, note):
    """Cập nhật thời gian Check Out và Ghi chú cho hàng đã Check In."""
    sheet_row_number = row_index + 2
    
    load_data.clear() 
    
    # Cột 4 (Thời gian Check out) và Cột 5 (Ghi chú)
    SHEET.update_cell(sheet_row_number, 4, now.strftime('%Y-%m-%d %H:%M:%S'))
    SHEET.update_cell(sheet_row_number, 5, note)


# --- LOGIC ỨNG DỤNG STREAMLIT ---

st.set_page_config(layout="wide", page_title="Hệ thống Chấm công Google Sheets")

st.title("⏰ Hệ thống Chấm công Google Sheets")
st.markdown("---")

# Tải dữ liệu ban đầu
data = load_data()

# --- Vùng nhập Email (Giả lập tự động lấy từ Google) ---

user_email = st.text_input(
    "📧 **Email người dùng (Giả lập tự động lấy từ Google)**",
    key='user_email_input',
    value=st.session_state.get('last_user_email', ''),
    placeholder="Nhập email của bạn (vd: ten.nguoi.dung@gmail.com)"
)
st.session_state.last_user_email = user_email
    
st.markdown("---")

# --- Vùng Thao tác và Ghi chú ---
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    # Nút Check In
    if st.button("🟢 CHECK IN", use_container_width=True):
        
        if not user_email:
            st.warning("⚠️ Vui lòng nhập Email người dùng trước khi Check In.")
            st.stop()
            
        now = datetime.now()
        
        append_check_in_to_sheet(user_email, now) 
        
        st.toast(f"✅ Check In thành công cho {user_email} lúc: {now.strftime('%H:%M:%S')}", icon="✅")
        st.rerun() 

with col2:
    # Nút Check Out
    if st.button("🔴 CHECK OUT", use_container_width=True):
        
        if not user_email:
            st.warning("⚠️ Vui lòng nhập Email người dùng trước khi Check Out.")
            st.stop()
            
        current_data = load_data() 
        
        user_checkins = current_data[
            (current_data['Tên người dùng'] == user_email) & 
            (pd.isna(current_data['Thời gian Check out']))
        ]
        
        if not user_checkins.empty:
            pandas_index = user_checkins.index[-1] 
            
            now = datetime.now()
            
            note = st.session_state.get('work_note_input_widget', '') 

            update_check_out_in_sheet(pandas_index, now, note)
            
            st.toast(f"✅ Check Out thành công cho {user_email} lúc: {now.strftime('%H:%M:%S')}", icon="✅")
            
            if 'work_note_input_widget' in st.session_state:
                st.session_state['work_note_input_widget'] = ""
            
            st.rerun()

        elif not current_data.empty and current_data.loc[current_data.index[-1], 'Tên người dùng'] != user_email:
             st.warning(f"⚠️ Bản ghi Check In gần nhất không phải của {user_email}. Vui lòng Check In trước.")
        else:
             st.toast("⚠️ Vui lòng Check In trước khi Check Out.", icon="⚠️")


with col3:
    # Ô nhập Ghi chú 
    note = st.text_input(
        "📝 **Ghi chú Địa điểm làm việc (sẽ được lưu khi Check Out)**", 
        key='work_note_input_widget', 
        placeholder="VD: Làm việc tại văn phòng/remote"
    )

st.markdown("---")

## 📊 Bảng Dữ liệu Chấm công
st.subheader("Bảng dữ liệu Chấm công (Lấy từ Google Sheet)")

# Tải dữ liệu lần cuối để hiển thị
display_data = load_data().copy()

# Định dạng lại thời gian cho dễ nhìn
def format_datetime(dt):
    if pd.isna(dt):
        return ''
    return dt.strftime('%Y-%m-%d %H:%M:%S')

display_data['Thời gian Check in'] = display_data['Thời gian Check in'].apply(format_datetime)
display_data['Thời gian Check out'] = display_data['Thời gian Check out'].apply(format_datetime)

st.dataframe(display_data, use_container_width=True, hide_index=True)

st.markdown("---")
