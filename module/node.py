import json
import requests
import time
from .logging import logger


def _poll_job_result(job_id, app_id, secret_key, poll_interval, max_wait_time):
    """轮询任务结果"""
    job_url = f"https://ali.youchuan.cn/v1/tob/job/{job_id}"
    headers = {
        "x-youchuan-app": app_id if app_id else "",
        "x-youchuan-secret": secret_key if secret_key else "",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    while True:
        try:
            # 检查是否超时
            if time.time() - start_time > max_wait_time:
                error_msg = f"任务轮询超时 ({max_wait_time}秒)"
                logger.info(f"[MidjourneyAPI] {error_msg}")
                return {"error": error_msg, "job_id": job_id}
            
            logger.info(f"[MidjourneyAPI] 轮询任务状态: {job_id}")
            
            # 查询任务状态
            response = requests.get(job_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result_data = response.json()
            job_status = result_data.get("status", 0)
            comment = result_data.get("comment", "")
            
            logger.info(f"[MidjourneyAPI] 任务状态: {job_status} ({comment})")
            
            # 任务完成 (status: 2 = 成功)
            if job_status == 2:
                logger.info(f"[MidjourneyAPI] 任务完成成功")
                return result_data
            
            # 任务失败 (status: 3 或其他非进行中状态)
            elif job_status == 3:
                error_message = result_data.get("comment", "任务执行失败")
                logger.info(f"[MidjourneyAPI] 任务执行失败: {error_message}")
                return result_data
            
            # 继续等待 (status: 1 = 执行中)
            elif job_status == 1:
                time.sleep(poll_interval)
                continue
            
            # 未知状态
            else:
                logger.info(f"[MidjourneyAPI] 未知任务状态: {job_status}")
                return result_data
                
        except requests.exceptions.RequestException as e:
            error_msg = f"轮询请求失败: {str(e)}"
            logger.info(f"[MidjourneyAPI] {error_msg}")
            return {"error": error_msg, "job_id": job_id}
            
        except Exception as e:
            error_msg = f"轮询过程出错: {str(e)}"
            logger.info(f"[MidjourneyAPI] {error_msg}")
            return {"error": error_msg, "job_id": job_id}


class MidjourneyAPI:
    """Midjourney 文生图 API 节点"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "A beautiful sunset over the mountains"}),
                "app_id": ("STRING", {"default": ""}),
                "secret_key": ("STRING", {"default": ""}),
            },
            "optional": {
                "endpoint": ("STRING", {"default": "https://ali.youchuan.cn/v1/tob/diffusion"}),
                "poll_interval": ("INT", {"default": 3, "min": 1, "max": 30}),
                "max_wait_time": ("INT", {"default": 300, "min": 30, "max": 1800}),
                "auto_poll": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)

    FUNCTION = "run"

    OUTPUT_NODE = True

    CATEGORY = "Midjourney"

    def run(self, text, app_id, secret_key, endpoint="https://ali.youchuan.cn/v1/tob/diffusion", 
            poll_interval=3, max_wait_time=300, auto_poll=True):
        try:
            if not text or text.strip() == "":
                raise ValueError("text 不能为空")
            
            if not app_id or app_id.strip() == "":
                raise ValueError("app_id 不能为空")
            
            if not secret_key or secret_key.strip() == "":
                raise ValueError("secret_key 不能为空")
            
            # 构建请求数据
            request_data = {
                "text": text.strip()
            }
            
            # 设置请求头
            headers = {
                "x-youchuan-app": app_id,
                "x-youchuan-secret": secret_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"[MidjourneyAPI] 发送请求到: {endpoint}, 文本: {text[:50]}...")
            
            # 发送 POST 请求
            response = requests.post(
                endpoint,
                headers=headers,
                json=request_data,
                timeout=30
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 返回响应内容
            response_data = response.json()
            job_id = response_data.get("id", "")
            job_status = response_data.get("status", 0)
            
            logger.info(f"[MidjourneyAPI] 任务提交成功，ID: {job_id}, 状态: {job_status}")
            
            # 如果启用自动轮询且任务在执行中
            if auto_poll and job_id and job_status == 1:
                logger.info(f"[MidjourneyAPI] 开始自动轮询任务结果")
                response_data = _poll_job_result(job_id, app_id, secret_key, poll_interval, max_wait_time)
            
            # 返回结果
            return (json.dumps(response_data, ensure_ascii=False, indent=2),)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API 请求失败: {str(e)}"
            logger.info(f"[MidjourneyAPI] {error_msg}")
            return (json.dumps({"error": error_msg}, ensure_ascii=False),)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {str(e)}"
            logger.info(f"[MidjourneyAPI] {error_msg}")
            return (json.dumps({"error": error_msg}, ensure_ascii=False),)
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.info(f"[MidjourneyAPI] {error_msg}")
            return (json.dumps({"error": error_msg}, ensure_ascii=False),)


class MidjourneyAPISubmit:
    """提交 Midjourney 任务，返回 job_id"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "A beautiful sunset over the mountains"}),
                "app_id": ("STRING", {"default": ""}),
                "secret_key": ("STRING", {"default": ""}),
            },
            "optional": {
                "endpoint": ("STRING", {"default": "https://ali.youchuan.cn/v1/tob/diffusion"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("job_id", "response")

    FUNCTION = "submit"

    OUTPUT_NODE = False

    CATEGORY = "Midjourney"

    def submit(self, text, app_id, secret_key, endpoint="https://ali.youchuan.cn/v1/tob/diffusion"):
        try:
            if not text or text.strip() == "":
                raise ValueError("text 不能为空")
            
            if not app_id or app_id.strip() == "":
                raise ValueError("app_id 不能为空")
            
            if not secret_key or secret_key.strip() == "":
                raise ValueError("secret_key 不能为空")
            
            # 构建请求数据
            request_data = {
                "text": text.strip()
            }
            
            # 设置请求头
            headers = {
                "x-youchuan-app": app_id,
                "x-youchuan-secret": secret_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"[MidjourneyAPISubmit] 提交任务到: {endpoint}, 文本: {text[:50]}...")
            
            # 发送 POST 请求
            response = requests.post(
                endpoint,
                headers=headers,
                json=request_data,
                timeout=30
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 返回响应内容
            response_data = response.json()
            job_id = response_data.get("id", "")
            job_status = response_data.get("status", 0)
            
            if job_id:
                logger.info(f"[MidjourneyAPISubmit] 任务提交成功，ID: {job_id}, 状态: {job_status}")
            else:
                logger.info(f"[MidjourneyAPISubmit] 任务提交完成，但未获取到 job_id")
            
            response_json = json.dumps(response_data, ensure_ascii=False, indent=2)
            return (job_id, response_json)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API 请求失败: {str(e)}"
            logger.info(f"[MidjourneyAPISubmit] {error_msg}")
            error_response = json.dumps({"error": error_msg}, ensure_ascii=False)
            return ("", error_response)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {str(e)}"
            logger.info(f"[MidjourneyAPISubmit] {error_msg}")
            error_response = json.dumps({"error": error_msg}, ensure_ascii=False)
            return ("", error_response)
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.info(f"[MidjourneyAPISubmit] {error_msg}")
            error_response = json.dumps({"error": error_msg}, ensure_ascii=False)
            return ("", error_response)


class MidjourneyAPIPoll:
    """轮询 Midjourney 任务结果"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "job_id": ("STRING", {"forceInput": True}),
                "app_id": ("STRING", {"default": ""}),
                "secret_key": ("STRING", {"default": ""}),
            },
            "optional": {
                "poll_interval": ("INT", {"default": 3, "min": 1, "max": 30}),
                "max_wait_time": ("INT", {"default": 300, "min": 30, "max": 1800}),
                "single_query": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("result", "status")

    FUNCTION = "poll"

    OUTPUT_NODE = True

    CATEGORY = "Midjourney"

    def poll(self, job_id, app_id, secret_key, poll_interval=3, max_wait_time=300, single_query=False):
        if not job_id or job_id.strip() == "":
            error_msg = "job_id 不能为空"
            logger.info(f"[MidjourneyAPIPoll] {error_msg}")
            error_response = json.dumps({"error": error_msg}, ensure_ascii=False)
            return (error_response, 0)
        
        if not app_id or app_id.strip() == "":
            error_msg = "app_id 不能为空"
            logger.info(f"[MidjourneyAPIPoll] {error_msg}")
            error_response = json.dumps({"error": error_msg}, ensure_ascii=False)
            return (error_response, 0)
        
        if not secret_key or secret_key.strip() == "":
            error_msg = "secret_key 不能为空"
            logger.info(f"[MidjourneyAPIPoll] {error_msg}")
            error_response = json.dumps({"error": error_msg}, ensure_ascii=False)
            return (error_response, 0)
        
        job_url = f"https://ali.youchuan.cn/v1/tob/job/{job_id.strip()}"
        headers = {
            "x-youchuan-app": app_id,
            "x-youchuan-secret": secret_key,
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        while True:
            try:
                logger.info(f"[MidjourneyAPIPoll] 查询任务状态: {job_id}")
                
                # 查询任务状态
                response = requests.get(job_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                result_data = response.json()
                job_status = result_data.get("status", 0)
                comment = result_data.get("comment", "")
                
                logger.info(f"[MidjourneyAPIPoll] 任务状态: {job_status} ({comment})")
                
                # 任务完成 (status: 2 = 成功)
                if job_status == 2:
                    logger.info(f"[MidjourneyAPIPoll] 任务完成成功")
                    result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
                    return (result_json, 2)
                
                # 任务失败 (status: 3)
                elif job_status == 3:
                    error_message = result_data.get("comment", "任务执行失败")
                    logger.info(f"[MidjourneyAPIPoll] 任务执行失败: {error_message}")
                    result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
                    return (result_json, 3)
                
                # 如果是单次查询模式，直接返回当前状态
                if single_query:
                    result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
                    return (result_json, job_status)
                
                # 继续等待 (status: 1 = 执行中)
                elif job_status == 1:
                    # 检查是否超时
                    if time.time() - start_time > max_wait_time:
                        error_msg = f"任务轮询超时 ({max_wait_time}秒)"
                        logger.info(f"[MidjourneyAPIPoll] {error_msg}")
                        error_response = json.dumps({"error": error_msg, "job_id": job_id, "last_status": job_status}, ensure_ascii=False)
                        return (error_response, -1)
                    
                    time.sleep(poll_interval)
                    continue
                
                # 未知状态
                else:
                    logger.info(f"[MidjourneyAPIPoll] 未知任务状态: {job_status}")
                    result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
                    return (result_json, job_status)
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"轮询请求失败: {str(e)}"
                logger.info(f"[MidjourneyAPIPoll] {error_msg}")
                error_response = json.dumps({"error": error_msg, "job_id": job_id}, ensure_ascii=False)
                return (error_response, 0)
                
            except Exception as e:
                error_msg = f"轮询过程出错: {str(e)}"
                logger.info(f"[MidjourneyAPIPoll] {error_msg}")
                error_response = json.dumps({"error": error_msg, "job_id": job_id}, ensure_ascii=False)
                return (error_response, 0)


class MidjourneyJSONExtractor:
    """从 JSON 中提取嵌套键值的工具节点"""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_input": ("STRING", {"forceInput": True}),
                "key_path": ("STRING", {"default": "urls.0"}),
            },
            "optional": {
                "default_value": ("STRING", {"default": ""}),
                "return_as_string": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("value",)

    FUNCTION = "extract"

    OUTPUT_NODE = True

    CATEGORY = "Midjourney"

    def extract(self, json_input, key_path, default_value="", return_as_string=True):
        try:
            # 解析JSON
            if isinstance(json_input, str):
                data = json.loads(json_input)
            else:
                data = json_input
            
            # 分割键路径
            keys = key_path.strip().split('.')
            
            # 逐层访问数据
            current_data = data
            for key in keys:
                if isinstance(current_data, dict) and key in current_data:
                    current_data = current_data[key]
                elif isinstance(current_data, list) and key.isdigit():
                    # 支持数组索引，如 "urls.0"
                    index = int(key)
                    if 0 <= index < len(current_data):
                        current_data = current_data[index]
                    else:
                        raise KeyError(f"数组索引 {index} 超出范围")
                else:
                    raise KeyError(f"键 '{key}' 不存在")
            
            # 处理返回值
            if return_as_string:
                if isinstance(current_data, (dict, list)):
                    result = json.dumps(current_data, ensure_ascii=False, indent=2)
                else:
                    result = str(current_data)
            else:
                result = str(current_data) if current_data is not None else ""
            
            logger.info(f"[JSONExtractor] 成功提取键路径 '{key_path}': {result[:100]}{'...' if len(str(result)) > 100 else ''}")
            formatted_result = None
            try:
                formatted_result = json.loads(result) if isinstance(result, str) else result
            except json.JSONDecodeError:
                logger.info(f"[JSONExtractor] 格式化结果失败，无法解析JSON，可能不是JSON格式: {result}")
                formatted_result = result
            return {"ui": {"json": [formatted_result], "text": [result]}, "result": (formatted_result,)}
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {str(e)}"
            logger.info(f"[JSONExtractor] {error_msg}")
            return (default_value,)
            
        except KeyError as e:
            error_msg = f"键路径 '{key_path}' 不存在: {str(e)}"
            logger.info(f"[JSONExtractor] {error_msg}")
            return (default_value,)
            
        except Exception as e:
            error_msg = f"提取过程出错: {str(e)}"
            logger.info(f"[JSONExtractor] {error_msg}")
            return (default_value,)


# 节点映射
NODE_CLASS_MAPPINGS = {
    "MidjourneyAPI": MidjourneyAPI,
    "MidjourneyAPISubmit": MidjourneyAPISubmit,
    "MidjourneyAPIPoll": MidjourneyAPIPoll,
    "MidjourneyJSONExtractor": MidjourneyJSONExtractor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MidjourneyAPI": "Midjourney API",
    "MidjourneyAPISubmit": "Midjourney API Submit",
    "MidjourneyAPIPoll": "Midjourney API Poll",
    "MidjourneyJSONExtractor": "Midjourney JSON Extractor",
}

