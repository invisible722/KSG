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

# --- 2. HÀM XỬ LÝ CHỐNG GHI ĐÈ ---

def append_check_in_to_sheet(user_email, now_vn):
    # Lấy toàn bộ dữ liệu cột B (Tên người dùng) để xác định dòng cuối cùng thực sự
    col_b_values = SHEET.col_values(2) 
    # Dòng tiếp theo sẽ là số lượng phần tử hiện tại + 1
    # Nếu chỉ có tiêu đề, col_b_values là 1 phần tử -> dòng tiếp theo là 2.
    # Nếu đã có 1 người, col_b_values là 2 phần tử -> dòng tiếp theo là 3.
    next_row = len(col_b_values) + 1
    
    # Tính Số thứ tự (STT) dựa trên cột A
    col_a_values = SHEET.col_values(1)
    stt_nums = [int(x) for x in col_a_values[1:] if str(x).isdigit()]
    new_stt = max(stt_nums) + 1 if stt_nums else 1
    
    new_row = [
        new_stt, 
        str(user_email).strip(), 
        now_vn.strftime('%Y-%m-%d %H:%M:%S'), 
        "", "", "Chờ duyệt", ""
    ]
    
    # Ghi dữ liệu vào dải ô chính xác (A{next_row} đến G{next_row})
    # Việc chỉ định rõ dải ô sẽ ngăn Google Sheets ghi đè lên dòng cũ
    SHEET.update(f"A{next_row}:G{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now_vn, note_content):
    if not note_content or str(note_content).strip() == "":
        return "EMPTY_NOTE"

    # Lấy dữ liệu tươi để tìm dòng
    all_rows = SHEET.get_all_values()
    target_row_idx = -1
    clean_user = str(user_email).strip().lower()

    # Quét ngược từ dưới lên để tìm đúng dòng của user chưa check-out
    for i in range(len(all_rows) - 1, 0, -1):
        row = all_rows[i]
        if len(row) > 1 and row[1].strip().lower() == clean_user:
            # Kiểm tra cột D (index 3) có trống không
            if len(row) <= 3 or row[3].strip() == "":
                target_row_idx = i + 1
                break

    if target_row_idx != -1:
        # Cập nhật cột D (4) và E (5) bằng tọa độ chính xác
        SHEET.update_cell(target_row_idx, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row_idx, 5, str(note_content).strip())
        return "SUCCESS"
    return "NOT_FOUND"

# --- 3. GIAO DIỆN (UI) ---
st.set_page_config(layout="wide", page_title="Chấm Công")
st.title("⏰ Hệ thống Chấm công")

with st.form("main_form"):
    st.info("Lưu ý: Bạn phải nhập Ghi chú địa điểm làm việc khi thực hiện Check Out.")
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
        st.success(f"Check In thành công!")
        st.rerun()

if btn_out:
    clean_note = note_in.strip()
    if not email_final:
        st.error("Vui lòng nhập tên!")
    elif not clean_note:
        st.error("❌ LỖI: Bạn phải nhập ghi chú địa điểm mới được Check Out!")
        st.stop()
    else:
        res = update_check_out_in_sheet(email_final, now, clean_note)
        if res == "SUCCESS":
            st.success("Check Out thành công!")
            st.rerun()
        else:
            st.error("❌ Không tìm thấy lượt Check In nào chưa đóng của bạn.")

# --- 5. HIỂN THỊ ---
st.write("---")
data_final = SHEET.get_all_values()
if len(data_final) > 1:
    df = pd.DataFrame(data_final[1:], columns=COLUMNS)
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
