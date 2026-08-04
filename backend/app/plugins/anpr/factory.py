from app.plugins.anpr.interfaces import IPlateDetector, IOCR
from app.plugins.anpr.detector import GenericYOLOPlateDetector, IndianYOLOPlateDetector
from app.plugins.anpr.providers.paddle_provider import PaddleOCRProvider
from app.plugins.anpr.providers.awiros_provider import AwirosOCRProvider
from app.plugins.anpr.config_parser import anpr_app_config
from loguru import logger

class ANPRFactory:
    """
    Factory for dependency injection of Plate Detectors and OCR wrappers based on config.yaml.
    Implements automatic fallback for OCR providers.
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
        use_gpu = anpr_app_config.ocr.use_gpu
        fallback_provider = anpr_app_config.ocr.fallback_provider.lower()
        
        if provider == "awiros":
            logger.info("Attempting to inject AwirosOCRProvider")
            try:
                # Instantiate Awiros Provider
                # It handles its own download via huggingface_hub according to config
                return AwirosOCRProvider(
                    local_model_path=anpr_app_config.ocr.local_model_path,
                    download_if_missing=anpr_app_config.ocr.download_if_missing,
                    use_gpu=use_gpu
                )
            except Exception as e:
                logger.error(f"Failed to load AwirosOCRProvider: {e}")
                logger.warning(f"Falling back to {fallback_provider} provider.")
                if fallback_provider == "paddle":
                    return PaddleOCRProvider(use_gpu=use_gpu, lang="en")
                else:
                    raise RuntimeError(f"Fallback provider {fallback_provider} not implemented.")
        
        # Default paddle
        logger.info("Injecting PaddleOCRProvider")
        return PaddleOCRProvider(use_gpu=use_gpu, lang="en")
