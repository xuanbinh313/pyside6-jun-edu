import cv2
import numpy as np
from pathlib import Path

def process_and_split_png_folder(input_folder_path: str, output_folder_path: str):
    input_dir = Path(input_folder_path)
    output_dir = Path(output_folder_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Chấp nhận cả đuôi .png, .PNG, .jpg, .JPG
    extensions = ["*.png", "*.PNG", "*.jpg", "*.JPG", "*.jpeg"]
    png_files = []
    for ext in extensions:
        png_files.extend(input_dir.glob(ext))
    
    if not png_files:
        print("❌ Không tìm thấy file ảnh nào trong thư mục đầu vào!")
        return
        
    print(f"🔍 Tìm thấy {len(png_files)} file ảnh. Bắt đầu quét...")
    
    for file_path in png_files:
        img = cv2.imread(str(file_path))
        if img is None:
            print(f"⚠️ Không thể đọc file: {file_path.name}")
            continue
            
        h_orig, w_orig, _ = img.shape
        
        # 1. Tiền xử lý ảnh gốc
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 230, 255, cv2.THRESH_BINARY_INV)
        
        # 2. 🔥 KỸ THUẬT SAFE ZONE: Xóa sạch nhiễu ở 5% rìa ngoài trang giấy
        margin_w = int(w_orig * 0.05)  # Bỏ 5% chiều rộng mép trái/phải
        margin_h = int(h_orig * 0.05)  # Bỏ 5% chiều cao mép trên/dưới
        
        thresh[0:margin_h, :] = 0                     # Xóa mép trên
        thresh[h_orig-margin_h:h_orig, :] = 0         # Xóa mép dưới
        thresh[:, 0:margin_w] = 0                     # Xóa mép trái
        thresh[:, w_orig-margin_w:w_orig] = 0         # Xóa mép phải
        
        # 3. Tìm các đường biên sau khi đã làm sạch rìa
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Lọc theo tỷ lệ hình lớn
            is_large_enough = (w > w_orig * 0.25) and (h > h_orig * 0.18)
            is_not_full_page = (w < w_orig * 0.98) and (h < h_orig * 0.98)
            
            if is_large_enough and is_not_full_page:
                valid_boxes.append((x, y, w, h))
        
        # 4. Kiểm tra và tiến hành tách hình
        if len(valid_boxes) == 2:
            print(f"✅ [VALID] File '{file_path.name}' hợp lệ. Tiến hành tách...")
            
            # Sắp xếp từ trên xuống dưới
            valid_boxes.sort(key=lambda box: box[1])
            
            for index, (x, y, w, h) in enumerate(valid_boxes, start=1):
                cropped_img = img[y:y+h, x:x+w]
                
                # Lưu file (Đổi đuôi ra thành .png cho đồng bộ)
                output_filename = f"{file_path.stem}_part_{index}.png"
                output_path = output_dir / output_filename
                
                cv2.imwrite(str(output_path), cropped_img)
                print(f"   -> Đã lưu: {output_filename}")
        else:
            print(f"⏭️ [SKIP] File '{file_path.name}' không khớp (Tìm thấy {len(valid_boxes)} vùng hình).")

# Chạy lại thử nghiệm
INPUT_FOLDER = "./extracted_images"      
OUTPUT_FOLDER = "./output_parts"   
process_and_split_png_folder(INPUT_FOLDER, OUTPUT_FOLDER)