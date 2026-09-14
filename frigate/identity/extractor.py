"""Local Multi-Scale Feature Extractor & Cosine Similarity for ANDRO-Vision."""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calculate normalized cosine similarity between two feature vectors."""
    if v1 is None or v2 is None:
        return 0.0
    v1 = np.asarray(v1, dtype=np.float32).flatten()
    v2 = np.asarray(v2, dtype=np.float32).flatten()
    if len(v1) != len(v2) or len(v1) == 0:
        return 0.0
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    
    dot = np.dot(v1, v2) / (norm1 * norm2)
    return float(np.clip((dot + 1.0) / 2.0 if dot < 0 else dot, 0.0, 1.0))

class LocalFeatureExtractor:
    """
    Lightweight, high-speed, local appearance feature extractor.
    Extracts a 192-D normalized color-spatial descriptor from object crops.
    """

    def __init__(self, target_size: tuple[int, int] = (128, 128)):
        self.target_size = target_size

    def extract_from_image(self, image: np.ndarray) -> np.ndarray | None:
        """
        Extract normalized feature vector from a BGR image / crop.
        Returns a 192-dimensional float32 vector with unit L2 norm.
        """
        if image is None or image.size == 0:
            return None

        try:
            # Standardize crop size
            h, w = image.shape[:2]
            if h < 16 or w < 16:
                return None

            resized = cv2.resize(image, self.target_size, interpolation=cv2.INTER_AREA)

            # 1. Spatial Grid HSV Histogram (3x3 grid = 9 cells, 16 bins per cell = 144 features)
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            cell_h, cell_w = self.target_size[1] // 3, self.target_size[0] // 3
            hist_features = []

            for row in range(3):
                for col in range(3):
                    cell = hsv[row * cell_h : (row + 1) * cell_h, col * cell_w : (col + 1) * cell_w]
                    # 8 bins for H, 4 for S, 4 for V
                    h_hist = cv2.calcHist([cell], [0], None, [8], [0, 180])
                    s_hist = cv2.calcHist([cell], [1], None, [4], [0, 256])
                    v_hist = cv2.calcHist([cell], [2], None, [4], [0, 256])
                    cell_hist = np.concatenate([h_hist.flatten(), s_hist.flatten(), v_hist.flatten()])
                    c_norm = np.linalg.norm(cell_hist)
                    if c_norm > 0:
                        cell_hist = cell_hist / c_norm
                    hist_features.append(cell_hist)

            hist_vec = np.concatenate(hist_features)  # 144 features

            # 2. Lab Color Moments across 3 horizontal strips (top, middle, bottom = 27 features)
            lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
            moment_features = []
            strip_h = self.target_size[1] // 3
            for i in range(3):
                strip = lab[i * strip_h : (i + 1) * strip_h, :]
                for ch in range(3):
                    channel = strip[:, :, ch].astype(np.float32)
                    mean = np.mean(channel) / 255.0
                    std = np.std(channel) / 128.0
                    # Standardized 3rd moment (skewness approximation)
                    diff = (channel - np.mean(channel)) / (np.std(channel) + 1e-5)
                    skew = np.clip(np.mean(diff ** 3) / 10.0, -1.0, 1.0)
                    moment_features.extend([mean, std, skew])

            moment_vec = np.array(moment_features, dtype=np.float32)  # 27 features

            # 3. Spatial Gradient & Edge Energy across horizontal bands (21 features)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            magnitude = cv2.magnitude(grad_x, grad_y)
            
            grad_features = []
            grad_strip_h = self.target_size[1] // 7  # 7 bands
            for i in range(7):
                band = magnitude[i * grad_strip_h : (i + 1) * grad_strip_h, :]
                grad_features.extend([
                    np.mean(band) / 255.0,
                    np.std(band) / 128.0,
                    np.percentile(band, 90) / 255.0,
                ])
            grad_vec = np.array(grad_features, dtype=np.float32)  # 21 features

            # Concatenate all features: 144 + 27 + 21 = 192 features
            combined = np.concatenate([hist_vec, moment_vec, grad_vec]).astype(np.float32)

            # L2 Normalize total feature vector
            total_norm = np.linalg.norm(combined)
            if total_norm > 0:
                combined = combined / total_norm

            return combined
        except Exception as e:
            logger.error("Error extracting local features: %s", e)
            return None

    def extract_from_bytes(self, image_bytes: bytes) -> np.ndarray | None:
        """Decode image bytes and extract normalized feature vector."""
        if not image_bytes:
            return None
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return self.extract_from_image(img)
        except Exception as e:
            logger.error("Error decoding image bytes for feature extraction: %s", e)
            return None


# Module-level aliases
FeatureExtractor = LocalFeatureExtractor
