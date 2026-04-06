import streamlit as st
from google import genai
from google.genai import types

# 1. CẤU HÌNH GIAO DIỆN WEB CƠ BẢN
st.set_page_config(page_title="App Cảnh Báo Tin Giả", page_icon="🕵️‍♂️")
st.title("🕵️‍♂️ Hệ Thống Kiểm Chứng Tin Giả")
st.write("Dự án vòng 3 - Nhập nội dung nghi ngờ để AI tra cứu đối chiếu ngay!")

# 2. KHỞI TẠO AI
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# 3. Ô NHẬP LIỆU CHO NGƯỜI DÙNG
tin_tuc_nghi_ngo = st.text_area("Dán nội dung tin tức hoặc bài báo vào đây:", height=150)

# 4. XỬ LÝ KHI BẤM NÚT
if st.button("🔍 Kiểm chứng ngay"):
    if tin_tuc_nghi_ngo.strip() == "":
        st.warning("Vui lòng nhập nội dung cần kiểm tra!")
    else:
        # Hiển thị vòng xoay chờ đợi cho chuyên nghiệp
        with st.spinner("AI đang tra cứu dữ liệu web và phân tích... Vui lòng đợi..."):
            prompt = f"""
            Bạn là một chuyên gia kiểm chứng sự thật (Fact-checker).
            Hãy sử dụng công cụ Google Tìm kiếm để đối chiếu thông tin và phân tích đoạn tin tức sau. 
            Trình bày kết quả theo định dạng:
            1. ĐÁNH GIÁ: (Tin thật / Tin giả / Gây hiểu lầm)
            2. SỰ THẬT TỪ BÁO CHÍ: (Trích dẫn ngắn gọn thông tin)
            3. KẾT LUẬN & LỜI KHUYÊN: Người dùng nên làm gì?

            Nội dung tin đồn: "{tin_tuc_nghi_ngo}"
            """
            
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}]
                    )
                )
                st.success("Hoàn thành kiểm chứng!")
                # In kết quả ra màn hình web
                st.markdown(response.text) 
                
            except Exception as e:
                st.error(f"Có lỗi xảy ra: {e}")
