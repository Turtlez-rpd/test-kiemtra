# =============================================================================
# TruthGuard AI - Phiên bản Thử nghiệm (Single-Agent)
# Công nghệ: Streamlit + Google Gemini (gemini-2.5-pro)
# SDK: google-genai (MỚI) — thay thế google-generativeai (cũ, deprecated)
# Chức năng: Kiểm chứng tin giả đa phương thức (văn bản + hình ảnh)
# =============================================================================

import streamlit as st
import base64
import io

# Thư viện crawl nội dung từ URL
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

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

    /* --- Thanh tiến trình từng bước --- */
    .progress-wrapper {
        background: #12122b;
        border: 1px solid #2a2a5a;
        border-radius: 14px;
        padding: 1.4rem 1.8rem;
        margin: 1rem 0 1.5rem 0;
    }
    .progress-title {
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #555;
        text-transform: uppercase;
        margin-bottom: 1.1rem;
    }
    .progress-rail {
        background: #1e1e3a;
        border-radius: 99px;
        height: 6px;
        margin-bottom: 1.4rem;
        overflow: hidden;
    }
    .progress-fill {
        height: 6px;
        border-radius: 99px;
        background: linear-gradient(90deg, #e94560, #f5a623);
        transition: width 0.5s ease;
    }
    .steps-list { list-style: none; padding: 0; margin: 0; }
    .step-item {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        padding: 0.45rem 0;
        font-size: 0.92rem;
        color: #444;
    }
    .step-item.done   { color: #00b894; }
    .step-item.active { color: #f5a623; font-weight: 600; }
    .step-item.pending { color: #333; }
    .step-icon {
        width: 26px; height: 26px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.75rem;
        flex-shrink: 0;
        font-weight: 700;
    }
    .icon-done    { background: #00b894; color: #fff; }
    .icon-active  {
        background: #f5a623; color: #fff;
        animation: pulse 1.2s ease-in-out infinite;
    }
    .icon-pending { background: #1e1e3a; color: #333; border: 1px solid #2a2a5a; }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 6px #f5a62355; }
        50%       { box-shadow: 0 0 16px #f5a623cc; }
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HELPER: RENDER THANH TIẾN TRÌNH TỪNG BƯỚC
# =============================================================================

def render_steps(placeholder, steps: list, current: int):
    """
    Vẽ thanh tiến trình + danh sách bước có icon trạng thái.

    Args:
        placeholder : st.empty() — vùng HTML được ghi đè mỗi lần gọi
        steps       : list[str]  — tên các bước theo thứ tự
        current     : int        — index bước ĐANG chạy (0-based)
                                   len(steps) = tất cả đã hoàn tất
    """
    total = len(steps)
    pct   = int(current / total * 100)

    rows = ""
    for i, label in enumerate(steps):
        if i < current:
            state, icon_cls, icon_html = "done",    "icon-done",    "✓"
        elif i == current:
            state, icon_cls, icon_html = "active",  "icon-active",  "●"
        else:
            state, icon_cls, icon_html = "pending", "icon-pending", str(i + 1)

        rows += (
            f'<li class="step-item {state}">'
            f'<span class="step-icon {icon_cls}">{icon_html}</span>'
            f'{label}</li>'
        )

    html = (
        f'<div class="progress-wrapper">'
        f'<div class="progress-title">⚙️ Tiến trình phân tích — {pct}%</div>'
        f'<div class="progress-rail">'
        f'<div class="progress-fill" style="width:{pct}%"></div>'
        f'</div>'
        f'<ul class="steps-list">{rows}</ul>'
        f'</div>'
    )
    placeholder.markdown(html, unsafe_allow_html=True)



# =============================================================================
# HELPER: PHÁT HIỆN MẠNG XÃ HỘI
# =============================================================================

# Danh sách domain mạng xã hội chặn crawl trực tiếp
SOCIAL_DOMAINS = {
    "facebook.com", "fb.com", "fb.watch",
    "instagram.com",
    "twitter.com", "x.com", "t.co",
    "tiktok.com", "vt.tiktok.com",
    "youtube.com", "youtu.be",
    "zalo.me",
    "threads.net",
    "linkedin.com",
    "reddit.com",
}

def is_social_media(url: str) -> tuple[bool, str]:
    """
    Kiểm tra URL có phải mạng xã hội không.
    Trả về (True, tên_mạng) hoặc (False, "").
    """
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        for domain in SOCIAL_DOMAINS:
            if host == domain or host.endswith("." + domain):
                # Tên hiển thị đẹp
                name_map = {
                    "facebook.com": "Facebook", "fb.com": "Facebook", "fb.watch": "Facebook",
                    "instagram.com": "Instagram",
                    "twitter.com": "Twitter/X", "x.com": "Twitter/X", "t.co": "Twitter/X",
                    "tiktok.com": "TikTok", "vt.tiktok.com": "TikTok",
                    "youtube.com": "YouTube", "youtu.be": "YouTube",
                    "zalo.me": "Zalo",
                    "threads.net": "Threads",
                    "linkedin.com": "LinkedIn",
                    "reddit.com": "Reddit",
                }
                return True, name_map.get(domain, domain)
    except Exception:
        pass
    return False, ""


# =============================================================================
# HELPER: CRAWL NỘI DUNG TỪ URL (Báo / Web thông thường)
# =============================================================================

def fetch_url_content(url: str) -> dict:
    """
    Xử lý URL theo 2 hướng:

    - Nếu là mạng xã hội (Facebook, TikTok, ...):
        Không crawl (bị chặn), trả về mode='social' để
        code bên ngoài chuyển URL thẳng cho Gemini tự tìm.

    - Nếu là báo / web thông thường:
        Crawl HTML, bóc nội dung, trả về mode='crawled'.

    Trả về dict:
        'mode'    : 'social' | 'crawled' | 'error'
        'platform': tên mạng xã hội (nếu mode='social')
        'title'   : tiêu đề trang   (nếu mode='crawled')
        'content' : nội dung text   (nếu mode='crawled')
        'error'   : mô tả lỗi       (nếu mode='error')
    """
    # --- Kiểm tra URL hợp lệ ---
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"mode": "error", "error": "URL không hợp lệ. Phải bắt đầu bằng http:// hoặc https://"}

    # --- Nếu là mạng xã hội → trả về ngay, không crawl ---
    social, platform = is_social_media(url)
    if social:
        return {"mode": "social", "platform": platform}

    # --- Crawl trang web thông thường ---
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return {"mode": "error", "error": "Hết thời gian chờ (timeout 15s). Trang phản hồi quá chậm."}
    except requests.exceptions.ConnectionError:
        return {"mode": "error", "error": "Không thể kết nối. Kiểm tra lại đường link."}
    except requests.exceptions.HTTPError as e:
        return {"mode": "error", "error": f"Lỗi HTTP {resp.status_code}: {e}"}
    except Exception as e:
        return {"mode": "error", "error": str(e)}

    # Parse HTML
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title else "Không có tiêu đề"

    # Xoá thẻ không liên quan
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "iframe", "noscript"]):
        tag.decompose()

    # Ưu tiên <article> / <main> (chứa nội dung bài báo)
    article = soup.find("article") or soup.find("main") or soup.find("body")
    raw_text = article.get_text(separator="\n") if article else soup.get_text(separator="\n")

    lines   = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    content = "\n".join(lines)[:6000]

    return {"mode": "crawled", "title": title, "content": content}


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

    st.markdown("### 🔗 Link bài báo / trang web *(tuỳ chọn)*")
    input_url = st.text_input(
        label="Dán URL cần kiểm chứng vào đây:",
        placeholder="https://example.com/bai-viet-nao-do",
        help="Hỗ trợ mọi trang báo, mạng xã hội có nội dung công khai",
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
    image_part   = None
    url_content  = ""   # Nội dung crawl được từ URL

    # Kiểm tra phải có ít nhất 1 trong 3 loại đầu vào
    if not user_text.strip() and not input_url.strip() and uploaded_file is None:
        st.warning("⚠️ Vui lòng nhập văn bản, dán link hoặc tải ảnh lên trước khi kiểm chứng.")
        st.stop()

    # -------------------------------------------------------------------------
    # XỬ LÝ URL: Phân loại và xử lý thông minh
    # -------------------------------------------------------------------------
    if input_url.strip():
        with st.spinner("🔗 Đang xử lý URL..."):
            result = fetch_url_content(input_url.strip())

        if result["mode"] == "error":
            st.error(f"❌ Không thể xử lý URL: {result['error']}")
            st.stop()

        elif result["mode"] == "social":
            # Mạng xã hội: không crawl được, chuyển URL thẳng cho Gemini
            # Gemini sẽ dùng Google Search để tự tìm nội dung bài đăng đó
            platform = result["platform"]
            url_content = (
                f"=== LINK MẠNG XÃ HỘI CẦN KIỂM CHỨNG ===\n"
                f"Nền tảng: {platform}\n"
                f"URL: {input_url.strip()}\n\n"
                f"Lưu ý: Đây là link {platform}. Hãy dùng Google Search để tìm kiếm "
                f"nội dung liên quan đến bài đăng này, xác minh thông tin được chia sẻ "
                f"trong link trên và đối chiếu với các nguồn báo chí chính thống."
            )
            st.info(f"📱 Đã nhận link **{platform}** — Gemini sẽ dùng Google Search để tra cứu nội dung.")

        elif result["mode"] == "crawled":
            # Trang báo / web thông thường: dùng nội dung crawl được
            url_content = (
                f"=== NỘI DUNG TỪ URL: {input_url.strip()} ===\n"
                f"Tiêu đề trang: {result['title']}\n\n"
                f"{result['content']}"
            )
            st.info(f"✅ Đã tải xong: **{result['title']}** ({len(result['content'])} ký tự)")

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

    # Part 3: Nội dung crawl từ URL (nếu có)
    if url_content:
        parts.append(types.Part(text=f"**Nội dung bài báo / trang web cần kiểm chứng:**\n\n{url_content}"))

    # Part 4: Hình ảnh (nếu có)
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
    # Định nghĩa các bước tiến trình — thích ứng theo đầu vào người dùng
    # -------------------------------------------------------------------------
    STEPS = [
        "🗂️  Chuẩn bị & đóng gói dữ liệu đầu vào",
        "🔗  Crawl & trích xuất nội dung từ URL",
        "🖼️  Phân tích hình ảnh (nhận diện Deepfake / OCR)",
        "🌐  Tra cứu Google — đối chiếu nguồn chính thống",
        "🧠  AI tổng hợp bằng chứng & soạn báo cáo",
        "✅  Hoàn tất — xuất kết quả",
    ]

    # Tạo placeholder để cập nhật UI tại chỗ (không bị đẩy xuống)
    progress_placeholder = st.empty()

    # ---- Bước 0: Chuẩn bị xong -----------------------------------------------
    render_steps(progress_placeholder, STEPS, current=0)

    # ---- Bước 1: URL — đã crawl xong ở trên, chỉ cần cập nhật UI ------------
    if input_url.strip():
        render_steps(progress_placeholder, STEPS, current=1)

    # ---- Bước 2: Phân tích ảnh -----------------------------------------------
    if uploaded_file is not None:
        render_steps(progress_placeholder, STEPS, current=2)

    # ---- Bước 3: Gọi Gemini API (tra cứu Google + suy luận — lâu nhất) ------
    render_steps(progress_placeholder, STEPS, current=3)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=parts,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],   # ✅ Truyền tool đúng cách
                temperature=0.1,              # Thấp để kết quả ổn định
            ),
        )
        result_text = response.text

    except Exception as e:
        # Xoá progress UI khi lỗi để không gây nhầm lẫn
        progress_placeholder.empty()
        st.error(f"❌ Đã xảy ra lỗi khi gọi Gemini API:\n\n`{e}`")
        st.stop()

    # ---- Bước 4: Tổng hợp (API đã trả về, đang render) ----------------------
    render_steps(progress_placeholder, STEPS, current=4)

    # ---- Bước 5: Hoàn tất — điền 100% rồi xoá thanh tiến trình -------------
    render_steps(progress_placeholder, STEPS, current=len(STEPS))
    progress_placeholder.empty()   # Dọn dẹp UI, nhường chỗ cho kết quả

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
            Hỗ trợ: Văn bản tin đồn · Link bài báo / trang web · Hình ảnh chụp màn hình
        </p>
    </div>
    """, unsafe_allow_html=True)
