import aiohttp
import json
import logging
import os
import uuid
import base64
from typing import Dict, Any
from app.config import settings

# 设置日志
logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.api_key = settings.AI_API_KEY  # 使用AI API密钥
        self.base_url = settings.AI_API_BASE_URL  # 从环境变量中读取AI服务API地址
        self.model_name = settings.AI_MODEL_NAME  # 从环境变量中读取AI模型名称
        self.penetrate_url = settings.PENETRATE_URL  # 穿透地址
    
    async def recognize_text(self, image_data: bytes, image_path: str = None) -> Dict[str, Any]:
        """直接使用大模型识别图片中的文本并提取结构化记账信息"""
        # 记录接收到的用户信息
        logger.info("收到新的图片识别请求，开始处理")
        
        # 如果没有提供图片路径，则创建临时文件保存图片
        if image_path is None:
            log_dir = "log"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            filename = f"XiaoHaiYan_{int(uuid.uuid4().time)}_{uuid.uuid4().hex[:8]}.jpg"
            image_path = os.path.join(log_dir, filename)
            
            # 保存图片到本地
            with open(image_path, "wb") as f:
                f.write(image_data)
            
            should_delete = True
        else:
            # 使用提供的图片路径，不删除文件
            filename = os.path.basename(image_path)
            should_delete = False
        
        try:
            # 构建图片的完整URL（用于日志记录）
            image_url = f"{self.penetrate_url}/log/{filename}"
            logger.info(f"图片URL: {image_url}")
            
            # 读取图片数据并转换为base64编码
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            # 直接使用大模型识别图片
            result = await self._process_image_with_ai(image_base64)
            
            # 如果识别失败，返回错误信息
            if not result.get("success", True):
                error_msg = result.get("error", "图片识别失败")
                logger.warning(f"图片识别失败: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
            
            return result
            
        except Exception as e:
            logger.warning(f"图片识别过程中发生异常: {e}")
            return {
                "success": False,
                "error": f"图片识别失败: {str(e)}"
            }
        finally:
            # 如果是临时创建的文件，则清理临时文件
            if should_delete:
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {e}")
        
    async def _process_image_with_ai(self, image_base64: str) -> Dict[str, Any]:
        """直接使用大模型识别图片并提取结构化记账信息"""
        # 构建精准的prompt，严格限制大模型输出结构化的记账信息
        prompt = """
请严格按照以下JSON格式从图片中的收据提取记账信息，不要输出任何JSON之外的内容：
{
  "amount": 金额（数字类型，如12.99）,
  "vendor": "商家名称",
  "category": "消费类别（如餐饮、交通、购物、娱乐、医疗、教育等）",
  "transaction_date": "交易日期（YYYY-MM-DD格式）",
  "description": "摘要描述"
}

要求：
- 金额必须是数字类型（整数或浮点数），不要包含货币符号
- 交易日期必须是YYYY-MM-DD格式，如果图片中没有日期，请使用当前日期
- 商家名称要简洁准确，去除多余的广告语
- 消费类别请选择最贴近的一项：餐饮、交通、购物、娱乐、医疗、教育、住房、通讯、其他
- 摘要描述要简明扼要，突出关键信息
- 如果信息无法识别，保留对应字段的null值
- 不要添加任何解释或说明文本
- 确保输出的内容是合法的JSON格式，不要包含markdown代码块标记
"""
        
        # 构建请求数据，使用多模态格式
        request_data = {
            "model": self.model_name,  # 使用从环境变量中读取的模型名称
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的记账助手，擅长从收据图片中提取结构化的记账信息。严格按照要求返回JSON格式数据，不包含任何解释文本。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,  # 降低随机性，提高一致性
            "max_tokens": 500
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 发送请求
        url = f"{self.base_url}/chat/completions"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=request_data, headers=headers) as response:
                    # 记录API请求信息
                    logger.info(f"发送AI API请求，模型: {self.model_name}, URL: {url}, 状态码: {response.status}")
                    
                    if response.status != 200:
                        # 如果API返回非200状态码，记录错误并返回错误信息
                        try:
                            error_response = await response.text()
                            logger.warning(f"AI API请求失败，状态码: {response.status}, 响应内容: {error_response}")
                        except Exception as e:
                            logger.warning(f"AI API请求失败，状态码: {response.status}, 无法获取响应内容: {e}")
                        return {
                            "success": False,
                            "error": "API请求失败，请检查API配置"
                        }
                    
                    result = await response.json()
                    
                    # 记录AI模型返回的原始消息
                    logger.info(f"AI API返回结果: {result}")
                    
                    # 解析结果
                    if "error" in result:
                        logger.warning(f"AI API返回错误: {result['error']}")
                        return {
                            "success": False,
                            "error": "API请求失败，服务返回错误"
                        }
                    
                    # 提取AI返回的文本
                    ai_response = result["choices"][0]["message"]["content"].strip()
                    
                    # 记录AI返回的文本内容
                    logger.info(f"AI返回的文本内容: {ai_response}")
                    
                    # 尝试解析JSON
                    try:
                        # 如果AI返回的是JSON格式的字符串，直接解析
                        if ai_response.startswith("{") and ai_response.endswith("}"):
                            parsed_data = json.loads(ai_response)
                            logger.info(f"成功解析AI返回的JSON数据: {parsed_data}")
                            return parsed_data
                        
                        # 如果AI返回的不是纯JSON，尝试从中提取JSON部分
                        start_idx = ai_response.find("{")
                        end_idx = ai_response.rfind("}") + 1
                        
                        if start_idx != -1 and end_idx != -1:
                            json_str = ai_response[start_idx:end_idx]
                            parsed_data = json.loads(json_str)
                            logger.info(f"成功提取并解析JSON数据: {parsed_data}")
                            return parsed_data
                        
                        # 如果无法提取JSON，返回错误信息
                        logger.warning(f"AI返回的内容不包含有效的JSON格式: {ai_response}")
                        return {
                            "success": False,
                            "error": "API请求失败，返回格式不正确"
                        }
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析AI返回的JSON失败: {e}, 原始内容: {ai_response}")
                        return {
                            "success": False,
                            "error": "API请求失败，响应解析错误"
                        }
        except Exception as e:
            # 捕获所有其他异常
            logger.warning(f"AI API调用过程中发生异常: {e}")
            return {
                "success": False,
                "error": "API请求失败，服务不可用"
            }
    


# 创建服务实例
ocr_service = OCRService()