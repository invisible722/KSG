import streamlit as st
import pandas as pd
import gspread
from gspread.exceptions import APIError, WorksheetNotFound, SpreadsheetNotFound
from datetime import datetime
import json
import time
import urllib.request # Thêm import cho Webhook
import urllib.error   # Thêm import cho Webhook

# --- CẤU HÌNH WEBHOOK TEAMS (Được tham khảo từ sendmsteams.py) ---
WEBHOOK_URL = (
    "https://defaulte1ac1481727f4eabbc6e93a51f4a79.16.environment.api.powerplatform.com:443/"
    "powerautomate/automations/direct/workflows/13f35ec749ac4ffc9e45703c8cdfb325/triggers/manual/paths/invoke"
    "?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=oU1G-QWi8zl9CbCaNKwtkglylwYi1qlTNaDxc2HNfGI"
)
TIMEOUT_SEC = 30 


def as_attachments(card: dict) -> dict:
    """Bao card thành payload dạng message + attachments cho Power Automate."""
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": card,
            }
        ],
    }


def post_json(url: str, payload: dict, timeout: int = TIMEOUT_SEC):
    """Gửi POST JSON bằng urllib.request."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return e.code, body
    except Exception as e:
        return 500, f"Không gọi được webhook: {e}"
# ---------------------------------------------------------------------

# --- CẤU HÌNH TRANG VÀ SESSION STATE ---
st.set_page_config(layout="wide") 

if 'form_key' not in st.session_state:
    st.session_state['form_key'] = 0

try:
    service_account_info = st.secrets["gcp_service_account"]
except KeyError:
    st.error("Lỗi: Không tìm thấy thông tin xác thực Google Service Account. Vui lòng kiểm tra file secrets.toml.")
    st.stop()


def connect_to_gsheet(spreadsheet_name, worksheet_name):
    """Thiết lập kết nối với Google Sheet bằng gspread."""
    try:
        gc = gspread.service_account_from_dict(service_account_info)
        spreadsheet = gc.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet
        
    except SpreadsheetNotFound:
        st.error(f"⚠️ Lỗi: Không tìm thấy Google Sheet có tên '{spreadsheet_name}'. Vui lòng kiểm tra lại tên file.")
        return None
    except WorksheetNotFound:
        st.error(f"⚠️ Lỗi: Không tìm thấy Sheet (tab) có tên '{worksheet_name}' trong file. Vui lòng kiểm tra lại tên tab.")
        return None
    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối Google Sheet: {e}")
        return None


# --- ĐỊNH NGHĨA HÀM load_data (ĐÃ BỎ CACHE) ---
def load_data(sheet_name, worksheet_name):
    ws = connect_to_gsheet(sheet_name, worksheet_name)
    if ws:
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
    return pd.DataFrame()


# Tên Spreadsheet và Worksheet
SPREADSHEET_NAME = "momijicustomer"
WORKSHEET_NAME = "Sheet1"

# --- THIẾT LẬP GIAO DIỆN STREAMLIT ---
st.title("🏡 Hệ Thống Theo Dõi Đặt Hàng Dịch Vụ Sửa Chữa BeniHOME")
st.markdown("---")

# 1. Nhập dữ liệu người đặt hàng dịch vụ
st.header("1. Nhập Thông Tin Đặt Hàng Mới")

with st.form(key=f'order_form_{st.session_state["form_key"]}'):
    
    col1, col2 = st.columns(2)
    
    with col1:
        customer_name = st.text_input("📝 **Tên Khách Hàng**", max_chars=100)
        phone_number = st.text_input("📱 **Số Điện Thoại** (VD: 090xxxxxxx)", max_chars=15)
        service_request = st.selectbox(
            "🛠️ **Yêu Cầu Dịch Vụ**",
            options=[
                "Thay sàn gỗ",
                "Sơn nhà",
                "Sửa chữa nhà (Tổng thể)",
                "Sửa đồ nội thất",
                "Sửa điện nước",
                "Vệ sinh công nghiệp",
                "Khác"
            ]
        )
    with col2:
        address = st.text_area("📍 **Địa Chỉ Cần Sửa Chữa**", max_chars=200, height=200)

    submit_button = st.form_submit_button(label='Lưu Đơn Hàng')

worksheet = None 

if submit_button:
    if not all([customer_name, phone_number, address, service_request]):
        st.error("Vui lòng điền đầy đủ tất cả các trường thông tin.")
    else:
        worksheet = connect_to_gsheet(
            spreadsheet_name=SPREADSHEET_NAME,
            worksheet_name=WORKSHEET_NAME
        )

        if worksheet:
            try:
                existing_data = worksheet.get_all_values()
                next_order_id = len(existing_data)
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                new_order_data = [
                    next_order_id,     
                    timestamp,         
                    customer_name,     
                    phone_number,      
                    address,           
                    service_request,   
                    "Mới"              
                ]

                worksheet.append_row(new_order_data)
                st.success("✅ **Lưu đơn hàng thành công!**")
                st.balloons()
                
                st.session_state['form_key'] += 1
                st.rerun()
                
            except APIError as e:
                st.error(f"⚠️ Lỗi GHI DỮ LIỆU vào Google Sheet (API Error): {e}")
                st.warning("Vui lòng kiểm tra: 1. Quyền **Editor** đã chia sẻ cho Service Account chưa? 2. Tiêu đề các cột trong Sheet có khớp không?")
            except Exception as e:
                st.error(f"⚠️ Lỗi KHÔNG XÁC ĐỊNH khi lưu dữ liệu: {e}")

st.markdown("---")
## 2. Danh Sách Đơn Hàng và Cập Nhật Tình Trạng
st.header("2. Danh Sách Đơn Hàng")

data_load_state = st.text('Đang tải dữ liệu...')
df = load_data(SPREADSHEET_NAME, WORKSHEET_NAME)
data_load_state.text('Đã tải dữ liệu thành công!')

if not df.empty:
    
    # --- 1. Chuẩn bị DataFrame cho st.data_editor và JSON ---
    
    df_edit = df.copy() 
    try:
        df_edit['Số thứ tự'] = pd.to_numeric(df_edit['Số thứ tự'], errors='coerce', downcast='integer')
        df_edit.set_index('Số thứ tự', inplace=True)
    except Exception as e:
        st.warning(f"Không thể đặt 'Số thứ tự' làm chỉ mục: {e}. Vui lòng đảm bảo cột này không có giá trị trống.")

    df_edit.rename(columns={
        'Tên Khách Hàng': 'Tên khách', 
        'Số Điện Thoại': 'Số điện thoại', 
        'Thời Gian': 'Ngày tạo',
        'Địa Chỉ': 'Địa chỉ',
        'Yêu Cầu Dịch Vụ': 'Yêu cầu dịch vụ',
        'Tình trạng': 'Tình trạng'
    }, inplace=True)

    display_columns = [
        'Ngày tạo', 
        'Tên khách', 
        'Số điện thoại', 
        'Địa chỉ', 
        'Yêu cầu dịch vụ',
        'Tình trạng' 
    ]
    df_display = df_edit[[col for col in display_columns if col in df_edit.columns]]

    # --- 2. HÀM TẠO ADAPTIVE CARD JSON ---
    
    def generate_adaptive_card_json(df):
        """
        Nhóm DataFrame theo 'Tình trạng' và tạo Adaptive Card JSON theo cấu trúc mẫu.
        """
        df_json = df.reset_index().rename(columns={
             'Số thứ tự': 'ID',
             'Ngày tạo': 'Thời gian tạo',
             'Tên khách': 'Tên Khách Hàng',
             'Số điện thoại': 'Số Điện Thoại',
             'Địa chỉ': 'Địa Chỉ',
             'Yêu cầu dịch vụ': 'Yêu Cầu Dịch Vụ',
             'Tình trạng': 'Tình trạng'
        })
        
        df_json = df_json[['ID', 'Tên Khách Hàng', 'Yêu Cầu Dịch Vụ', 'Địa Chỉ', 'Số Điện Thoại', 'Thời gian tạo', 'Tình trạng']]

        total_orders = len(df_json)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        adaptive_card_template = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.0",
            "body": [
                # Header
                {
                    "type": "ColumnSet",
                    "columns": [
                        {"type": "Column", "width": 3, "items": [
                            {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": "Đơn hàng BeniHome"},
                            {"type": "TextBlock", "isSubtle": True, "spacing": "None", "text": f"Cập nhật: {current_time}"}
                        ]},
                        {"type": "Column", "width": "auto", "items": [
                            {"type": "Image", "url": "https://benihome.com.vn/wp-content/uploads/2018/08/logo.png", "size": "Medium", "altText": "BeniHome"}
                        ], "horizontalAlignment": "Right"}
                    ]
                },
                # Total
                {"type": "TextBlock", "text": f"Tổng: {total_orders} đơn", "weight": "Bolder", "spacing": "Small"}
            ],
            "actions": [
                {"type": "Action.OpenUrl", "title": "Mở bảng Excel", "url": "https://docs.google.com/spreadsheets/d/1uRtOnKX29zge_KjHmajNppWUGnqB3YStA1nh_J356Jo/edit?gid=0#gid=0"}
            ]
        }

        grouped = df_json.groupby('Tình trạng')
        
        for status, group in grouped:
            order_list_container = {"type": "Container", "items": []}
            
            for index, row in group.iterrows():
                order_string = f"#{row['ID']} • {row['Tên Khách Hàng']} • {row['Yêu Cầu Dịch Vụ']} • {row['Địa Chỉ']} • {row['Số Điện Thoại']} • {row['Thời gian tạo']}"
                
                order_list_container["items"].append({
                    "type": "TextBlock",
                    "text": order_string,
                    "wrap": True,
                    "spacing": "Small"
                })

            status_container = {
                "type": "Container",
                "items": [
                    {"type": "TextBlock", "text": f"{status} ({len(group)})", "weight": "Bolder", "size": "Medium", "spacing": "Medium"},
                    order_list_container
                ]
            }
            
            adaptive_card_template["body"].append(status_container)
            
        return json.dumps(adaptive_card_template, ensure_ascii=False, indent=4)

    # Hàm wrapper để Streamlit gọi khi tạo tệp tải xuống
    def get_adaptive_card_data():
        return generate_adaptive_card_json(df_display)

    # --- 3. HÀM GỬI LÊN TEAMS (Callback cho nút) ---
    def send_to_teams_callback():
        json_string = get_adaptive_card_data()
        
        try:
            card = json.loads(json_string)
            
            # 1. Bao thành attachments
            wrapped = as_attachments(card)

            # 2. Gửi lên webhook
            st.toast("Đang gửi báo cáo Adaptive Card lên MS Teams...")
            status, body = post_json(WEBHOOK_URL, wrapped)
            
            # 3. Xử lý phản hồi
            if status in (200, 202):
                st.success(f"✅ Đã gửi báo cáo đơn hàng thành công lên MS Teams! (Status: {status})")
            else:
                st.error(f"❌ Lỗi khi gửi lên MS Teams (Status: {status}). Vui lòng kiểm tra Flow Power Automate.")
                st.code(f"Phản hồi: {body[:500]}", language='text') # Hiện 500 ký tự đầu của body
                
        except json.JSONDecodeError:
            st.error("Lỗi: Dữ liệu JSON tạo ra không hợp lệ.")
        except Exception as e:
            st.error(f"Lỗi không xác định trong quá trình gửi: {e}")

    # --- 4. CÁC NÚT HÀNH ĐỘNG ---
    col_download, col_send = st.columns([0.25, 0.75])

    with col_download:
        st.download_button(
            label="⬇️ Xuất Dữ Liệu Adaptive Card JSON",
            data=get_adaptive_card_data(), 
            file_name='adaptive_card_don_hang_benihome.json', 
            mime='application/json',
            help="Tải toàn bộ danh sách đơn hàng hiện tại dưới dạng Adaptive Card JSON."
        )

    with col_send:
        # Nút mới: Gửi lên MS Teams
        st.button(
            label="📤 Gửi Báo Cáo lên MS Teams",
            on_click=send_to_teams_callback,
            help="Tạo Adaptive Card JSON mới nhất và gửi đến Power Automate Flow (MS Teams)."
        )
    # -----------------------------

    st.caption("💡 **Nhấn đúp chuột vào cột 'Tình trạng' để thay đổi trạng thái.**")
    
    # --- 5. Hiển thị bảng có thể chỉnh sửa (data_editor) ---
    edited_df = st.data_editor(
        df_display,
        key="data_editor",
        column_config={
            "Tình trạng": st.column_config.SelectboxColumn(
                "Tình trạng",
                help="Cập nhật tình trạng của đơn hàng",
                width="medium",
                options=["Mới", "Đang chăm sóc", "Hoàn thành", "Hủy"],
                required=True,
            ),
        },
        disabled=df_display.columns.difference(['Tình trạng']), 
        width='stretch'
    )
    
    # --- 6. Logic Ghi lại thay đổi vào Google Sheet ---
    
    if st.session_state["data_editor"]["edited_rows"]:
        with st.spinner("🔄 Đang cập nhật trạng thái đơn hàng..."):
            
            worksheet = connect_to_gsheet(SPREADSHEET_NAME, WORKSHEET_NAME)
            if worksheet:
                changes = st.session_state["data_editor"]["edited_rows"]
                
                all_records = worksheet.get_all_values()
                header = all_records[0]
                
                try:
                    status_col_index = header.index("Tình trạng") + 1 
                    id_col_index = header.index("Số thứ tự") + 1
                except ValueError:
                    st.error("Lỗi: Không tìm thấy cột 'Tình trạng' hoặc 'Số thứ tự' trong Google Sheet. Vui lòng kiểm tra tiêu đề cột.")
                    st.stop()
                
                updated_successfully = False
                
                for index, updated_data in changes.items():
                    order_id = index 
                    new_status = updated_data.get("Tình trạng")
                    
                    if new_status:
                        gsheet_row_number = -1
                        for i, row in enumerate(all_records):
                            if str(row[id_col_index - 1]) == str(order_id): 
                                gsheet_row_number = i + 1 
                                break
                        
                        if gsheet_row_number > 1:
                            try:
                                worksheet.update_cell(gsheet_row_number, status_col_index, new_status)
                                updated_successfully = True
                                st.toast(f"✅ Đã cập nhật Đơn hàng ID {order_id} sang trạng thái: {new_status}")
                            except Exception as e:
                                st.error(f"Lỗi khi cập nhật ID {order_id}: {e}")
                        
        if updated_successfully:
            st.session_state["data_editor"]["edited_rows"] = {}
            st.rerun() 

else:
    st.info("Chưa có đơn hàng nào được lưu hoặc không thể kết nối Google Sheet. Vui lòng kiểm tra permissions và tên Sheet.")

st.markdown("---")
st.info("Ứng dụng được lập trình bởi NNT.")
