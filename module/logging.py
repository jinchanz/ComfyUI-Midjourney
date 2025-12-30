import logging

# 创建 logger
logger = logging.getLogger("ComfyUI-Midjourney")

# 如果还没有配置 handler，则添加一个
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[MidjourneyAPI] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)



