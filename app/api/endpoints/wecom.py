from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from app.database import get_db
from app.services.wecom_service import wecom_service
from app.services.image_recognition_service import image_recognition_service
from app.crud import create_transaction
from app.schemas import TransactionCreate
from app.config import settings
from app.security import create_access_token
from datetime import datetime, timedelta
import json
import logging
from urllib.parse import unquote

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/v1/wecom/callback")
async def verify_callback_url(
    request: Request,
    msg_signature: Optional[str] = Query(None, alias="msg_signature"),
    timestamp: Optional[str] = Query(None, alias="timestamp"),
    nonce: Optional[str] = Query(None, alias="nonce"),
    echostr: Optional[str] = Query(None, alias="echostr")
):
    """用于企业微信服务器验证URL"""
    try:
        # 获取查询参数
        query_params = request.query_params
        
        # 如果参数为空，尝试从查询参数中获取
        if not msg_signature:
            msg_signature = query_params.get("msg_signature")
        if not timestamp:
            timestamp = query_params.get("timestamp")
        if not nonce:
            nonce = query_params.get("nonce")
        if not echostr:
            echostr = query_params.get("echostr")
        
        # 检查必需参数
        if not all([msg_signature, timestamp, nonce, echostr]):
            # 记录缺少的参数
            missing_params = []
            if not msg_signature:
                missing_params.append("msg_signature")
            if not timestamp:
                missing_params.append("timestamp")
            if not nonce:
                missing_params.append("nonce")
            if not echostr:
                missing_params.append("echostr")
            
            logger.error(f"Missing required parameters: {missing_params}")
            logger.error(f"All query params: {dict(query_params)}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required parameters: {', '.join(missing_params)}"
            )
        
        # 对收到的请求做Urldecode处理
        msg_signature = unquote(msg_signature)
        timestamp = unquote(timestamp)
        nonce = unquote(nonce)
        echostr = unquote(echostr)
        
        # 使用企业微信官方库验证URL并解密echostr
        # 注意：这里不再需要单独调用verify_url方法，因为decrypt_echostr方法已经包含了验证逻辑
        msg = wecom_service.decrypt_echostr(msg_signature, timestamp, nonce, echostr)
        
        if msg:
            return PlainTextResponse(content=msg)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="URL verification failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_callback_url: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/api/v1/wecom/callback")
async def handle_wecom_message(
    request: Request,
    msg_signature: Optional[str] = Query(None, alias="msg_signature"),
    timestamp: Optional[str] = Query(None, alias="timestamp"),
    nonce: Optional[str] = Query(None, alias="nonce"),
    db: AsyncSession = Depends(get_db)
):
    """接收用户消息，处理图片消息并启动记账流程"""
    try:
        # 获取查询参数
        query_params = request.query_params
        
        # 如果参数为空，尝试从查询参数中获取
        if not msg_signature:
            msg_signature = query_params.get("msg_signature")
        if not timestamp:
            timestamp = query_params.get("timestamp")
        if not nonce:
            nonce = query_params.get("nonce")
        
        # 检查必需参数
        if not all([msg_signature, timestamp, nonce]):
            # 记录缺少的参数
            missing_params = []
            if not msg_signature:
                missing_params.append("msg_signature")
            if not timestamp:
                missing_params.append("timestamp")
            if not nonce:
                missing_params.append("nonce")
            
            logger.error(f"Missing required parameters: {missing_params}")
            logger.error(f"All query params: {dict(query_params)}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required parameters: {', '.join(missing_params)}"
            )
        
        # 对收到的请求做Urldecode处理
        msg_signature = unquote(msg_signature)
        timestamp = unquote(timestamp)
        nonce = unquote(nonce)
        
        # 获取请求体
        body = await request.body()
        
        # 解密消息 - 传递msg_signature, timestamp, nonce参数给decrypt_message方法
        message_data = wecom_service.decrypt_message(body.decode('utf-8'), msg_signature, timestamp, nonce)
        
        # 检查消息类型
        msg_type = message_data.get("MsgType")
        
        # 消息去重检查
        msg_id = message_data.get("MsgId")
        if msg_id and msg_id in processed_messages:
            # 如果消息已处理过，直接返回成功响应，避免重复处理
            logger.info(f"消息已处理过，跳过重复处理: msg_id={msg_id}")
            response_data = {"status": "success", "message": "Message already processed"}
            encrypted_response = wecom_service.encrypt_message(response_data)
            # 构建符合企业微信要求的XML响应格式
            xml_response = f"""<xml>
<Encrypt><![CDATA[{encrypted_response}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""
            return Response(content=xml_response, media_type="application/xml")
        
        # 记录已处理的消息ID
        if msg_id:
            processed_messages[msg_id] = datetime.now().isoformat()
            # 清理超过24小时的消息ID记录，防止内存泄漏
            current_time = datetime.now()
            expired_msgs = [mid for mid, mtime in processed_messages.items() 
                          if (current_time - datetime.fromisoformat(mtime)).total_seconds() > 86400]
            for mid in expired_msgs:
                del processed_messages[mid]
        
        if msg_type == "image":
            # 处理图片消息
            media_id = message_data.get("MediaId")
            user_id = message_data.get("FromUserName")
            
            # 下载图片
            image_data = await wecom_service.download_image(media_id)
            
            # 保存图片到log文件夹
            import os
            import time
            log_dir = "log"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 使用时间戳和用户ID作为文件名
            timestamp = int(time.time())
            filename = f"{log_dir}/{user_id}_{timestamp}.jpg"
            with open(filename, "wb") as f:
                f.write(image_data)
            logger.info(f"图片已保存到: {filename}")
            
            # 调用图片识别服务直接获取结构化的记账数据，传递图片路径避免重复保存
            recognition_result = await image_recognition_service.recognize_text(image_data, filename)
            
            # 检查图片识别是否成功
            if not recognition_result.get('success', True):  # 默认为True以兼容旧格式
                # 图片识别失败，向用户发送错误消息
                error_msg = recognition_result.get('error', '图片识别失败，无法识别图片中的文本')
                await wecom_service.send_text_message(user_id, f"识别失败：{error_msg}")
            else:
                # 检查是否启用了钱迹模式
                qianji_enabled = getattr(settings, 'QIANJI_ENABLED', False)
                
                if qianji_enabled and recognition_result.get('qianji_enabled', False):
                    # 钱迹模式已启用，直接返回识别结果和钱迹记账链接
                    qianji_url = recognition_result.get('qianji_url', '')
                    catechoose = recognition_result.get('catechoose', True)
                    
                    # 构建钱迹记账链接消息
                    if qianji_url:
                        if catechoose:
                            message = f"已识别记账信息，请点击链接记账：\n{qianji_url}"
                        else:
                            message = f"已识别记账信息，请点击链接记账（已跳过分类选择）：\n{qianji_url}"
                        await wecom_service.send_text_message(user_id, message)
                    else:
                        await wecom_service.send_text_message(user_id, "识别成功，但生成钱迹记账链接失败，请重试。")
                else:
                    # 普通模式，走原来的确认流程
                    # OCR识别成功，处理交易数据
                    transaction_data = recognition_result
                    
                    # 为交易数据添加当前时间作为默认交易日期
                    if 'transaction_date' not in transaction_data or not transaction_data['transaction_date']:
                        transaction_data['transaction_date'] = datetime.now().strftime('%Y-%m-%d')
                    
                    # 保存待确认的交易数据
                    transaction_timestamp = await save_pending_transaction(user_id, transaction_data)
                    
                    # 添加交易标识到数据中，用于后续确认
                    transaction_data['transaction_id'] = transaction_timestamp
                    
                    # 发送确认卡片
                    await wecom_service.send_confirmation_card(user_id, transaction_data)
            
            # 返回成功响应
            response_data = {"status": "success"}
            encrypted_response = wecom_service.encrypt_message(response_data)
            # 构建符合企业微信要求的XML响应格式
            xml_response = f"""<xml>
<Encrypt><![CDATA[{encrypted_response}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""
            return Response(content=xml_response, media_type="application/xml")
            
        elif msg_type == "text":
            # 处理文本消息
            content = message_data.get("Content")
            user_id = message_data.get("FromUserName")
            
            # 检查是否是确认消息
            if content.lower() == "确认" or content.lower() == "confirm":
                # 获取用户最新的待确认交易
                if user_id in pending_transactions and pending_transactions[user_id]:
                    # 获取最新的交易timestamp
                    latest_timestamp = max(pending_transactions[user_id].keys())
                    
                    # 确认交易并保存到数据库
                    success = await confirm_transaction(user_id, latest_timestamp, db)
                    
                    if success:
                        await wecom_service.send_text_message(user_id, "交易已确认，已记录到账本中。")
                    else:
                        await wecom_service.send_text_message(user_id, "确认失败，未找到对应的交易数据。")
                else:
                    await wecom_service.send_text_message(user_id, "未找到待确认的交易数据。")
            elif content.lower() == "取消" or content.lower() == "cancel":
                # 获取用户最新的待确认交易
                if user_id in pending_transactions and pending_transactions[user_id]:
                    # 获取最新的交易timestamp
                    latest_timestamp = max(pending_transactions[user_id].keys())
                    
                    # 从待确认列表中删除
                    if user_id in pending_transactions and latest_timestamp in pending_transactions[user_id]:
                        del pending_transactions[user_id][latest_timestamp]
                        
                        # 如果用户没有其他待确认交易，删除用户条目
                        if not pending_transactions[user_id]:
                            del pending_transactions[user_id]
                            
                await wecom_service.send_text_message(user_id, "交易已取消。")
            elif content == "菜单" or content.lower() == "menu":
                # 发送菜单选项
                menu_text = "请选择您需要的服务：\n1. 发送图片进行记账\n2. 查看账本\n3. 访问后台管理\n4. 帮助\n\n请回复对应数字或直接发送图片"
                await wecom_service.send_text_message(user_id, menu_text)
            elif content == "1":
                await wecom_service.send_text_message(user_id, "请发送包含消费信息的收据图片，我将为您自动识别并记账。")
            elif content == "2":
                # 这里可以添加查看账本的功能
                await wecom_service.send_text_message(user_id, "账本查看功能正在开发中，敬请期待。")
            elif content == "3":
                # 发送后台管理链接
                # 为用户生成一个临时token，有效期1小时
                token_data = {"sub": user_id}
                access_token = create_access_token(data=token_data, expires_delta=timedelta(hours=1))
                admin_url = f"{settings.PENETRATE_URL}/token/{access_token}"
                await wecom_service.send_text_message(user_id, f"后台管理页面：{admin_url}\n\n请使用浏览器打开链接进行管理操作。\n\n注意：链接有效期1小时，请尽快使用。")
            elif content == "4":
                help_text = "使用帮助：\n1. 发送包含消费信息的收据图片，系统将自动识别并记账\n2. 识别后会发送确认信息，回复'确认'或'取消'\n3. 回复'菜单'可查看所有可用功能\n4. 如有问题请联系管理员"
                await wecom_service.send_text_message(user_id, help_text)
            else:
                # 非预设内容，提供选择
                response_text = f"您发送的消息：'{content}' 不是预设指令。\n\n请选择您需要的操作：\n1. 发送图片进行记账\n2. 查看账本\n3. 访问后台管理\n4. 查看帮助\n\n请回复对应数字或发送'菜单'查看所有选项"
                await wecom_service.send_text_message(user_id, response_text)
            
            # 返回成功响应
            response_data = {"status": "success"}
            encrypted_response = wecom_service.encrypt_message(response_data)
            # 构建符合企业微信要求的XML响应格式
            xml_response = f"""<xml>
<Encrypt><![CDATA[{encrypted_response}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""
            return Response(content=xml_response, media_type="application/xml")
            
        elif msg_type == "event":
            # 处理事件消息
            event = message_data.get("Event")
            user_id = message_data.get("FromUserName")
            
            if event == "click":
                event_key = message_data.get("EventKey")
                
                # 处理卡片点击事件
                if event_key == "confirm":
                    # 获取用户最新的待确认交易
                    if user_id in pending_transactions and pending_transactions[user_id]:
                        # 获取最新的交易timestamp
                        latest_timestamp = max(pending_transactions[user_id].keys())
                        
                        # 确认交易并保存到数据库
                        success = await confirm_transaction(user_id, latest_timestamp, db)
                        
                        if success:
                            await wecom_service.send_text_message(user_id, "交易已确认，已记录到账本中。")
                        else:
                            await wecom_service.send_text_message(user_id, "确认失败，未找到对应的交易数据。")
                    else:
                        await wecom_service.send_text_message(user_id, "未找到待确认的交易数据。")
                elif event_key == "cancel":
                    # 获取用户最新的待确认交易
                    if user_id in pending_transactions and pending_transactions[user_id]:
                        # 获取最新的交易timestamp
                        latest_timestamp = max(pending_transactions[user_id].keys())
                        
                        # 从待确认列表中删除
                        if user_id in pending_transactions and latest_timestamp in pending_transactions[user_id]:
                            del pending_transactions[user_id][latest_timestamp]
                            
                            # 如果用户没有其他待确认交易，删除用户条目
                            if not pending_transactions[user_id]:
                                del pending_transactions[user_id]
                                
                    await wecom_service.send_text_message(user_id, "交易已取消。")
            
            # 返回成功响应
            response_data = {"status": "success"}
            encrypted_response = wecom_service.encrypt_message(response_data)
            # 构建符合企业微信要求的XML响应格式
            xml_response = f"""<xml>
<Encrypt><![CDATA[{encrypted_response}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""
            return Response(content=xml_response, media_type="application/xml")
            
        else:
            # 不支持的消息类型
            response_data = {"status": "unsupported message type"}
            encrypted_response = wecom_service.encrypt_message(response_data)
            # 构建符合企业微信要求的XML响应格式
            xml_response = f"""<xml>
<Encrypt><![CDATA[{encrypted_response}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""
            return Response(content=xml_response, media_type="application/xml")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in handle_wecom_message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# 临时存储交易数据的字典（实际应用中应使用Redis等）
# 格式: {user_id: {timestamp: transaction_data}}
pending_transactions = {}

# 临时存储已处理消息ID的集合，用于消息去重
# 格式: {msg_id: timestamp}
processed_messages = {}

async def save_pending_transaction(user_id: str, transaction_data: Dict[str, Any]):
    """保存待确认的交易数据"""
    timestamp = datetime.now().isoformat()
    
    if user_id not in pending_transactions:
        pending_transactions[user_id] = {}
    
    pending_transactions[user_id][timestamp] = transaction_data
    return timestamp

async def get_pending_transaction(user_id: str, timestamp: str) -> Optional[Dict[str, Any]]:
    """获取待确认的交易数据"""
    if user_id in pending_transactions and timestamp in pending_transactions[user_id]:
        return pending_transactions[user_id][timestamp]
    return None

async def confirm_transaction(user_id: str, timestamp: str, db: AsyncSession):
    """确认交易并保存到数据库"""
    transaction_data = await get_pending_transaction(user_id, timestamp)
    
    if not transaction_data:
        return False
    
    # 创建交易记录
    transaction = TransactionCreate(
        amount=transaction_data.get("amount"),
        vendor=transaction_data.get("vendor"),
        category=transaction_data.get("category"),
        transaction_date=datetime.fromisoformat(transaction_data.get("transaction_date")),
        description=transaction_data.get("description"),
        image_url=transaction_data.get("image_url")
    )
    
    # 保存到数据库
    await create_transaction(db, transaction, user_id)
    
    # 从待确认列表中删除
    if user_id in pending_transactions and timestamp in pending_transactions[user_id]:
        del pending_transactions[user_id][timestamp]
        
        # 如果用户没有其他待确认交易，删除用户条目
        if not pending_transactions[user_id]:
            del pending_transactions[user_id]
    
    return True