# =============================================================================
# TruthGuard AI - Phiên bản Thử nghiệm (Single-Agent)
# Công nghệ: Streamlit + Google Gemini (gemini-2.5-pro)
# Chức năng: Kiểm chứng tin giả đa phương thức (văn bản + hình ảnh)
# =============================================================================

import streamlit as st
import google.generativeai as genai
from PIL import Image

# =============================================================================
# BƯỚC 1: CẤU HÌNH TRANG STREAMLIT
# =============================================================================

st.set_page_config(
    page_title="TruthGuard AI",
    page_icon="🛡️",
    layout="wide",
)

# CSS tùy chỉnh giao diện
st.markdown("""
<style>
    /* --- Màu nền tổng thể --- */
    [data-testid="stAppViewContainer"] {
        background-color: #0d0d1a;
    }
    [data-testid="stSidebar"] {
        background-color: #12122b;
        border-right: 1px solid #2a2a5a;
    }

    /* --- Tiêu đề lớn --- */
    .app-title {
        text-align: center;
        font-size: 2.6rem;
        font-weight: 900;
        color: #e94560;
        letter-spacing: -1px;
        padding-bottom: 0.2rem;
    }
    .app-subtitle {
        text-align: center;
        color: #888;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* --- Đường kẻ phân cách --- */
    hr.divider {
        border: none;
        border-top: 1px solid #2a2a5a;
        margin: 1rem 0;
    }

    /* --- Hộp kết quả --- */
    .result-box {
        background-color: #12122b;
        border: 1px solid #2a2a5a;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        color: #e0e0e0;
        line-height: 1.8;
    }

    /* --- Chữ sidebar --- */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #cccccc !important;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# BƯỚC 2: KHỞI TẠO API CLIENT
# Lấy key từ st.secrets để bảo mật — KHÔNG hardcode vào code
# =============================================================================

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error(
        "❌ Không tìm thấy **GEMINI_API_KEY** trong `st.secrets`.\n\n"
        "Tạo file `.streamlit/secrets.toml` và thêm:\n"
        "```toml\nGEMINI_API_KEY = \"your-key-here\"\n```"
    )
    st.stop()


# =============================================================================
# BƯỚC 3: KHỞI TẠO MODEL GEMINI VỚI CÔNG CỤ TÌM KIẾM
# gemini-2.5-pro + google_search_retrieval để tự lên mạng tra cứu
# =============================================================================

model = genai.GenerativeModel(
    model_name="gemini-2.5-pro",   # Model mạnh nhất, hỗ trợ multimodal + search
    tools="google_search",         # ✅ Tên tool mới (google_search_retrieval đã deprecated)
)


# =============================================================================
# BƯỚC 4: SYSTEM PROMPT — Nhúng thẳng vào code
# Định nghĩa vai trò, quy trình và định dạng kết quả của AI
# =============================================================================

SYSTEM_PROMPT = """
Bạn là một Chuyên gia Kiểm chứng Thông tin (Lead Fact-Checker) cấp cao,
làm việc hoàn toàn khách quan, dựa trên logic và bằng chứng thực tế.

**QUY TRÌNH BẮT BUỘC:**

1. **Bóc tách tuyên bố cốt lõi:** Xác định các luận điểm chính cần kiểm chứng
   trong nội dung được cung cấp.
   - Nếu có hình ảnh: mô tả chi tiết nội dung ảnh, tìm dấu hiệu chỉnh sửa,
     cắt ghép hoặc AI tạo ra (Deepfake), và trích xuất toàn bộ văn bản trong ảnh.

2. **Tra cứu bắt buộc:** Sử dụng công cụ Google Search được tích hợp sẵn để
   đối chiếu thông tin. **CHỈ tin tưởng** vào:
   - Báo chí chính thống Việt Nam: VTV, VnExpress, Tuổi Trẻ, Thanh Niên,
     Dân Trí, Nhân Dân, Pháp luật TP.HCM.
   - Cổng thông tin Chính phủ và cơ quan nhà nước (.gov.vn).
   - Tổ chức quốc tế uy tín: WHO, UN, Reuters, AP.

3. **Suy luận logic:** Xâu chuỗi thời gian, số liệu, hình ảnh để tìm mâu
   thuẫn hoặc bóp méo sự thật.

**ĐỊNH DẠNG KẾT QUẢ BẮT BUỘC (Markdown tiếng Việt):**

---

## 🛑 KẾT LUẬN CUỐI CÙNG
> **[Chọn đúng 1 trong 4: SỰ THẬT / TIN GIẢ / TIN XUYÊN TẠC / CHƯA THỂ XÁC MINH]**

---

## 📋 TÓM TẮT SỰ THẬT
*Giải thích bản chất sự việc trong 2–3 câu ngắn gọn, đanh thép.*

---

## 🔍 PHÂN TÍCH CHI TIẾT

### Bằng chứng từ nguồn chính thống
- Trích dẫn / tóm tắt những gì tìm được từ Google Search.
- Giải thích tại sao thông tin này bác bỏ hoặc xác nhận tin đồn.

### Phân tích logic & Hình ảnh *(bỏ qua nếu không có ảnh)*
- Chỉ ra điểm vô lý, cắt ghép, đánh tráo khái niệm hoặc dấu hiệu chỉnh sửa.

---

## 💡 LỜI KHUYÊN
*Một câu khuyên người dùng cảnh giác với dạng tin này.*

---

Bây giờ hãy phân tích nội dung dưới đây:
"""


# =============================================================================
# BƯỚC 5: GIAO DIỆN — SIDEBAR (Khu vực nhập liệu)
# =============================================================================

with st.sidebar:
    st.markdown("## 🛡️ TruthGuard AI")
    st.markdown("**Phiên bản thử nghiệm** · Single-Agent")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown("### 📝 Nội dung cần kiểm chứng")

    # Ô nhập văn bản tin đồn
    user_text = st.text_area(
        label="Dán văn bản tin đồn vào đây:",
        placeholder=(
            "Ví dụ: 'Nghe nói Hà Nội sắp phong tỏa toàn bộ "
            "vì dịch mới bùng phát...'"
        ),
        height=180,
    )

    st.markdown("### 🖼️ Hình ảnh đính kèm *(tuỳ chọn)*")

    # Widget upload ảnh
    uploaded_file = st.file_uploader(
        label="Tải ảnh chụp màn hình / hình ảnh nghi vấn:",
        type=["png", "jpg", "jpeg"],
        help="Hỗ trợ: PNG, JPG, JPEG",
    )

    # Hiển thị preview ảnh nếu người dùng đã upload
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Ảnh đã tải lên", use_column_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Nút bắt đầu kiểm chứng
    verify_button = st.button(
        label="🔍 BẮT ĐẦU KIỂM CHỨNG",
        type="primary",
        use_container_width=True,
    )


# =============================================================================
# BƯỚC 6: GIAO DIỆN — MAIN CONTENT (Khu vực hiển thị kết quả)
# =============================================================================

st.markdown('<div class="app-title">🛡️ TruthGuard AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">'
    "Hệ thống kiểm chứng tin giả đa phương thức · "
    "Powered by Google Gemini + Google Search"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown('<hr class="divider">', unsafe_allow_html=True)


# =============================================================================
# BƯỚC 7: XỬ LÝ KHI NGƯỜI DÙNG NHẤN NÚT KIỂM CHỨNG
# =============================================================================

if verify_button:

    # -------------------------------------------------------------------------
    # Khai báo biến từ đầu để tránh lỗi NameError (scope Python)
    # nếu người dùng chỉ nhập text mà không upload ảnh (hoặc ngược lại)
    # -------------------------------------------------------------------------
    pil_image = None   # Sẽ chứa đối tượng PIL.Image nếu có ảnh

    # --- Kiểm tra: phải có ít nhất một loại đầu vào ---
    if not user_text.strip() and uploaded_file is None:
        st.warning("⚠️ Vui lòng nhập văn bản hoặc tải ảnh lên trước khi kiểm chứng.")
        st.stop()

    # -------------------------------------------------------------------------
    # Xây dựng mảng contents gửi cho Gemini
    # Gemini nhận một list gồm: string, PIL.Image, hoặc hỗn hợp cả hai
    # -------------------------------------------------------------------------
    contents = []

    # Thêm System Prompt vào đầu danh sách
    contents.append(SYSTEM_PROMPT)

    # Nếu người dùng nhập văn bản → đưa vào contents
    if user_text.strip():
        contents.append(
            f"**Văn bản tin đồn cần kiểm chứng:**\n\n{user_text.strip()}"
        )

    # Nếu người dùng upload ảnh → mở bằng PIL rồi đưa vào contents
    if uploaded_file is not None:
        pil_image = Image.open(uploaded_file)
        contents.append("\n**Hình ảnh đính kèm cần phân tích:**")
        contents.append(pil_image)   # Gemini SDK nhận trực tiếp PIL.Image

    # -------------------------------------------------------------------------
    # Gọi Gemini API — toàn bộ text + ảnh + prompt xử lý trong 1 lượt
    # -------------------------------------------------------------------------
    with st.spinner("🔄 Đang phân tích và tra cứu thông tin trên mạng... Vui lòng chờ."):
        try:
            response = model.generate_content(contents)
            result_text = response.text

        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi khi gọi Gemini API:\n\n`{e}`")
            st.stop()

    # --- Hiển thị kết quả ra màn hình ---
    st.success("✅ Phân tích hoàn tất!")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown("## 📄 Báo cáo Kiểm chứng")

    # Render Markdown từ Gemini (dùng st.markdown để hiển thị đúng định dạng)
    st.markdown(result_text)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Nút tải báo cáo về máy dạng .txt
    st.download_button(
        label="⬇️ Tải báo cáo (.txt)",
        data=result_text.encode("utf-8"),
        file_name="truthguard_report.txt",
        mime="text/plain",
    )

else:
    # -------------------------------------------------------------------------
    # Màn hình chào khi chưa có hành động nào từ người dùng
    # -------------------------------------------------------------------------
    st.markdown("""
    <div style="text-align:center; padding: 5rem 2rem; color: #555;">
        <div style="font-size: 5rem;">🔎</div>
        <h3 style="color: #666; font-weight: 400; margin-top: 1.2rem;">
            Nhập nội dung vào <strong style="color:#e94560;">Sidebar</strong> và nhấn<br>
            <strong style="color: #e94560;">BẮT ĐẦU KIỂM CHỨNG</strong> để phân tích.
        </h3>
        <p style="color: #444; font-size: 0.9rem; margin-top: 1rem;">
            Hỗ trợ: Văn bản tin đồn · Hình ảnh chụp màn hình · Bài viết mạng xã hội
        </p>
    </div>
    """, unsafe_allow_html=True)
