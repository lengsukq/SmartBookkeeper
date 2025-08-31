import json
import aiohttp
from typing import Dict, Any, Optional
from app.config import settings

class AIService:
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.base_url = settings.AI_API_BASE_URL
        self.model_name = settings.AI_MODEL_NAME
    
    async def process_receipt_to_json(self, ocr_text: str) -> Dict[str, Any]:
        """将OCR结果处理成结构化的JSON记账数据"""
        
        # 构建提示词
        prompt = f"""
        请从以下OCR识别的文本中提取记账信息，并返回JSON格式的数据：
        
        {ocr_text}
        
        请提取以下信息（如果存在）：
        - amount: 金额（数字类型）
        - vendor: 商家名称
        - category: 消费类别（如餐饮、交通、购物等）
        - transaction_date: 交易日期（YYYY-MM-DD格式）
        - description: 摘要描述
        
        如果某项信息无法确定，请设为null。
        只返回JSON格式的数据，不要包含其他解释文本。
        """
        
        # 构建请求数据
        request_data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的记账助手，擅长从文本中提取结构化的记账信息。"
                },
                {
                    "role": "user",
                    "content": prompt
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
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"AI API request failed with status {response.status}")
                
                result = await response.json()
                
                # 解析结果
                if "error" in result:
                    raise Exception(f"AI API error: {result['error']}")
                
                # 提取AI返回的文本
                ai_response = result["choices"][0]["message"]["content"].strip()
                
                # 尝试解析JSON
                try:
                    # 如果AI返回的是JSON格式的字符串，直接解析
                    if ai_response.startswith("{") and ai_response.endswith("}"):
                        return json.loads(ai_response)
                    
                    # 如果AI返回的不是纯JSON，尝试从中提取JSON部分
                    start_idx = ai_response.find("{")
                    end_idx = ai_response.rfind("}") + 1
                    
                    if start_idx != -1 and end_idx != -1:
                        json_str = ai_response[start_idx:end_idx]
                        return json.loads(json_str)
                    
                    # 如果无法提取JSON，返回错误
                    raise ValueError("AI response does not contain valid JSON")
                    
                except json.JSONDecodeError as e:
                    raise Exception(f"Failed to parse AI response as JSON: {e}")
    
    async def generate_confirmation_message(self, transaction_data: Dict[str, Any]) -> str:
        """生成确认消息"""
        
        prompt = f"""
        基于以下记账数据，生成一条友好的确认消息：
        
        金额: {transaction_data.get('amount', '未知')}
        商家: {transaction_data.get('vendor', '未知')}
        类别: {transaction_data.get('category', '未知')}
        日期: {transaction_data.get('transaction_date', '未知')}
        摘要: {transaction_data.get('description', '无')}
        
        请生成一条简洁、友好的确认消息，提醒用户确认这些信息是否正确。
        """
        
        # 构建请求数据
        request_data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的记账助手，擅长生成友好的用户交互消息。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 发送请求
        url = f"{self.base_url}/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"AI API request failed with status {response.status}")
                
                result = await response.json()
                
                # 解析结果
                if "error" in result:
                    raise Exception(f"AI API error: {result['error']}")
                
                # 返回生成的消息
                return result["choices"][0]["message"]["content"].strip()

# 创建服务实例
ai_service = AIService()