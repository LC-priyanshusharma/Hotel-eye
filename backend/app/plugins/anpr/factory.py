from app.plugins.anpr.interfaces import IPlateDetector, IOCR
from app.plugins.anpr.detector import GenericYOLOPlateDetector, IndianYOLOPlateDetector
from app.plugins.anpr.ocr import PaddleOCRWrapper, AwirosOCRWrapper
from app.plugins.anpr.config_parser import anpr_app_config
from loguru import logger

class ANPRFactory:
    """
    Factory for dependency injection of Plate Detectors and OCR wrappers based on config.yaml
    """
    @staticmethod
    def get_plate_detector() -> IPlateDetector:
        provider = anpr_app_config.plate_detector.provider.lower()
        model_path = anpr_app_config.plate_detector.model_path
        conf_thresh = anpr_app_config.plate_detector.confidence_threshold
        
        if provider == "indian_yolo":
            logger.info("Injecting IndianYOLOPlateDetector")
            return IndianYOLOPlateDetector(model_path=model_path, conf_threshold=conf_thresh)
        else:
            logger.info("Injecting GenericYOLOPlateDetector")
            return GenericYOLOPlateDetector(model_path=model_path, conf_threshold=conf_thresh)
            
    @staticmethod
    def get_ocr_engine() -> IOCR:
        provider = anpr_app_config.ocr.provider.lower()
        model_path = anpr_app_config.ocr.model_path
        use_gpu = anpr_app_config.ocr.use_gpu
        
        if provider == "awiros":
            logger.info("Injecting AwirosOCRWrapper")
            return AwirosOCRWrapper(model_path=model_path, use_gpu=use_gpu)
        else:
            logger.info("Injecting PaddleOCRWrapper")
            # Default paddle language to english as per original setup
            return PaddleOCRWrapper(use_gpu=use_gpu, lang="en")
