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
    # Lấy toàn bộ dữ liệu cột Email và cột Check-out
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    target_row = -1
    # Duyệt từ dưới lên trên để tìm lần Check-in mới nhất mà chưa Check-out
    for i in range(len(emails) - 1, 0, -1):
        if emails[i].strip() == str(user_email).strip():
            # Nếu cột Check-out (cột 4) của dòng này còn trống
            if i >= len(checkouts) or not checkouts[i].strip():
                target_row = i + 1
                break
    
    if target_row != -1:
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, str(content_note).strip())
        return "SUCCESS"
    return "NOT_FOUND"

def append_check_in_to_sheet(user_email, now_vn):
    """
    Sử dụng append_row để Google Sheets tự tìm dòng trống cuối cùng, 
    tránh hoàn toàn việc ghi đè dữ liệu cũ.
    """
    clean_email = str(user_email).strip()
    
    # Lấy toàn bộ cột STT để tính số thứ tự mới
    stt_col = SHEET.col_values(1)[1:] # Bỏ qua tiêu đề
    stt_nums = [int(x) for x in stt_col if str(x).isdigit()]
    new_stt = max(stt_nums) + 1 if stt_nums else 1
    
    # Chuẩn bị dữ liệu dòng mới (7 cột)
    new_row_data = [
        new_stt, 
        clean_email, 
        now_vn.strftime('%Y-%m-%d %H:%M:%S'), 
        '', # Check out trống
        '', # Ghi chú trống
        'Chờ duyệt', 
        ''  # Người duyệt trống
    ]
    
    # Dùng lệnh append_row để Google tự chèn vào dòng cuối cùng
    SHEET.append_row(new_row_data, value_input_option='USER_ENTERED')
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

