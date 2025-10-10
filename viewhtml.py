import streamlit as st
import streamlit.components.v1 as components
import base64
import io
import math
import textwrap
from PIL import Image, ImageDraw, ImageFont

# ID của DIV chứa nội dung HTML Preview
PREVIEW_ELEMENT_ID = "html-content-wrapper" 

# --- 1. Hàm JavaScript: In nội dung trong Cửa sổ Mới (Không thay đổi) ---
JS_PRINT_FUNCTION = """
<script>
    function printPreview() {
        // 1. Lấy nội dung HTML cần in (đã bọc trong div có ID)
        var previewElement = document.getElementById('html-content-wrapper');
        if (!previewElement) {
            alert('Lỗi: Không tìm thấy nội dung HTML để in.');
            return;
        }
        
        var htmlToPrint = previewElement.innerHTML;
        
        // 2. Mở một cửa sổ/tab mới
        var printWindow = window.open('', '', 'height=600,width=800');
        
        // Lấy lại các thẻ style từ head của trang chính (nếu có)
        var fullHTML = '<html><head><title>Print</title>' + 
                       document.head.innerHTML + 
                       '</head><body>' + htmlToPrint + '</body></html>';
                       
        printWindow.document.write(fullHTML);
        
        // 3. Xóa nút bấm khỏi cửa sổ in để nó không xuất hiện trong PDF
        var printButtonContainer = printWindow.document.getElementById('print-button-container');
        if (printButtonContainer) {
            printButtonContainer.remove();
        }
        
        // 4. Kích hoạt lệnh in
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
    }
</script>
"""

# ---------- HÀM XỬ LÝ ẢNH GHÉP (TỪ CODE CỦA BẠN) ----------

def measure_text(draw, text, font):
    """Đo kích thước văn bản (Hỗ trợ PIL 9+ và cũ hơn)."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return w, h
    except Exception:
        # Fallback cho các phiên bản PIL cũ hơn
        try:
            return font.getsize(text)
        except Exception:
            return (len(text) * 6, 12)

def make_grid_with_captions(cells, cols=4, size=(300, 300), caption_height=70, bg_color=(255,255,255)):
    """Tạo ảnh lưới từ danh sách các cells (chứa file_bytes và caption)."""
    total = len(cells)
    if total == 0:
        return None

    rows = math.ceil(total / cols)
    w = cols * size[0]
    h = rows * (size[1] + caption_height)
    grid = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(grid)

    # Font hỗ trợ tiếng Việt (cần phải có trên hệ thống hoặc môi trường)
    font = None
    for fname in ("NotoSans-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(fname, 18)
            break
        except Exception:
            font = None
    if font is None:
        font = ImageFont.load_default()

    for i, cell in enumerate(cells):
        r, c = divmod(i, cols)
        x = c * size[0]
        y = r * (size[1] + caption_height)

        fb = cell.get("file_bytes")
        desc = (cell.get("caption") or "").strip()

        # Dán ảnh
        if fb:
            try:
                img = Image.open(io.BytesIO(fb)).convert("RGB")
                img = img.resize(size)
                grid.paste(img, (x, y))
            except Exception:
                # Bỏ qua ảnh lỗi
                pass

        # Ghi mô tả
        if desc:
            lines = textwrap.wrap(desc, width=25)
            lines = lines[:2] # Giới hạn 2 dòng
            for li, line in enumerate(lines):
                tw, th = measure_text(draw, line, font)
                tx = x + (size[0] - tw) // 2 # Canh giữa
                ty = y + size[1] + li * (th + 4) + 6
                draw.text((tx, ty), line, fill=(0, 0, 0), font=font)

    return grid


# --- 2. Các hàm xử lý Session State ---

def update_preview():
    """Đặt cờ để kích hoạt render lại phần Preview."""
    st.session_state['show_preview'] = True

def handle_grid_generation():
    """Xử lý tạo ảnh ghép, chuyển thành Base64 và cập nhật HTML."""
    cells = st.session_state.get('current_cells_data', [])
    # Lấy giá trị cột trực tiếp từ Session State, nơi nó được cập nhật tự động
    cols = st.session_state.get('cols_input', 4) 
    
    if not cells:
        st.warning("Vui lòng tải lên ảnh và nhập mô tả để tạo ảnh ghép.")
        st.session_state['base64_image_html'] = ""
        return

    try:
        # 1. Tạo ảnh ghép (Grid Image)
        grid_img = make_grid_with_captions(
            cells,
            cols=cols,
            size=(300, 300),
            caption_height=70
        )
        
        if grid_img is None:
            st.error("Không thể tạo ảnh ghép.")
            return

        # 2. Chuyển ảnh ghép thành Base64 (định dạng PNG)
        buf = io.BytesIO()
        grid_img.save(buf, format="PNG")
        bytes_data = buf.getvalue()

        base64_encoded_data = base64.b64encode(bytes_data).decode('utf-8')
        mime_type = "image/png"
        
        # 3. Tạo thẻ <img> sử dụng Base64 Data URI
        image_html = f"""
        <div style="margin-top: 30px; padding-top: 15px; border-top: 3px solid #8E44AD; padding: 20px; border-radius: 8px;">
            <h3 style="color: #8E44AD;">Ảnh Ghép Lưới Đã Tạo:</h3>
            <p>Tổng số ảnh: {len(cells)}. Bố cục: {cols} cột.</p>
            <img src="data:{mime_type};base64,{base64_encoded_data}" alt="Generated Image Grid" 
                 style="max-width: 100%; height: auto; display: block; margin: 15px 0; border: 1px solid #D7DBDD; border-radius: 4px;">
        </div>
        """
        
        # 4. Cập nhật Session State
        st.session_state['base64_image_html'] = image_html
        st.session_state['show_preview'] = True
        st.success(f"🖼️ Ảnh ghép ({len(cells)} ảnh) đã được tạo và nhúng thành công. Nhấn 'Hiển thị HTML Preview' để xem.")

    except Exception as e:
        st.error(f"Lỗi khi xử lý tạo ảnh ghép: {e}")


# --- 3. Hàm Chính của Ứng dụng Streamlit ---
def main():
    st.set_page_config(layout="wide", page_title="HTML Preview & PDF Export")

    st.title("HTML Report Generator & PDF Exporter (Grid Image)")
    
    # --- Khởi tạo Session State An toàn ---
    
    default_html = ()
    
    
    # Sử dụng setdefault để đảm bảo các khóa luôn tồn tại, tránh KeyError
    st.session_state.setdefault('html_code', default_html)
    st.session_state.setdefault('base64_image_html', "") # Lưu chuỗi HTML chứa ảnh Base64
    st.session_state.setdefault('show_preview', True)
    st.session_state.setdefault('current_cells_data', []) # Lưu dữ liệu ảnh và caption
    st.session_state.setdefault('cols_input', 4) # Đã fix: Khóa này giờ luôn được khởi tạo.

    # --- Định nghĩa Layout 2 cột ---
    col_input, col_preview = st.columns([1, 1])
    
    # --- Cột 1: Nhập Mã HTML, Tải Ảnh, Nút Kích hoạt ---
    with col_input:
        st.subheader("1. Dán Mã HTML (Nội dung Báo Cáo)")
        
        # Text area liên kết trực tiếp với Session State
        st.session_state['html_code'] = st.text_area(
            "Chỉnh sửa nội dung HTML ở đây:", 
            st.session_state['html_code'], 
            height=250,
            key="input_html_area"
        )
        
        # Nút Kích hoạt Hiển thị Preview
        st.button(
            "▶ Hiển thị HTML Preview", 
            on_click=update_preview, 
            type="primary"
        )
        
        st.markdown("---")
        st.subheader("2. Tải lên Ảnh và Nhập Mô tả")
        
        # Uploader cho nhiều file
        uploaded_files = st.file_uploader(
            "Chọn nhiều ảnh (PNG/JPG):",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="grid_uploaded_files"
        )
        
        cells = []
        if uploaded_files:
            # Nhập số cột
            # Đã fix: 'cols_input' đã được đảm bảo tồn tại, nên việc truy cập là an toàn.
            cols_input = st.number_input(
                "Số cột trong lưới", 
                min_value=1, 
                max_value=10, 
                value=st.session_state['cols_input'], 
                key="cols_input"
            )

            st.markdown("### ✍️ Nhập mô tả cho từng ảnh")
            for i, file in enumerate(uploaded_files):
                fb = file.getvalue()
                col1_img, col2_cap = st.columns([1, 5])
                with col1_img:
                    try:
                        # Preview nhỏ 100x100
                        img_preview = Image.open(io.BytesIO(fb)).convert("RGB")
                        img_preview = img_preview.resize((100, 100))
                        st.image(img_preview)
                    except Exception:
                        st.write("❌ Không xem được")
                with col2_cap:
                    caption = st.text_input(f"Mô tả cho ảnh {i+1} ({file.name})", key=f"grid_cap_{i}")
                cells.append({"file_bytes": fb, "caption": caption})
            
            # Lưu dữ liệu cells vào Session State để hàm callback truy cập
            st.session_state['current_cells_data'] = cells
        else:
             st.session_state['current_cells_data'] = []
             st.session_state['base64_image_html'] = "" # Xóa ảnh cũ khi không có ảnh mới

        # Nút Cập nhật Hình ảnh (kích hoạt tạo ảnh ghép)
        st.button(
            "🖼️ Tải lên & Tạo Ảnh Ghép", 
            on_click=handle_grid_generation
        )
    
    # --- Cột 2: HTML Preview & Nút Xuất PDF ---
    with col_preview:
        st.subheader("3. HTML Preview & Xuất PDF")

        # Gộp HTML của người dùng và HTML hình ảnh Base64 đã tạo
        final_html_content = st.session_state["html_code"] + st.session_state["base64_image_html"]
        
        # 4. Tạo Nút Xuất PDF trong cùng khối HTML
        pdf_button_html = f"""
        <div id="print-button-container" style="width: 100%; margin-top: 20px;">
            <button onclick="printPreview()" 
                    style="background-color: #D35400; color: white; border: none; 
                           padding: 12px 24px; text-align: center; text-decoration: none; 
                           display: inline-block; font-size: 18px; margin: 4px 0; 
                           cursor: pointer; border-radius: 8px; width: 100%;">
                ⬇ Xuất File PDF Chính Xác (Cửa Sổ Mới)
            </button>
            <p style="font-size: 12px; color: gray;">⚠️ Cửa sổ mới sẽ mở ra. Chọn **'Lưu dưới dạng PDF'** trong hộp thoại In trên cửa sổ đó.</p>
        </div>
        """

        # 5. Gộp HTML code của người dùng, Script và Nút bấm vào một khối duy nhất
        if st.session_state.get('show_preview', False):
            
            # Wrapper ID giúp JS tìm thấy toàn bộ nội dung cần copy
            full_html_to_embed = f"""
            {JS_PRINT_FUNCTION}
            <div id="{PREVIEW_ELEMENT_ID}" style="height: 400px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; background-color: white;">
                {final_html_content}
            </div>
            {pdf_button_html}
            """
            
            # Nhúng toàn bộ khối này vào Streamlit
            components.html(full_html_to_embed, height=550, scrolling=False)
        else:
            st.info("Nhấn nút **'Hiển thị HTML Preview'** ở cột bên trái để xem kết quả.")


if __name__ == "__main__":
    main()




