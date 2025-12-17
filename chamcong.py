import streamlit as st

import pandas as pd

from datetime import datetime

import gspread

import os

import json

import base64



# --- CẤU HÌNH GOOGLE SHEETS (Đọc từ Streamlit Secrets) ---

try:

    SHEET_ID = st.secrets["sheet_id"] 

    WORKSHEET_NAME = st.secrets["worksheet_name"]

    BASE64_CREDS = st.secrets["base64_service_account"] 

except Exception:

    st.error("Lỗi: Không tìm thấy thông tin cấu hình trong Streamlit Secrets (sheet_id, worksheet_name, base64_service_account). Vui lòng kiểm tra file secrets.toml.")

    st.stop()



# Define columns (MUST match the headers in Google Sheet)

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú'] 



# --- THIẾT LẬP KẾT NỐI (Decoding Base64) ---

try:

    CREDS_DICT = {}

    try:

        # 1. Giải mã chuỗi Base64 thành nội dung JSON (bytes)

        decoded_json_bytes = base64.b64decode(BASE64_CREDS)

        

        # 2. Tải nội dung JSON thành Python dictionary

        CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 

    except Exception as base64_error:

        # Lỗi giải mã Base64 thường do chuỗi bị hỏng hoặc có ký tự thừa

        st.error(f"LỖI GIẢI MÃ BASE64: Chuỗi Base64 có thể bị lỗi định dạng. Chi tiết lỗi: {base64_error}")

        st.stop()



    # 3. Sử dụng dictionary để xác thực

    CLIENT = gspread.service_account_from_dict(CREDS_DICT)

    

    # 4. Use open_by_key to connect using the Sheet ID

    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)



except Exception as e:

    # Lỗi JWT Signature sẽ rơi vào đây.

    st.error(f"Lỗi kết nối Google Sheets. Chi tiết lỗi: {e}. Vui lòng kiểm tra:\n1. ID Sheet và Tên Worksheet.\n2. Email dịch vụ đã được chia sẻ quyền EDIT Sheet.\n3. Khóa dịch vụ Base64 được tạo MỚI và dán ĐÚNG định dạng.")

    st.stop()





# --- DATA LOADING AND WRITING FUNCTIONS ---



@st.cache_data(ttl=5) # Cache 5 giây để giảm tải cho API

def load_data():

    """Tải dữ liệu từ Google Sheet."""

    try:

        data = SHEET.get_all_records()

        df = pd.DataFrame(data, columns=COLUMNS)

        

        # Convert to datetime, coercing errors to NaT

        df['Thời gian Check in'] = pd.to_datetime(df['Thời gian Check in'], errors='coerce')

        df['Thời gian Check out'] = pd.to_datetime(df['Thời gian Check out'], errors='coerce')

        return df

    except Exception as e:

        # This typically indicates mismatched column headers

        st.error("Lỗi khi tải dữ liệu. Hãy đảm bảo Hàng 1 của Sheet1 chứa **CHÍNH XÁC** các tiêu đề.")

        return pd.DataFrame(columns=COLUMNS)



def append_check_in_to_sheet(user_email, now):

    """Write a new Check In record to the end of the Sheet."""

    load_data.clear() # Clear cache to force reload after write

    

    current_data = SHEET.get_all_values() 

    new_index = len(current_data) 

    

    new_row = [new_index, user_email, now.strftime('%Y-%m-%d %H:%M:%S'), '', '']

    SHEET.append_row(new_row, value_input_option='USER_ENTERED')



def update_check_out_in_sheet(row_index, now, note):

    """Update the Check Out time and Note for an existing Check In record."""

    # Sheet row is Pandas index + 2

    sheet_row_number = row_index + 2 

    

    load_data.clear() 

    

    SHEET.update_cell(sheet_row_number, 4, now.strftime('%Y-%m-%d %H:%M:%S'))

    SHEET.update_cell(sheet_row_number, 5, note)





# --- STREAMLIT APPLICATION LOGIC ---



st.set_page_config(layout="wide", page_title="Hệ thống Chấm công Google Sheets")



st.title("⏰ Hệ thống Chấm công Google Sheets")

st.markdown("---")



# Load initial data

data = load_data()



# --- User Email Input ---



user_email = st.text_input(

    "📧 **Email người dùng (Giả lập tự động lấy từ Google)**",

    key='user_email_input',

    value=st.session_state.get('last_user_email', ''),

    placeholder="Nhập email của bạn (vd: ten.nguoi.dung@gmail.com)"

)

st.session_state.last_user_email = user_email

    

st.markdown("---")



# --- Action Buttons and Note ---

col1, col2, col3 = st.columns([1, 1, 3])



with col1:

    # Check In Button

    if st.button("🟢 CHECK IN", use_container_width=True):

        

        if not user_email:

            st.warning("⚠️ Vui lòng nhập Email người dùng trước khi Check In.")

            st.stop()

            

        now = datetime.now()

        

        append_check_in_to_sheet(user_email, now) 

        

        st.toast(f"✅ Check In thành công cho {user_email} lúc: {now.strftime('%H:%M:%S')}", icon="✅")

        st.rerun() 



with col2:

    # Check Out Button

    if st.button("🔴 CHECK OUT", use_container_width=True):

        

        if not user_email:

            st.warning("⚠️ Vui lòng nhập Email người dùng trước khi Check Out.")

            st.stop()

            

        current_data = load_data() 

        

        # Find the last Check In record without a Check Out time for this user

        user_checkins = current_data[

            (current_data['Tên người dùng'] == user_email) & 

            (pd.isna(current_data['Thời gian Check out']))

        ]

        

        if not user_checkins.empty:

            pandas_index = user_checkins.index[-1] # Get the index of the most recent Check In

            

            now = datetime.now()

            

            note = st.session_state.get('work_note_input_widget', '') 



            update_check_out_in_sheet(pandas_index, now, note)

            

            st.toast(f"✅ Check Out thành công cho {user_email} lúc: {now.strftime('%H:%M:%S')}", icon="✅")

            

            # Clear the note after Check Out

            if 'work_note_input_widget' in st.session_state:

                st.session_state['work_note_input_widget'] = ""

            

            st.rerun()



        else:

             st.toast("⚠️ Vui lòng Check In trước khi Check Out hoặc bạn đã Check Out rồi.", icon="⚠️")





with col3:

    # Note input field

    note = st.text_input(

        "📝 **Ghi chú Địa điểm làm việc (sẽ được lưu khi Check Out)**", 

        key='work_note_input_widget', 

        placeholder="VD: Làm việc tại văn phòng/remote"

    )



st.markdown("---")



## 📊 Timesheet Data Table

st.subheader("Bảng dữ liệu Chấm công (Lấy từ Google Sheet)")



# Load the final data for display

display_data = load_data().copy()



# Helper function to format datetime objects cleanly

def format_datetime(dt):

    if pd.isna(dt):

        return ''

    return dt.strftime('%Y-%m-%d %H:%M:%S')



display_data['Thời gian Check in'] = display_data['Thời gian Check in'].apply(format_datetime)

display_data['Thời gian Check out'] = display_data['Thời gian Check out'].apply(format_datetime)



st.dataframe(display_data, use_container_width=True, hide_index=True)



st.markdown("---")
