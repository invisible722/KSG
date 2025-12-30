import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz

# --- 1. CẤU HÌNH & KẾT NỐI ---
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

# --- 2. HÀM XỬ LÝ (CHẶN TẠI GỐC) ---

def update_check_out_in_sheet(user_email, now_vn, content_note):
    # LỚP BẢO VỆ 1: CHẶN TẠI HÀM (Nếu content_note trống, thoát ngay)
    if not content_note or str(content_note).strip() == "":
        return "ERROR_EMPTY_NOTE"

    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    target_row = -1
    for i in range(len(emails) - 1, 0, -1):
        if emails[i].strip() == str(user_email).strip():
            if i >= len(checkouts) or not checkouts[i].strip():
                target_row = i + 1
                break
    
    if target_row != -1:
        # CHỈ GHI KHI CÓ GIÁ TRỊ THỰC
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, str(content_note).strip())
        return "SUCCESS"
    return "NOT_FOUND"

def append_check_in_to_sheet(user_email, now_vn):
    col_b = SHEET.col_values(2)
    next_row = len([row for row in col_b if row.strip()]) + 1
    stt_col = SHEET.col_values(1)[1:]
    stt_nums = [int(x) for x in stt_col if str(x).isdigit()]
    new_stt = max(stt_nums) + 1 if stt_nums else 1
    new_row = [new_stt, user_email, now_vn.strftime('%Y-%m-%d %H:%M:%S'), '', '', 'Chờ duyệt', '']
    SHEET.update(f"A{next_row}:G{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

# --- 3. GIAO DIỆN (UI) ---

st.set_page_config(layout="wide", page_title="Chấm Công")
st.title("⏰ Hệ thống Chấm công")

# FORM BẢO VỆ DỮ LIỆU
with st.form("attendance_form"):
    st.write("### Nhập thông tin")
    input_email = st.text_input("📧 Email / Tên", value=st.session_state.get('saved_email', ''))
    
    # Ô nhập ghi chú
    input_note = st.text_input("📝 Ghi chú địa điểm (BẮT BUỘC KHI CHECK OUT)", key="note_field")
    
    st.write("---")
    c1, c2 = st.columns(2)
    do_in = c1.form_submit_button("🟢 CHECK IN", use_container_width=True)
    do_out = c2.form_submit_button("🔴 CHECK OUT", use_container_width=True)

# --- 4. LOGIC XỬ LÝ ---

email_final = input_email.strip()
st.session_state.saved_email = email_final
now = datetime.now(VN_TZ)

if do_in:
    if not email_final:
        st.error("Vui lòng nhập tên!")
    else:
        append_check_in_to_sheet(email_final, now)
        st.success("Check In thành công!")
        st.rerun()

if do_out:
    # LÀM SẠCH GHI CHÚ NGAY LẬP TỨC
    clean_note = input_note.strip()
    
    # KIỂM TRA ĐIỀU KIỆN
    if not email_final:
        st.error("Vui lòng nhập tên!")
    elif not clean_note:
        # HIỆN LỖI VÀ NGẮT LUỒNG NGAY TẠI ĐÂY
        st.error("❌ LỖI: Ghi chú không được để trống khi Check Out!")
        st.warning("Vui lòng điền 'Địa điểm làm việc' rồi bấm lại.")
    else:
        # GỌI HÀM VÀ KIỂM TRA KẾT QUẢ TRẢ VỀ
        result = update_check_out_in_sheet(email_final, now, clean_note)
        
        if result == "SUCCESS":
            st.success("Check Out thành công!")
            st.rerun()
        elif result == "ERROR_EMPTY_NOTE":
            st.error("❌ Hệ thống đã chặn Check Out vì Ghi chú trống!")
        else:
            st.error("❌ Không tìm thấy lượt Check In nào chưa đóng.")

# --- 5. HIỂN THỊ ---
st.write("---")
all_vals = SHEET.get_all_values()
if len(all_vals) > 1:
    df_view = pd.DataFrame(all_vals[1:], columns=COLUMNS)
    st.dataframe(df_view.iloc[::-1], use_container_width=True, hide_index=True)
