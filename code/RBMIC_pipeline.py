import cv2
import numpy as np
import os
import sys
from tkinter import Tk, filedialog
import time

from scipy.interpolate import RBFInterpolator
# import SimpleITK as sitk
# from skimage import transform as sktransform
import matplotlib.pyplot as plt

def robust_nonlinear_registration(HE_roi, fluorescence_reged, HE_points, fluorescence_points):
    """
    鲁棒的非线性配准函数
    
    参数:
    HE_roi: HE图像 (numpy array)
    fluorescence_reged: 荧光图像 (numpy array) 
    HE_points: HE图像上的标记点 (N,2) array
    fluorescence_points: 荧光图像上的对应点 (N,2) array
    
    返回:
    registered_fluorescence: 配准后的荧光图像
    transformation: 变换对象
    """
    
    # 将点转换为numpy数组
    HE_points = np.array(HE_points)
    fluorescence_points = np.array(fluorescence_points)
    
    print(f"标记点数量: {len(HE_points)}")
    
    # 检查图像维度并确保是2D灰度图像
    HE_roi_gray = preprocess_image(HE_roi)
    fluorescence_reged_gray = preprocess_image(fluorescence_reged)
    
    # 方法1: 使用改进的RBF配准
    def improved_rbf_registration():
        """使用改进的RBF进行非线性配准"""
        try:
            # 确保有足够的点进行配准
            if len(HE_points) < 3:
                print("警告: 标记点数量不足，至少需要3个点")
                return None, None
            
            # 计算位移场
            displacement = HE_points - fluorescence_points
            
            # 创建RBF插值器
            rbf_x = RBFInterpolator(fluorescence_points, displacement[:, 0], kernel='thin_plate_spline')
            rbf_y = RBFInterpolator(fluorescence_points, displacement[:, 1], kernel='thin_plate_spline')
            
            # 生成坐标网格 - 使用灰度图像的形状
            height, width = fluorescence_reged_gray.shape
            y_coords, x_coords = np.mgrid[0:height, 0:width]
            coordinates = np.column_stack([x_coords.ravel(), y_coords.ravel()])
            
            # 计算每个点的位移
            print("计算位移场...")
            dx = rbf_x(coordinates).reshape((height, width))
            dy = rbf_y(coordinates).reshape((height, width))
            
            # 创建映射
            map_x = x_coords + dx
            map_y = y_coords + dy
            
            # 对原始图像应用变换（保持原始通道数）
            if len(fluorescence_reged.shape) == 3:  # 彩色图像
                registered = np.zeros_like(fluorescence_reged)
                for channel in range(fluorescence_reged.shape[2]):
                    registered[:, :, channel] = cv2.remap(
                        fluorescence_reged[:, :, channel].astype(np.float32), 
                        map_x.astype(np.float32), 
                        map_y.astype(np.float32),
                        cv2.INTER_LINEAR
                    )
            else:  # 灰度图像
                registered = cv2.remap(
                    fluorescence_reged.astype(np.float32), 
                    map_x.astype(np.float32), 
                    map_y.astype(np.float32),
                    cv2.INTER_LINEAR
                )
                
            return registered, (rbf_x, rbf_y)
            
        except Exception as e:
            print(f"RBF配准失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    # 方法2: 使用移动最小二乘法(MLS)
    def mls_registration():
        """使用移动最小二乘法进行非线性配准"""
        try:
            if len(HE_points) < 3:
                return None, None
                
            registered = moving_least_squares(fluorescence_reged, fluorescence_points, HE_points)
            return registered, "MLS"
        except Exception as e:
            print(f"MLS配准失败: {e}")
            return None, None
    
    # 方法3: 使用多项式变换
    def polynomial_registration():
        """使用多项式变换进行配准"""
        try:
            if len(HE_points) < 6:  # 二次多项式需要至少6个点
                print("多项式变换需要至少6个点")
                return None, None
                
            # 计算多项式变换
            transformation = cv2.estimateAffine2D(fluorescence_points, HE_points, method=cv2.RANSAC)
            if transformation[0] is not None:
                registered = cv2.warpAffine(
                    fluorescence_reged, 
                    transformation[0], 
                    (HE_roi.shape[1], HE_roi.shape[0]),
                    flags=cv2.INTER_LINEAR
                )
                return registered, transformation[0]
            return None, None
            
        except Exception as e:
            print(f"多项式变换失败: {e}")
            return None, None
    
    # 尝试多种配准方法
    methods = [
        ("改进RBF", improved_rbf_registration),
        # ("移动最小二乘法", mls_registration),  # 太耗时
        ("多项式变换", polynomial_registration)
    ]
    
    best_result = None
    best_method = None
    min_error = float('inf')
    
    for method_name, method_func in methods:
        print(f"尝试 {method_name} 配准...")
        try:
            registered, transform = method_func()
            
            if registered is not None:
                # 评估配准质量
                error = evaluate_registration_quality(HE_points, fluorescence_points, registered, method_name)
                print(f"{method_name} 配准误差: {error:.4f}")
                
                if error < min_error:
                    min_error = error
                    best_result = (registered, transform)
                    best_method = method_name
            else:
                print(f"{method_name} 返回空结果")
                
        except Exception as e:
            print(f"{method_name} 执行出错: {e}")
            continue
    
    if best_result is not None:
        print(f"选择最佳方法: {best_method}, 误差: {min_error:.4f}")
        return best_result
    else:
        print("所有配准方法均失败，尝试使用仿射变换作为备选")
        # 使用仿射变换作为备选
        try:
            transformation = cv2.estimateAffine2D(fluorescence_points, HE_points)[0]
            registered = cv2.warpAffine(
                fluorescence_reged, 
                transformation, 
                (HE_roi.shape[1], HE_roi.shape[0]),
                flags=cv2.INTER_LINEAR
            )
            return registered, transformation
        except:
            print("备选方案也失败，返回原始图像")
            return fluorescence_reged, None

def preprocess_image(image):
    """预处理图像，确保是2D灰度图像"""
    if len(image.shape) == 3:
        # 如果是彩色图像，转换为灰度
        if image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        elif image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
    return image

def moving_least_squares(image, source_points, target_points, alpha=1.0):
    """移动最小二乘法实现"""
    height, width = image.shape[:2]
    result = np.zeros_like(image)
    
    # 为每个像素计算变换
    for y in range(height):
        for x in range(width):
            # 计算权重
            weights = []
            for i in range(len(source_points)):
                dist = np.linalg.norm([x - source_points[i, 0], y - source_points[i, 1]])
                weight = 1.0 / (dist**2 * alpha + 1e-8)
                weights.append(weight)
            
            weights = np.array(weights)
            weights /= np.sum(weights)  # 归一化
            
            # 计算加权中心
            center_src = np.sum(weights[:, np.newaxis] * source_points, axis=0)
            center_tgt = np.sum(weights[:, np.newaxis] * target_points, axis=0)
            
            # 计算仿射变换
            X = source_points - center_src
            Y = target_points - center_tgt
            
            # 计算变换矩阵
            A = np.zeros((2, 2))
            for i in range(len(weights)):
                A += weights[i] * np.outer(Y[i], X[i])
            
            # 计算新位置
            p = np.array([x, y]) - center_src
            new_p = np.dot(A, p) + center_tgt
            
            new_x, new_y = new_p
            
            # 双线性插值
            if 0 <= new_x < width-1 and 0 <= new_y < height-1:
                x1, y1 = int(new_x), int(new_y)
                x2, y2 = x1 + 1, y1 + 1
                
                dx, dy = new_x - x1, new_y - y1
                
                # 处理多通道图像
                if len(image.shape) == 3:
                    for c in range(image.shape[2]):
                        result[y, x, c] = (1 - dx) * (1 - dy) * image[y1, x1, c] + \
                                         dx * (1 - dy) * image[y1, x2, c] + \
                                         (1 - dx) * dy * image[y2, x1, c] + \
                                         dx * dy * image[y2, x2, c]
                else:
                    result[y, x] = (1 - dx) * (1 - dy) * image[y1, x1] + \
                                 dx * (1 - dy) * image[y1, x2] + \
                                 (1 - dx) * dy * image[y2, x1] + \
                                 dx * dy * image[y2, x2]
    
    return result

def evaluate_registration_quality(HE_points, fluorescence_points, registered_image, method_name):
    """评估配准质量"""
    try:
        # 简化评估：使用点对之间的平均距离
        if method_name == "改进RBF":
            # 对于RBF，我们可以估计变换后的点位置
            distances = np.sqrt(np.sum((HE_points - fluorescence_points) ** 2, axis=1))
        else:
            # 对于其他方法，使用原始点距离
            distances = np.sqrt(np.sum((HE_points - fluorescence_points) ** 2, axis=1))
        
        return np.mean(distances)
    except:
        return float('inf')

class ImageRegistrator:
    def __init__(self):
        self.HE_img = None
        self.fluorescence_img = None
        self.HE_roi = None
        self.fluorescence_roi = None
        self.HE_points = []
        self.fluorescence_points = []
        self.edge_points = []
        self.window_name = "RBMIC Registration Pipeline"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1200, 800)
        self.current_step = 0

    def select_image(self, title):
        """选择图像文件"""
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif")]
        )
        root.destroy()
        if not file_path:
            print("未选择图像，程序退出")
            sys.exit(0)
        return cv2.imread(file_path), file_path

    def preprocess_image(self, img, is_he=True):
        """图像预处理与ROI选择"""
        print(f"\n{'HE' if is_he else '荧光'}图像预处理 - 请框选感兴趣区域(ROI)")
        print("操作提示: 拖动鼠标选择区域，按Enter确认，按c取消重选")
        
        roi = cv2.selectROI(
            self.window_name, 
            img, 
            False, 
            False
        )
        x, y, w, h = roi
        processed = img[y:y+h, x:x+w]
        
        # 显示预处理结果
        cv2.imshow(self.window_name, processed)
        print("预处理结果已显示，按任意键继续...")
        cv2.waitKey(0)
        return processed, roi

    def _get_drawing_params(self, img):
        """根据图像尺寸计算绘制参数（自适应大小）"""
        h, w = img.shape[:2]
        min_dim = min(h, w)  # 以最小维度作为基准
        scale_factor = min_dim / 200  # 基准尺寸为200像素
        
        # 计算绘制参数（确保最小值，避免过小）
        circle_radius = max(1, int(scale_factor * 2))  # 圆半径
        font_scale = max(0.3, scale_factor * 0.5)      # 字体大小
        line_thickness = max(1, int(scale_factor * 1.5))  # 线条粗细
        text_offset = max(2, int(scale_factor * 3))    # 文字偏移量
        
        return circle_radius, font_scale, line_thickness, text_offset

    def click_points(self, img, num_points, title):
        """交互式标记点坐标（自适应绘制大小）"""
        points = []
        print(f"\n{title} - 请点击至少{num_points}个对应点")
        print("操作提示: 点击图像标记点，按r重选，按Enter确认")
        
        # 获取自适应绘制参数
        circle_radius, font_scale, line_thickness, text_offset = self._get_drawing_params(img)
        
        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))
                temp = img.copy()
                for i, (px, py) in enumerate(points):
                    # 根据点索引选择颜色（前4个绿色，之后红色）
                    color = (0, 255, 0) if i < 4 else (0, 0, 255)
                    # 绘制圆圈
                    cv2.circle(temp, (px, py), circle_radius, color, -1)
                    # 绘制点编号文字
                    cv2.putText(temp, str(i+1), 
                               (px + text_offset, py), 
                               cv2.FONT_HERSHEY_SIMPLEX, 
                               font_scale, 
                               (255, 0, 0), 
                               line_thickness)
                cv2.imshow(self.window_name, temp)

        cv2.setMouseCallback(self.window_name, mouse_callback)
        cv2.imshow(self.window_name, img)
        
        while True: # len(points) < num_points:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('r'):  # 重置
                points = []
                cv2.imshow(self.window_name, img)
            elif key == 13:  # Enter键
                if len(points) < num_points:
                    print(f"需要标记{num_points}个点，当前仅标记了{len(points)}个")
                else:
                    break
        
        cv2.setMouseCallback(self.window_name, lambda *args: None)  # 重置鼠标回调
        return np.array(points, dtype=np.float32)

    def register_perspective(self):
        """图像配准计算（自适应文字大小）"""
        print("\n正在进行图像配准...")
        
        # 计算变换矩阵
        M, _ = cv2.findHomography(
            self.fluorescence_points, 
            self.HE_points, 
            cv2.RANSAC, 5.0
        )
        
        # 执行配准
        h, w = self.HE_roi.shape[:2]
        registered = cv2.warpPerspective(
            self.fluorescence_roi, 
            M, 
            (w, h)
        )
        
        # 获取自适应绘制参数
        circle_radius, font_scale, line_thickness, text_offset = self._get_drawing_params(self.HE_roi)
        text_y_pos = max(20, int(text_offset * 10))  # 文字Y坐标
        
        # 可视化配准结果
        overlay = cv2.addWeighted(self.HE_roi, 0.5, registered, 0.5, 0)
        combined = np.hstack((self.HE_roi, registered, overlay))
        
        # 绘制标题文字（自适应大小和位置）
        cv2.putText(combined, "HE Image", 
                   (text_offset * 3, text_y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, 
                   (0, 0, 255), 
                   line_thickness)
        cv2.putText(combined, "Registered Fluorescence", 
                   (w + text_offset * 3, text_y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, 
                   (0, 255, 0), 
                   line_thickness)
        cv2.putText(combined, "Overlay", 
                   (2*w + text_offset * 3, text_y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, 
                   (255, 0, 0), 
                   line_thickness)
        
        cv2.imshow(self.window_name, combined)
        print("配准结果已显示，按任意键继续...")
        cv2.waitKey(0)
        return registered, M

    def affine_transformation(self, M):
        """仿射变换与最终结果可视化（自适应绘制大小）"""
        print("\n正在进行仿射变换...")
        
        # 获取边缘点并执行透视变换
        h, w = self.HE_roi.shape[:2]
        transformed = cv2.warpPerspective(
            self.fluorescence_roi, 
            M, 
            (w, h)
        )
        
        # 绘制边缘点
        edge_transformed = cv2.perspectiveTransform(
            self.edge_points.reshape(-1, 1, 2), 
            M
        ).reshape(-1, 2)
        
        # 获取自适应绘制参数
        circle_radius, font_scale, line_thickness, text_offset = self._get_drawing_params(self.HE_roi)
        text_y_pos = max(20, int(text_offset * 10))  # 文字Y坐标
        
        result = self.HE_roi.copy()
        for (x, y) in edge_transformed.astype(int):
            cv2.circle(result, (x, y), circle_radius, (0, 0, 255), -1)
        
        # 显示最终结果
        final = np.hstack((self.HE_roi, transformed, result))
        
        # 绘制标题文字（自适应大小和位置）
        cv2.putText(final, "Original HE", 
                   (text_offset * 3, text_y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, 
                   (0, 0, 255), 
                   line_thickness)
        cv2.putText(final, "Transformed Fluorescence", 
                   (w + text_offset * 3, text_y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, 
                   (0, 255, 0), 
                   line_thickness)
        cv2.putText(final, "Edge Markers", 
                   (2*w + text_offset * 3, text_y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, 
                   (255, 0, 0), 
                   line_thickness)
        
        cv2.imshow(self.window_name, final)
        print("最终结果已显示，按s保存结果，按任意键结束...")
        key = cv2.waitKey(0)
        if key == ord('s'):
            cv2.imwrite("registration_result.jpg", final)
            print("结果已保存为 registration_result.jpg")

    def run_pipeline(self):
        """运行完整配准流程"""
        try:
            print("===== RBMIC 图像配准流程 =====")
            
            # 1. 加载图像
            self.HE_img, _ = self.select_image("选择HE染色图像")
            self.fluorescence_img, if_path = self.select_image("选择荧光图像")
            start_time = time.time()
            
            # 2. 预处理与ROI选择
            # self.HE_roi, _ = self.preprocess_image(self.HE_img, is_he=True)
            # self.fluorescence_roi, _ = self.preprocess_image(self.fluorescence_img, is_he=False)
            self.HE_roi = self.HE_img
            self.fluorescence_roi = self.fluorescence_img
            
            # 3. 标记对应点(4个)
            self.HE_points = self.click_points(
                self.HE_roi, 3, "HE图像 - 标记至少3个对应点"
            )
            n_HE_points = self.HE_points.shape[0]
            self.fluorescence_points = self.click_points(
                self.fluorescence_roi, n_HE_points, "荧光图像 - 标记%d个对应点(与HE图像对应)" % n_HE_points
            )
            
            # 4. 图像配准
            self.fluorescence_reged, M = self.register_perspective()
            
            # 5. 标记第二轮用于非线性配准
            self.HE_points = self.click_points(
                self.HE_roi, 1, "HE图像 - 标记若干个对应点"
            )
            n_HE_points = self.HE_points.shape[0]
            self.fluorescence_points = self.click_points(
                self.fluorescence_reged, n_HE_points, "荧光图像 - 标记至少%d个对应点" % n_HE_points
            )
            
            # 6. 仿射变换与结果展示
            # self.affine_transformation(M)
            self.fluorescence_non_linear, transform = robust_nonlinear_registration(self.HE_roi, self.fluorescence_reged, self.HE_points, self.fluorescence_points)
            
            # 可视化配准结果
            overlay = cv2.addWeighted(self.HE_roi, 0.5, self.fluorescence_non_linear, 0.5, 0)
            cv2.imshow(self.window_name, overlay)
            save_path = os.path.join(os.path.dirname(if_path), os.path.basename(if_path).split('.')[0] + '_reged.jpg')
            cv2.imwrite(save_path, self.fluorescence_non_linear)
            print("配准结果已显示，按任意键继续... time cost: %.2f" % (time.time() - start_time))
            cv2.waitKey(0)
            
        except Exception as e:
            print(f"处理过程出错: {str(e)}")
        finally:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    # 检查依赖
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("缺少依赖库，请先安装: pip install opencv-python numpy")
        sys.exit(1)
        
    registrator = ImageRegistrator()
    registrator.run_pipeline()