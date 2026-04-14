# =============================================================================
# TruthGuard AI - Phiên bản Thử nghiệm (Single-Agent)
# Công nghệ: Streamlit + Google Gemini (gemini-2.5-pro)
# SDK: google-genai (MỚI) — thay thế google-generativeai (cũ, deprecated)
# Chức năng: Kiểm chứng tin giả đa phương thức (văn bản + hình ảnh)
# =============================================================================

import streamlit as st
import base64
import io

# ✅ Dùng SDK MỚI: "google-genai" thay vì "google-generativeai"
# Cài đặt: pip install google-genai
from google import genai
from google.genai import types
from PIL import Image

# =============================================================================
# BƯỚC 1: CẤU HÌNH TRANG STREAMLIT
# =============================================================================

st.set_page_config(
    page_title="TruthGuard AI",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0d0d1a; }
    [data-testid="stSidebar"] {
        background-color: #12122b;
        border-right: 1px solid #2a2a5a;
    }
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
    hr.divider {
        border: none;
        border-top: 1px solid #2a2a5a;
        margin: 1rem 0;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: #cccccc !important; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# BƯỚC 2: KHỞI TẠO CLIENT (SDK MỚI)
# Dùng genai.Client() thay vì genai.configure() của SDK cũ
# =============================================================================

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error(
        "❌ Không tìm thấy **GEMINI_API_KEY** trong `st.secrets`.\n\n"
        "Tạo file `.streamlit/secrets.toml` và thêm:\n"
        "```toml\nGEMINI_API_KEY = \"your-key-here\"\n```"
    )
    st.stop()


# =============================================================================
# BƯỚC 3: CẤU HÌNH MODEL + TOOL
# SDK mới dùng types.Tool(google_search=types.GoogleSearch())
# =============================================================================

MODEL_NAME = "gemini-2.5-pro"

# ✅ Cách khai báo Google Search đúng với SDK google-genai
google_search_tool = types.Tool(google_search=types.GoogleSearch())


# =============================================================================
# BƯỚC 4: SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """Bạn là một Chuyên gia Kiểm chứng Thông tin (Lead Fact-Checker) cấp cao,
làm việc hoàn toàn khách quan, dựa trên logic và bằng chứng thực tế.

**QUY TRÌNH BẮT BUỘC:**

1. **Bóc tách tuyên bố cốt lõi:** Xác định các luận điểm chính cần kiểm chứng
   trong nội dung được cung cấp.
   - Nếu có hình ảnh: mô tả chi tiết nội dung ảnh, tìm dấu hiệu chỉnh sửa,
     cắt ghép hoặc AI tạo ra (Deepfake), và trích xuất toàn bộ văn bản trong ảnh.

2. **Tra cứu bắt buộc:** Sử dụng công cụ Google Search được tích hợp sẵn để
   đối chiếu thông tin. CHỈ tin tưởng vào:
   - Báo chí chính thống Việt Nam: VTV, VnExpress, Tuổi Trẻ, Thanh Niên,
     Dân Trí, Nhân Dân, Pháp luật TP.HCM.
   - Cổng thông tin Chính phủ (.gov.vn).
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

Bây giờ hãy phân tích nội dung dưới đây:"""


# =============================================================================
# BƯỚC 5: SIDEBAR — Khu vực nhập liệu
# =============================================================================

with st.sidebar:
    st.markdown("## 🛡️ TruthGuard AI")
    st.markdown("**Phiên bản thử nghiệm** · Single-Agent")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown("### 📝 Nội dung cần kiểm chứng")
    user_text = st.text_area(
        label="Dán văn bản tin đồn vào đây:",
        placeholder="Ví dụ: 'Nghe nói Hà Nội sắp phong tỏa toàn bộ vì dịch mới...'",
        height=180,
    )

    st.markdown("### 🖼️ Hình ảnh đính kèm *(tuỳ chọn)*")
    uploaded_file = st.file_uploader(
        label="Tải ảnh chụp màn hình / hình ảnh nghi vấn:",
        type=["png", "jpg", "jpeg"],
        help="Hỗ trợ: PNG, JPG, JPEG",
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Ảnh đã tải lên", use_column_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    verify_button = st.button(
        label="🔍 BẮT ĐẦU KIỂM CHỨNG",
        type="primary",
        use_container_width=True,
    )


# =============================================================================
# BƯỚC 6: MAIN CONTENT — Tiêu đề
# =============================================================================

st.markdown('<div class="app-title">🛡️ TruthGuard AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">'
    "Hệ thống kiểm chứng tin giả đa phương thức · "
    "Powered by Google Gemini 2.5 Pro + Google Search"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown('<hr class="divider">', unsafe_allow_html=True)


# =============================================================================
# BƯỚC 7: XỬ LÝ KHI NHẤN NÚT
# =============================================================================

if verify_button:

    # Khai báo trước để tránh lỗi NameError
    image_part = None

    # Kiểm tra phải có ít nhất 1 đầu vào
    if not user_text.strip() and uploaded_file is None:
        st.warning("⚠️ Vui lòng nhập văn bản hoặc tải ảnh lên trước khi kiểm chứng.")
        st.stop()

    # -------------------------------------------------------------------------
    # Xây dựng danh sách parts gửi cho Gemini
    # SDK mới dùng types.Part để đóng gói từng loại nội dung
    # -------------------------------------------------------------------------
    parts = []

    # Part 1: System Prompt
    parts.append(types.Part(text=SYSTEM_PROMPT))

    # Part 2: Văn bản người dùng nhập (nếu có)
    if user_text.strip():
        parts.append(
            types.Part(text=f"**Văn bản tin đồn cần kiểm chứng:**\n\n{user_text.strip()}")
        )

    # Part 3: Hình ảnh (nếu có) — encode sang bytes rồi bọc vào types.Part
    if uploaded_file is not None:
        # Đọc bytes từ file upload
        image_bytes = uploaded_file.read()

        # Xác định MIME type từ tên file
        file_name = uploaded_file.name.lower()
        if file_name.endswith(".png"):
            mime_type = "image/png"
        elif file_name.endswith(".jpg") or file_name.endswith(".jpeg"):
            mime_type = "image/jpeg"
        else:
            mime_type = "image/png"  # Mặc định

        parts.append(types.Part(text="\n**Hình ảnh đính kèm cần phân tích:**"))

        # ✅ SDK mới: dùng types.Part.from_bytes() để gửi ảnh
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        parts.append(image_part)

    # -------------------------------------------------------------------------
    # Gọi Gemini API với SDK mới
    # client.models.generate_content() thay vì model.generate_content()
    # -------------------------------------------------------------------------
    with st.spinner("🔄 Đang phân tích và tra cứu thông tin trên mạng... Vui lòng chờ."):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=parts,
                config=types.GenerateContentConfig(
                    tools=[google_search_tool],   # ✅ Truyền tool đúng cách
                    temperature=0.1,              # Thấp để kết quả ổn định, ít sáng tạo
                ),
            )
            result_text = response.text

        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi khi gọi Gemini API:\n\n`{e}`")
            st.stop()

    # --- Hiển thị kết quả ---
    st.success("✅ Phân tích hoàn tất!")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("## 📄 Báo cáo Kiểm chứng")
    st.markdown(result_text)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.download_button(
        label="⬇️ Tải báo cáo (.txt)",
        data=result_text.encode("utf-8"),
        file_name="truthguard_report.txt",
        mime="text/plain",
    )

else:
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
