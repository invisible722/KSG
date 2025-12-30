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
    st.error(f"Lỗi hệ thống: {e}")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt']
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 2. HÀM XỬ LÝ DỮ LIỆU (DATABASE LAYER) ---

@st.cache_data(ttl=2)
def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1: return pd.DataFrame(columns=COLUMNS)
        return pd.DataFrame(all_values[1:], columns=COLUMNS)
    except: return pd.DataFrame(columns=COLUMNS)

def update_check_out_in_sheet(user_email, now_vn, note_to_save):
    """
    HÀM NÀY LÀ CHỐT CHẶN CUỐI CÙNG. 
    NẾU note_to_save TRỐNG, NÓ SẼ TRẢ VỀ FALSE VÀ KHÔNG GHI GÌ CẢ.
    """
    # KIỂM TRA CỨNG: Nếu không có ghi chú, thoát ngay lập tức
    if not note_to_save or str(note_to_save).strip() == "":
        return False

    load_data.clear()
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    target_row = -1
    for i in range(len(emails) - 1, 0, -1):
        if emails[i].strip() == str(user_email).strip():
            if i >= len(checkouts) or not checkouts[i].strip():
                target_row = i + 1
                break
    
    if target_row != -1:
        # Ghi giờ Out và Ghi chú vào cột 4 và 5
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, str(note_to_save).strip())
        return True
    return False

def append_check_in_to_sheet(user_email, now_vn):
    load_data.clear()
    col_b = SHEET.col_values(2)
    next_row = len([row for row in col_b if row.strip()]) + 1
    
    stt_col = SHEET.col_values(1)[1:]
    stt_nums = [int(x) for x in stt_col if str(x).isdigit()]
    new_stt = max(stt_nums) + 1 if stt_nums else 1
    
    new_row = [new_stt, user_email, now_vn.strftime('%Y-%m-%d %H:%M:%S'), '', '', 'Chờ duyệt', '']
    SHEET.update(f"A{next_row}:G{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

# --- 3. GIAO DIỆN NGƯỜI DÙNG (UI LAYER) ---

st.set_page_config(layout="wide", page_title="Chấm Công TTS")
st.title("⏰ Hệ thống Chấm công")

# Sử dụng FORM để đảm bảo dữ liệu được gửi đi đồng thời
with st.form("attendance_form"):
    st.write("### Nhập thông tin")
    
    input_email = st.text_input("📧 Email / Tên", value=st.session_state.get('saved_email', ''))
    
    # ĐÂY LÀ Ô GHI CHÚ QUAN TRỌNG
    input_note = st.text_input("📝 Ghi chú địa điểm (BẮT BUỘC KHI CHECK OUT)")
    
    st.write("---")
    c1, c2 = st.columns(2)
    do_in = c1.form_submit_button("🟢 CHECK IN", use_container_width=True)
    do_out = c2.form_submit_button("🔴 CHECK OUT", use_container_width=True)

# --- 4. LOGIC KIỂM TRA (SECURITY LAYER) ---

email_final = input_email.strip()
st.session_state.saved_email = email_final
now = datetime.now(VN_TZ)

if do_in:
    if not email_final:
        st.error("Vui lòng nhập tên!")
    else:
        if append_check_in_to_sheet(email_final, now):
            st.success("Check In thành công!")
            st.rerun()

if do_out:
    # Lấy giá trị ghi chú và xóa khoảng trắng
    note_final = input_note.strip()
    
    # KIỂM TRA 1: Email
    if not email_final:
        st.error("Vui lòng nhập tên!")
    
    # KIỂM TRA 2: Ghi chú (Đây là nơi chặn lỗi)
    elif note_final == "":
        st.error("❌ LỖI: Bạn KHÔNG THỂ Check Out vì chưa nhập ghi chú!")
        st.warning("Hãy nhập địa điểm làm việc vào ô 'Ghi chú địa điểm' phía trên rồi bấm lại.")
        # Lệnh st.stop() này sẽ ngăn không cho bất kỳ code nào bên dưới chạy
        st.stop() 
        
    else:
        # KIỂM TRA 3: Chỉ khi có ghi chú mới gọi hàm ghi vào Sheet
        if update_check_out_in_sheet(email_final, now, note_final):
            st.success("Check Out thành công!")
            st.rerun()
        else:
            st.error("Không tìm thấy lượt Check In nào chưa đóng.")

# --- 5. HIỂN THỊ BẢNG ---
st.write("---")
df_view = load_data()
if not df_view.empty:
    st.dataframe(df_view.iloc[::-1], use_container_width=True, hide_index=True)
