import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz

# --- 1. KẾT NỐI ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
    decoded_json_bytes = base64.b64decode(BASE64_CREDS)
    CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi cấu hình: {e}")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt']
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 2. HÀM XỬ LÝ DỮ LIỆU ---

def append_check_in_to_sheet(user_email, now_vn):
    """
    Sử dụng chèn dòng trực tiếp để đảm bảo không bao giờ ghi đè dòng 2.
    """
    # Lấy toàn bộ dữ liệu hiện tại
    all_data = SHEET.get_all_values()
    
    # Tính STT mới dựa trên số dòng hiện có (không bao gồm tiêu đề)
    new_stt = len(all_data) if len(all_data) > 0 else 1
    
    # Tạo dữ liệu dòng mới
    new_row = [
        new_stt, 
        str(user_email).strip(), 
        now_vn.strftime('%Y-%m-%d %H:%M:%S'), 
        "", "", "Chờ duyệt", ""
    ]
    
    # LUÔN CHÈN VÀO CUỐI: Cách này an toàn hơn append_row thông thường
    SHEET.insert_row(new_row, index=len(all_data) + 1, value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now_vn, note_content):
    """
    Tìm dòng mới nhất chưa Check-out của user để cập nhật.
    """
    if not note_content or str(note_content).strip() == "":
        return "EMPTY_NOTE"

    # Lấy dữ liệu mới nhất
    all_rows = SHEET.get_all_values()
    target_row_idx = -1
    clean_user = str(user_email).strip().lower()

    # Quét ngược từ dòng cuối lên
    for i in range(len(all_rows) - 1, 0, -1):
        row = all_rows[i]
        # Kiểm tra tên khớp và Cột D (index 3) còn trống
        if len(row) > 1 and row[1].strip().lower() == clean_user:
            if len(row) <= 3 or row[3].strip() == "":
                target_row_idx = i + 1
                break

    if target_row_idx != -1:
        # Cập nhật cột 4 (D) và 5 (E)
        SHEET.update_cell(target_row_idx, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row_idx, 5, str(note_content).strip())
        return "SUCCESS"
    return "NOT_FOUND"

# --- 3. GIAO DIỆN ---
st.set_page_config(layout="wide", page_title="Chấm Công")
st.title("⏰ Hệ thống Chấm công")

with st.form("main_form"):
    email_in = st.text_input("📧 Email / Tên người dùng", value=st.session_state.get('last_mail', ''))
    note_in = st.text_input("📝 Ghi chú địa điểm (Bắt buộc khi Check Out)")
    c1, c2 = st.columns(2)
    btn_in = c1.form_submit_button("🟢 CHECK IN", use_container_width=True)
    btn_out = c2.form_submit_button("🔴 CHECK OUT", use_container_width=True)

# --- 4. LOGIC ĐIỀU KHIỂN ---
email_final = email_in.strip()
st.session_state.last_mail = email_final
now = datetime.now(VN_TZ)

if btn_in:
    if not email_final:
        st.error("Vui lòng nhập tên!")
    else:
        append_check_in_to_sheet(email_final, now)
        st.success("Đã ghi nhận Check In vào dòng mới!")
        st.rerun()

if btn_out:
    clean_note = note_in.strip()
    if not email_final:
        st.error("Vui lòng nhập tên!")
    elif not clean_note:
        st.error("❌ Bạn phải nhập ghi chú địa điểm để Check Out!")
    else:
        res = update_check_out_in_sheet(email_final, now, clean_note)
        if res == "SUCCESS":
            st.success("Check Out thành công!")
            st.rerun()
        else:
            st.error("❌ Không tìm thấy lượt Check In nào đang mở cho bạn.")

# --- 5. HIỂN THỊ ---
st.write("---")
data_final = SHEET.get_all_values()
if len(data_final) > 1:
    df = pd.DataFrame(data_final[1:], columns=COLUMNS)
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
