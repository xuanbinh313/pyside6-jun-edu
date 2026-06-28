from pathlib import Path

import fitz  # PyMuPDF


def extract_images_from_pdf(pdf_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Mở file PDF
    doc = fitz.open(str(pdf_path))
    
    image_count = 0
    
    # Duyệt qua từng trang
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        # Duyệt qua các hình ảnh tìm thấy trong trang
        for img_index, img in enumerate(image_list):
            xref = img[0]  # ID của đối tượng ảnh
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]  # png, jpeg, etc.
            
            # Đặt tên file ảnh đầu ra
            image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
            image_file_path = output_dir / image_filename
            
            # Ghi dữ liệu binary ra file ảnh
            with open(image_file_path, "wb") as f:
                f.write(image_bytes)
                
            image_count += 1
            print(f"Đã trích xuất: {image_filename}")
            
    print(f"=== HOÀN THÀNH: Đã lấy được tổng cộng {image_count} hình ảnh ===")

# Chạy thử
extract_images_from_pdf(Path("de_thi_toeic.pdf"), Path("./extracted_images"))