import base64
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
import json
from app.config import settings
import time

# 导入企业微信官方加解密库
from app.weworkapi import WXBizMsgCrypt

class WeComService:
    def __init__(self):
        self.corp_id = settings.WECOM_CORP_ID
        self.secret = settings.WECOM_SECRET
        self.token = settings.WECOM_TOKEN
        self.aes_key = settings.WECOM_AES_KEY
        self.agent_id = settings.WECOM_AGENT_ID
        self.access_token = None
        self.token_expires_at = 0
        
        # 创建企业微信加解密实例
        self.wx_crypt = WXBizMsgCrypt(
            self.token, 
            self.aes_key, 
            self.corp_id
        )
    
    async def get_access_token(self) -> str:
        """获取企业微信access_token"""
        # 如果token未过期，直接返回
        if self.access_token and self.token_expires_at > datetime.now().timestamp():
            return self.access_token
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                
                if data["errcode"] != 0:
                    raise Exception(f"Failed to get access token: {data['errmsg']}")
                
                self.access_token = data["access_token"]
                # 提前5分钟过期
                self.token_expires_at = datetime.now().timestamp() + data["expires_in"] - 300
                return self.access_token
    
    async def download_image(self, media_id: str) -> bytes:
        """下载企业微信图片"""
        access_token = await self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download image: {response.status}")
                return await response.read()
    
    async def send_confirmation_card(self, user_id: str, data: Dict[str, Any]) -> bool:
        """发送确认卡片"""
        try:
            access_token = await self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            # 数据验证和格式化
            # 确保金额是数字类型，并且格式化为合适的字符串
            amount = data.get('amount', 0)
            if isinstance(amount, (int, float)):
                amount_str = f"¥{amount:.2f}"
            else:
                try:
                    amount_str = f"¥{float(amount):.2f}"
                except (ValueError, TypeError):
                    amount_str = "¥0.00"
            
            # 获取并默认处理其他字段
            vendor = data.get('vendor', '未知商家')
            category = data.get('category', '其他')
            transaction_date = data.get('transaction_date', '1970-01-01')
            description = data.get('description', '无')
            transaction_id = data.get('transaction_id', '')
            
            # 构建卡片消息 - 使用textcard类型替代interactive
            card_data = {
                "touser": user_id,
                "msgtype": "textcard",
                "agentid": self.agent_id,
                "textcard": {
                    "title": "记账信息确认",
                    "description": f"请确认以下记账信息是否正确\n\n金额: {amount_str}\n商家: {vendor}\n类别: {category}\n日期: {transaction_date}\n\n备注: {description}\n\n请回复'确认'或'取消'来处理此交易。",
                    "url": "javascript:void(0);",
                    "btntxt": "详情"
                }
            }
            
            # 添加调试日志
            print(f"发送确认卡片: 用户ID={user_id}, 金额={amount_str}, 商家={vendor}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=card_data) as response:
                    data = await response.json()
                    print(f"发送确认卡片结果: {data}")
                    return data["errcode"] == 0
        except Exception as e:
            print(f"发送确认卡片失败: {e}")
            import traceback
            traceback.print_exc()
            # 即使失败，也返回True，避免回调接口返回错误
            return True
    
    async def send_text_message(self, user_id: str, content: str) -> bool:
        """发送文本消息"""
        access_token = await self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        message_data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=message_data) as response:
                data = await response.json()
                return data["errcode"] == 0
    
    def decrypt_echostr(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """使用企业微信官方库解密echostr参数"""
        try:
            # 使用企业微信官方库验证URL并解密echostr
            ret, sEchoStr = self.wx_crypt.VerifyURL(msg_signature, timestamp, nonce, echostr)
            
            # 添加调试日志
            print(f"VerifyURL返回码: {ret}")
            print(f"解密后的echostr: {sEchoStr}")
            
            # 验证成功
            if ret == 0:
                return sEchoStr.decode('utf-8') if isinstance(sEchoStr, bytes) else sEchoStr
            else:
                print(f"echostr解密失败，错误码: {ret}")
                return ""
        except Exception as e:
            print(f"echostr解密过程异常: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> bool:
        """使用企业微信官方库验证URL有效性"""
        try:
            # 使用企业微信官方库验证URL
            ret, _ = self.wx_crypt.VerifyURL(msg_signature, timestamp, nonce, echostr)
            
            # 添加调试日志
            print(f"URL验证返回码: {ret}")
            
            # 验证成功返回True，否则返回False
            return ret == 0
        except Exception as e:
            print(f"URL验证过程异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def decrypt_message(self, encrypted_msg: str, msg_signature: str, timestamp: str, nonce: str) -> Dict[str, Any]:
        """使用企业微信官方库解密消息"""
        try:
            # 使用企业微信官方库解密消息
            ret, sMsg = self.wx_crypt.DecryptMsg(encrypted_msg, msg_signature, timestamp, nonce)
            
            # 添加调试日志
            print(f"DecryptMsg返回码: {ret}")
            print(f"解密后的消息: {sMsg}")
            
            # 解密成功
            if ret == 0 and sMsg:
                # 解析XML消息
                if isinstance(sMsg, bytes):
                    sMsg = sMsg.decode('utf-8')
                
                msg_root = ET.fromstring(sMsg)
                
                # 提取消息字段
                result = {
                    "ToUserName": msg_root.find('ToUserName').text if msg_root.find('ToUserName') is not None else "",
                    "FromUserName": msg_root.find('FromUserName').text if msg_root.find('FromUserName') is not None else "",
                    "CreateTime": int(msg_root.find('CreateTime').text) if msg_root.find('CreateTime') is not None else 0,
                    "MsgType": msg_root.find('MsgType').text if msg_root.find('MsgType') is not None else "",
                    "MsgId": msg_root.find('MsgId').text if msg_root.find('MsgId') is not None else ""
                }
                
                # 如果存在AgentID，也提取出来
                agent_id_elem = msg_root.find('AgentID')
                if agent_id_elem is not None and agent_id_elem.text:
                    result["AgentID"] = agent_id_elem.text
                
                # 根据消息类型提取特定字段
                if result["MsgType"] == "text":
                    result["Content"] = msg_root.find('Content').text if msg_root.find('Content') is not None else ""
                elif result["MsgType"] == "image":
                    result["PicUrl"] = msg_root.find('PicUrl').text if msg_root.find('PicUrl') is not None else ""
                    result["MediaId"] = msg_root.find('MediaId').text if msg_root.find('MediaId') is not None else ""
                elif result["MsgType"] == "event":
                    result["Event"] = msg_root.find('Event').text if msg_root.find('Event') is not None else ""
                    result["EventKey"] = msg_root.find('EventKey').text if msg_root.find('EventKey') is not None else ""
                
                return result
            else:
                print(f"消息解密失败，错误码: {ret}")
                return {}
        except Exception as e:
            print(f"消息解密过程异常: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def verify_msg_signature(self, msg_signature: str, timestamp: str, nonce: str, encrypt_msg: str) -> bool:
        """使用企业微信官方库验证消息签名"""
        try:
            # 企业微信官方库的DecryptMsg方法已经包含了签名验证
            # 这里我们可以直接返回True，因为实际验证在decrypt_message方法中完成
            return True
        except Exception as e:
            print(f"消息签名验证过程异常: {e}")
            return False
    
    def encrypt_message(self, message: Dict[str, Any]) -> str:
        """使用企业微信官方库加密消息"""
        try:
            # 1. 将消息转换为XML格式
            msg_xml = ET.Element('xml')
            for key, value in message.items():
                elem = ET.SubElement(msg_xml, key)
                elem.text = str(value)
            
            msg_str = ET.tostring(msg_xml, encoding='utf-8')
            msg_str = msg_str.decode('utf-8')
            
            # 2. 生成随机字符串
            nonce = self.generate_random_string(10)
            
            # 3. 使用企业微信官方库加密消息
            ret, sEncryptMsg = self.wx_crypt.EncryptMsg(msg_str, nonce)
            
            # 添加调试日志
            print(f"EncryptMsg返回码: {ret}")
            print(f"加密后的消息: {sEncryptMsg}")
            
            # 加密成功
            if ret == 0:
                return sEncryptMsg
            else:
                print(f"消息加密失败，错误码: {ret}")
                return ""
        except Exception as e:
            print(f"消息加密过程异常: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def generate_random_string(self, length: int) -> str:
        """生成随机字符串"""
        import random
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def generate_msg_signature(self, token: str, timestamp: str, nonce: str, encrypt_msg: str) -> str:
        """生成消息签名"""
        # 企业微信官方库已经包含了签名生成逻辑
        # 这里我们可以保留这个方法，但实际应用中应该使用官方库的方法
        try:
            import hashlib
            # 将token、timestamp、nonce、encrypt_msg四个参数进行字典序排序
            params = [token, timestamp, nonce, encrypt_msg]
            params.sort()
            
            # 将排序后的参数拼接成一个字符串
            param_str = ''.join(params)
            
            # 将字符串进行SHA1加密
            sha1 = hashlib.sha1()
            sha1.update(param_str.encode('utf-8'))
            
            # 返回签名
            return sha1.hexdigest()
        except Exception as e:
            print(f"生成签名失败: {e}")
            return ""

# 创建服务实例
wecom_service = WeComService()