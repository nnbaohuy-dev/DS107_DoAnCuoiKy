import cv2 as cv
import numpy as np
import os
from sklearn.preprocessing import StandardScaler
from skimage.feature import hog, local_binary_pattern
from sklearn.model_selection import train_test_split
from Object_detection_CBD import process_and_plot_coffee_bean

def load_data_and_labels(base_folder):
    """
    Hàm đọc dữ liệu từ thư mục, trích xuất đặc trưng và gán nhãn, 
    kèm theo mảng 'groups' để theo dõi nguồn gốc ảnh gốc của từng hạt.
    """
    images = []
    labels = []
    groups = [] # Mảng lưu tên file ảnh gốc để chống Data Leakage
    
    # Định nghĩa nhãn cho 7 lớp dữ liệu (theo danh sách target_names của bạn)
    class_mapping = {
        "A": 0,
        "AA": 1,
        "AAA": 2,
        "Bits": 3,
        "C": 4,
        "PB-I": 5,
        "PB-II": 6
    }
    
    for folder_name, label in class_mapping.items():
        folder_path = os.path.join(base_folder, folder_name)
        
        if not os.path.exists(folder_path):
            print(f"Warning: Không tìm thấy thư mục {folder_path}")
            continue
            
        for filename in os.listdir(folder_path):
            img_path = os.path.join(folder_path, filename)
            
            # Đọc ảnh và tách từng hạt
            imgs = process_and_plot_coffee_bean(img_path)
            
            if imgs is not None:
                # Hứng 3 biến: Ảnh tự nhiên, Ảnh nền trắng, Vector Hình học
                for img_natural, img_white_bg, geom_features in imgs:
                    
                    # ==========================================
                    # 1. TRÍCH XUẤT HOG TỪ ẢNH TỰ NHIÊN
                    # ==========================================
                    img_blur = cv.bilateralFilter(img_natural, 5, 50, 50)
                    gray = cv.cvtColor(img_blur, cv.COLOR_BGR2GRAY)

                    hog_feature = hog(
                        gray,
                        orientations=12,
                        pixels_per_cell=(8, 8),
                        cells_per_block=(2, 2),
                        block_norm='L2-Hys'
                    )

                    # ==========================================
                    # 2. TẠO MẶT NẠ (MASK) TỪ ẢNH NỀN TRẮNG
                    # ==========================================
                    gray_white = cv.cvtColor(img_white_bg, cv.COLOR_BGR2GRAY)
                    _, mask = cv.threshold(gray_white, 254, 255, cv.THRESH_BINARY_INV)

                    # ==========================================
                    # 3. TRÍCH XUẤT COLOR HISTOGRAM 
                    # ==========================================
                    hsv_white = cv.cvtColor(img_white_bg, cv.COLOR_BGR2HSV)
                    bins = 64
                    hist_h = cv.calcHist([hsv_white], [0], mask, [bins], [0, 180])
                    hist_s = cv.calcHist([hsv_white], [1], mask, [bins], [0, 256])
                    hist_v = cv.calcHist([hsv_white], [2], mask, [bins], [0, 256])
                    
                    cv.normalize(hist_h, hist_h)
                    cv.normalize(hist_s, hist_s)
                    cv.normalize(hist_v, hist_v)
                    color_hist_feature = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])

                    # ==========================================
                    # 4. TRÍCH XUẤT BỀ MẶT BẰNG LBP
                    # ==========================================
                    gray_nat = cv.cvtColor(img_natural, cv.COLOR_BGR2GRAY)
                    radius = 2
                    n_points = 8 * radius
                    
                    lbp = local_binary_pattern(gray_nat, n_points, radius, method='uniform')
                    
                    n_bins = n_points + 2
                    lbp_hist, _ = np.histogram(lbp[mask == 255], bins=n_bins, range=(0, n_bins))
                    lbp_hist = lbp_hist.astype(np.float32)
                    cv.normalize(lbp_hist, lbp_hist) 

                    # ==========================================
                    # 5. DUNG HỢP VÀ LƯU TRỮ
                    # ==========================================
                    feature = np.concatenate([geom_features, hog_feature, color_hist_feature, lbp_hist])

                    images.append(feature)
                    labels.append(label)
                    groups.append(filename) # LƯU TÊN FILE ĐỂ CHỐNG LEAKAGE

    flatten_images = np.array(images, dtype=np.float32)
    data_labels = np.array(labels, dtype=np.int32)
    data_groups = np.array(groups) # Chuyển groups sang numpy array
    
    return flatten_images, data_labels, data_groups


def data_preprocessing(base_folder="CBD_Coffee Bean Dataset"):
    print("Đang đọc, trích xuất Hình học, HOG, Color Histogram và LBP...")
    X_all, y_all, groups_all = load_data_and_labels(base_folder)
    
    print("Đang chia tập dữ liệu đảm bảo Cân bằng Class và Chống Leakage...")

    # 1. Trích xuất danh sách các bức ảnh duy nhất và nhãn của chúng
    # (Vì mỗi ảnh chỉ thuộc 1 lớp, nên nhãn của ảnh chính là nhãn của các hạt bên trong nó)
    unique_groups, indices = np.unique(groups_all, return_index=True)
    unique_labels = y_all[indices]
    
    # 2. CHIA ẢNH (Image-level split): Áp dụng Stratify lên cấp độ ảnh
    # Bước 2.1: Tách 30% làm ảnh Temp, 70% làm ảnh Train
    train_img, temp_img, train_img_labels, temp_img_labels = train_test_split(
        unique_groups, unique_labels, 
        test_size=0.30, 
        random_state=42, 
        stratify=unique_labels # Ép tỷ lệ 70% ảnh mỗi lớp vào Train
    )
    
    # Bước 2.2: Tách đôi số ảnh Temp (mỗi nửa 15%) thành Val và Test
    val_img, test_img, _, _ = train_test_split(
        temp_img, temp_img_labels, 
        test_size=0.50, 
        random_state=42, 
        stratify=temp_img_labels # Ép tỷ lệ 15% ảnh mỗi lớp vào Val/Test
    )

    # 3. GÁN HẠT VỀ TẬP (Ánh xạ từ ảnh sang hạt)
    # Tìm index của các hạt tương ứng với danh sách ảnh đã chia
    train_mask = np.isin(groups_all, train_img)
    val_mask = np.isin(groups_all, val_img)
    test_mask = np.isin(groups_all, test_img)

    # Chia mảng X_all và y_all dựa trên mask
    X_train, y_train = X_all[train_mask], y_all[train_mask]
    X_val, y_val = X_all[val_mask], y_all[val_mask]
    X_test, y_test = X_all[test_mask], y_all[test_mask]

    # 4. Scale dữ liệu với StandardScaler
    print("Đang chuẩn hóa với StandardScaler...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)
    
    print(f"Kích thước X_train: {X_train.shape}")
    print(f"Kích thước X_val:   {X_val.shape}")
    print(f"Kích thước X_test:  {X_test.shape}")
    print("Xử lý dữ liệu hoàn tất!")
    
    return X_train, y_train, X_val, y_val, X_test, y_test