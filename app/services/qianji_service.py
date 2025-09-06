from typing import Dict, Any, Optional
from urllib.parse import quote
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class QianjiService:
    """钱迹服务，用于生成钱迹记账链接"""
    
    def __init__(self):
        self.enabled = settings.QIANJI_ENABLED
        self.cate_choose = settings.QIANJI_CATE_CHOOSE
        
    def generate_qianji_url(self, transaction_data: Dict[str, Any]) -> str:
        """根据交易数据生成钱迹记账链接
        
        Args:
            transaction_data: 交易数据字典，包含amount, vendor, category, transaction_date, description等字段
            
        Returns:
            钱迹记账链接
        """
        try:
            # 钱迹API基础URL
            base_url = "qianji://publicapi/addbill?"
            
            # 构建参数
            params = []
            
            # type参数：0支出，1收入，默认为支出
            # 由于图片识别无法确定是收入还是支出，默认设为支出
            params.append(f"type=0")
            
            # money参数：金额
            amount = transaction_data.get("amount")
            if amount is not None:
                params.append(f"money={amount}")
            else:
                logger.warning("交易数据中缺少金额信息")
                return ""
            
            # time参数：交易时间，格式为yyyy-MM-dd HH:mm:ss
            transaction_date = transaction_data.get("transaction_date")
            if transaction_date:
                # 如果只有日期，添加默认时间
                if " " not in transaction_date:
                    transaction_date += " 12:00:00"
                params.append(f"time={transaction_date}")
            
            # remark参数：备注
            description = transaction_data.get("description") or transaction_data.get("vendor")
            if description:
                params.append(f"remark={quote(description)}")
            
            # catename参数：分类名称
            category = transaction_data.get("category")
            if category and not self.cate_choose:
                params.append(f"catename={quote(category)}")
            
            # catechoose参数：是否弹出分类选择面板
            if self.cate_choose:
                params.append("catechoose=1")
                # 可以添加主题参数，默认为黑色主题
                # params.append("catetheme=light")  # 白色主题
                # params.append("catetheme=auto")   # 自动适应系统主题
            
            # 拼接URL
            url = base_url + "&".join(params)
            
            logger.info(f"生成的钱迹记账链接: {url}")
            return url
            
        except Exception as e:
            logger.error(f"生成钱迹记账链接失败: {e}")
            return ""
    
    def format_transaction_data(self, recognition_result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化识别结果，适配钱迹需要的格式
        
        Args:
            recognition_result: 图片识别结果
            
        Returns:
            格式化后的交易数据
        """
        try:
            # 提取关键字段
            amount = recognition_result.get("amount")
            vendor = recognition_result.get("vendor")
            category = recognition_result.get("category")
            transaction_date = recognition_result.get("transaction_date")
            description = recognition_result.get("description")
            
            # 构建返回数据
            formatted_data = {
                "type": 0,  # 默认为支出
                "money": amount,
                "time": transaction_date,
                "remark": description or vendor,
                "category": category,
                "catechoose": self.cate_choose
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"格式化交易数据失败: {e}")
            return {}

# 创建服务实例
qianji_service = QianjiService()