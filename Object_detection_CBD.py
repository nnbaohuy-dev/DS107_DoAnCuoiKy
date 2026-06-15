import cv2
import numpy as np
import os

def process_and_plot_coffee_bean(image_path):
    if not os.path.exists(image_path):
        print(f"Lỗi: Không tìm thấy file ảnh tại '{image_path}'")
        return []

    # 1. Đọc ảnh và thiết lập
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_h, img_w = img.shape[:2]
    image_area = img_h * img_w
    min_area = image_area * 0.00015
    max_area = image_area * 0.00375
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    _, s, _ = cv2.split(hsv)

    # 2. Vòng lặp tìm Threshold tối ưu trên toàn ảnh
    number_of_contours = 0
    max_threshold = 110
    threshold = 10
    final_threshold = 10
    count = 0
    while threshold <= max_threshold:
        _, thresh = cv2.threshold(s, threshold, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours_count = 0
        if contours:
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area < area < max_area:
                    valid_contours_count += 1
        
        if valid_contours_count > number_of_contours:
            number_of_contours = valid_contours_count
            final_threshold = threshold
            threshold += 5
            count = 0
        elif valid_contours_count == number_of_contours:
            threshold += 5
            count += 1
        elif valid_contours_count < number_of_contours and count <= 3:
            threshold += 5
            count += 1
        elif valid_contours_count < number_of_contours and count > 3:
            break
    
    # Threshold lần 1 để định vị tọa độ hạt
    _, final_thresh_mask = cv2.threshold(s, final_threshold, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(final_thresh_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # List lưu trữ Tuple: (Ảnh đã xử lý, Vector Đặc trưng)
    processed_beans = []

    if contours:
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                
                # --- TÌM KHUNG BAO CẮT ẢNH ---
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
                side_length = 208 # Cố định khung cắt để giữ tỷ lệ kích thước thật
                half_side = side_length // 2

                sq_x = max(0, center_x - half_side)
                sq_y = max(0, center_y - half_side)

                if sq_x + side_length > img_w: sq_x = img_w - side_length
                if sq_y + side_length > img_h: sq_y = img_h - side_length

                bounding_box_area = side_length * side_length
                if bounding_box_area < image_area * 0.0125:

                    # --- CẮT ẢNH VÀ XÓA NỀN CỤC BỘ ---
                    cropped_bean = img_rgb[sq_y:sq_y + side_length, sq_x:sq_x + side_length]
                    hsv_crop = cv2.cvtColor(cropped_bean, cv2.COLOR_RGB2HSV)
                    _, s_crop, _ = cv2.split(hsv_crop)
                    
                    # Dùng Otsu trên từng khung nhỏ để tìm mask sát nhất
                    _, bean_mask = cv2.threshold(s_crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                    bean_mask = cv2.morphologyEx(bean_mask, cv2.MORPH_OPEN, kernel)
                    bean_mask = cv2.morphologyEx(bean_mask, cv2.MORPH_CLOSE, kernel)
                    
                    mask_contours, _ = cv2.findContours(bean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    perfect_mask = np.zeros_like(bean_mask)
                    geom_features = np.zeros(5, dtype=np.float32)
                    
                    if mask_contours:
                        # 1. Trích xuất viền thật của hạt
                        largest_mask_contour = max(mask_contours, key=cv2.contourArea)
                        
                        # 2. Tạo viền Bao lồi (Convex Hull) bọc qua vết khuyết/lẹm đen
                        hull = cv2.convexHull(largest_mask_contour)
                        cv2.drawContours(perfect_mask, [hull], 0, 255, -1)
                        
                        # =========================================================
                        # TÍNH TOÁN 5 ĐẶC TRƯNG HÌNH HỌC TỪ VIỀN THẬT (largest_mask_contour)
                        # =========================================================
                        true_area = cv2.contourArea(largest_mask_contour)
                        true_perimeter = cv2.arcLength(largest_mask_contour, True)
                        hull_area = cv2.contourArea(hull)
                        
                        # Tính Circularity
                        circularity = 0
                        if true_perimeter > 0:
                            circularity = (4 * np.pi * true_area) / (true_perimeter ** 2)
                            
                        # Tính Aspect Ratio (Dùng minAreaRect để KHÔNG BỊ sai khi hạt nằm chéo)
                        rect = cv2.minAreaRect(largest_mask_contour)
                        (rect_w, rect_h) = rect[1]
                        aspect_ratio = 0
                        if min(rect_w, rect_h) > 0:
                            aspect_ratio = max(rect_w, rect_h) / min(rect_w, rect_h)
                            
                        # Tính Solidity (Độ đặc nguyên vẹn)
                        solidity = 0
                        if hull_area > 0:
                            solidity = float(true_area) / hull_area
                            
                        # Gói gọn 5 chỉ số vào mảng Numpy
                        geom_features = np.array([true_area, true_perimeter, circularity, aspect_ratio, solidity], dtype=np.float32)

                    # Dùng mask vừa có được để xóa nền xung quanh hạt
                    cropped_bean_no_bg = cv2.bitwise_and(cropped_bean, cropped_bean, mask=perfect_mask)
                    
                    # BIẾN NỀN THÀNH MÀU TRẮNG thay vì màu Đen
                    cropped_bean_no_bg[perfect_mask == 0] = [255, 255, 255]

                    # Resize về kích thước chuẩn hóa của mô hình
                    final_resized_no_bg = cv2.resize(cropped_bean_no_bg, (64, 64), interpolation=cv2.INTER_AREA)
                    
                    # 2. Resize ảnh GỐC CHƯA XÓA NỀN (Dành cho HOG)
                    final_resized_original = cv2.resize(cropped_bean, (64, 64), interpolation=cv2.INTER_AREA)
                    
                    # Thêm Tuple gồm 3 phần tử vào list
                    processed_beans.append((
                        cv2.cvtColor(final_resized_original, cv2.COLOR_RGB2BGR), # Ảnh cho HOG
                        cv2.cvtColor(final_resized_no_bg, cv2.COLOR_RGB2BGR),    # Ảnh cho Histogram
                        geom_features                                            # Các thông số vật lý
                    ))

        return processed_beans 
    else:
        print("[LỖI] Không tìm thấy hạt cà phê!")
        return []