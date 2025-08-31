# SmartBookkeeper - 智能记账机器人后端服务

SmartBookkeeper 是一个基于 FastAPI 的智能记账机器人后端服务，它能够通过企业微信接收用户发送的图片消息，直接使用大语言模型识别图片中的信息并提取结构化的 JSON 记账数据，最后向用户发送一个交互式卡片进行信息确认。用户确认后，数据将被存入数据库，用户可以通过 Web 页面查看和修改自己的记账记录。

## 功能特点

- 通过企业微信接收用户发送的图片消息
- 直接使用大语言模型识别图片中的信息并提取结构化的记账数据
- 向用户发送交互式卡片进行信息确认
- 提供带有时效性 JWT Token 的 Web 页面，供用户查看和修改记账记录
- 使用 SQLite 数据库存储数据
- 基于 FastAPI 和 SQLAlchemy 2.0 的异步模式构建

## 技术栈

- **框架**: FastAPI
- **数据库**: SQLite (使用 SQLAlchemy 2.0 的异步模式)
- **认证**: JWT Token
- **外部服务**: 企业微信 API、大语言模型 API
- **前端**: Bootstrap 5、JavaScript

## 项目结构

```
SmartBookkeeper/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用主文件
│   ├── config.py            # 配置文件
│   ├── database.py          # 数据库配置
│   ├── models.py            # ORM 模型
│   ├── schemas.py           # Pydantic 数据模型
│   ├── crud.py              # CRUD 操作
│   ├── security.py          # 安全与认证
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       ├── wecom.py     # 企业微信相关 API
│   │       ├── transactions.py  # 交易记录相关 API
│   │       └── auth.py      # 认证相关 API
│   ├── services/
│   │   ├── wecom_service.py     # 企业微信服务封装
│   │   ├── ocr_service.py       # OCR 服务封装
│   │   └── ai_service.py        # AI 服务封装
│   ├── templates/
│   │   └── index.html       # 前端页面模板
│   └── static/              # 静态文件目录
├── requirements.txt         # 项目依赖
├── .env.example            # 环境变量示例
└── README.md               # 项目说明
```

## 安装与运行

### 1. 克隆项目

```bash
git clone <repository-url>
cd SmartBookkeeper
```

### 2. 创建虚拟环境

```bash
python -m venv venv
```

### 3. 激活虚拟环境

- Windows:

```bash
venv\Scripts\activate
```

- Linux/Mac:

```bash
source venv/bin/activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 初始化数据库

运行数据库初始化脚本，创建数据库表并添加示例数据：

```bash
python init_db.py
```

### 6. 配置环境变量

复制 `.env.example` 文件为 `.env`，并填入相应的配置：

```bash
copy .env.example .env
```

然后编辑 `.env` 文件，填入以下配置：

```
# Database
DATABASE_URL=sqlite+aiosqlite:///./smart_bookkeeper.db

# WeChat Work Configuration
WECOM_CORP_ID=ww1234567890abcdef
WECOM_SECRET=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456
WECOM_TOKEN=your_custom_token_string
WECOM_AES_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG

# AI Service Configuration
AI_API_KEY=sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdef

# JWT Configuration
JWT_SECRET_KEY=a_very_secure_random_string_for_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### 环境变量详细说明

##### 1. 数据库配置

```
DATABASE_URL=sqlite+aiosqlite:///./smart_bookkeeper.db
```

**说明**：指定数据库连接URL。

**示例值**：`sqlite+aiosqlite:///./smart_bookkeeper.db`

**获取方法**：
- 默认使用SQLite数据库，数据库文件将保存在项目根目录下的`smart_bookkeeper.db`文件中
- 如需使用其他数据库（如MySQL、PostgreSQL），请修改为相应格式，例如：
  - MySQL: `mysql+aiomysql://用户名:密码@localhost/数据库名`
  - PostgreSQL: `postgresql+asyncpg://用户名:密码@localhost/数据库名`

##### 2. 企业微信配置

```
WECOM_CORP_ID=ww1234567890abcdef
WECOM_SECRET=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456
WECOM_TOKEN=your_custom_token_string
WECOM_AES_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG
```

**说明**：企业微信应用配置参数，用于与企业微信API交互。

**获取方法**：
1. 登录[企业微信管理后台](https://work.weixin.qq.com/)
2. 进入「应用管理」→「应用」，创建或选择一个应用
3. 在应用详情页面获取「企业ID」(CorpID)
4. 在「应用管理」页面获取「Secret」(企业应用的凭证密钥)
5. 在「开发者接口」页面配置「接收消息」的「Token」和「EncodingAESKey」

##### 3. AI服务配置

```
AI_API_KEY=sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdef
```

**说明**：大语言模型服务的API密钥，用于直接识别图片中的信息并提取结构化的记账数据。

**获取方法**：
1. 选择一个大语言模型服务提供商（如OpenAI、百度文心一言、阿里云通义千问等）
2. 注册账号并创建API密钥

**常用AI服务提供商**：
- [OpenAI](https://platform.openai.com/)（推荐使用GPT-4V模型，支持图片识别）
- [百度文心一言](https://yiyan.baidu.com/)
- [阿里云通义千问](https://qianwen.aliyun.com/)

##### 5. JWT配置

```
JWT_SECRET_KEY=a_very_secure_random_string_for_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**说明**：JWT（JSON Web Token）配置参数，用于用户认证和授权。

**获取方法**：
- `JWT_SECRET_KEY`：应使用随机生成的字符串，可以使用以下命令生成：
  ```bash
  openssl rand -hex 32
  ```
- `JWT_ALGORITHM`：默认使用HS256算法，一般不需要修改
- `ACCESS_TOKEN_EXPIRE_MINUTES`：设置Token过期时间（分钟），根据安全需求调整

#### 安全注意事项

1. **不要将`.env`文件提交到版本控制系统**（如Git），它应包含在`.gitignore`文件中
2. **定期更换API密钥和Token**，特别是生产环境
3. **使用强密码和随机字符串**作为JWT_SECRET_KEY
4. **根据安全需求调整ACCESS_TOKEN_EXPIRE_MINUTES**，建议不要设置过长
5. **在生产环境中使用环境变量或密钥管理服务**，而不是直接使用.env文件

### 7. 运行应用

```bash
python -m uvicorn app.main:app --reload
```

或者直接运行 `app/main.py`：

```bash
python app/main.py
```

应用将在 `http://localhost:8000` 上运行。

## API 文档

启动应用后，可以通过以下地址访问 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 使用说明

### 1. 企业微信配置

1. 在企业微信后台创建应用，获取 `corp_id`、`secret`、`token` 和 `aes_key`。
2. 配置应用的回调 URL 为 `http://your-domain.com/api/v1/wecom/callback`。

### 2. AI 服务配置

1. 选择一个大语言模型服务提供商（如 OpenAI、百度文心一言等）。
2. 注册账号并获取 API Key。
3. 在 `app/services/ocr_service.py` 中修改 API 调用代码，以适应所选 AI 服务的 API。

### 4. 使用 Web 界面

1. 获取访问 Token：
   - 可以通过调用 `/api/v1/auth/token/{user_id}` 获取测试 Token。
   - 实际应用中，Token 应在用户发起会话时生成。
2. 访问 Web 界面：`http://localhost:8000/?token={your_token}`
3. 在 Web 界面中，可以查看、编辑和删除记账记录。

## 开发说明

### 数据库模型

项目使用 SQLAlchemy 2.0 的异步模式，主要模型为 `Transaction`，包含以下字段：

- `id`: 主键
- `user_id`: 用户企业微信 ID
- `amount`: 金额
- `vendor`: 商家
- `category`: 类别
- `transaction_date`: 交易日期
- `description`: 摘要
- `image_url`: 原始凭证图片 URL
- `created_at`: 创建时间
- `updated_at`: 更新时间

### API 端点

- 企业微信相关：
  - `GET /api/v1/wecom/callback`: 用于企业微信服务器验证 URL
  - `POST /api/v1/wecom/callback`: 接收用户消息，处理图片消息并启动记账流程
- 交易记录相关：
  - `GET /api/v1/transactions/`: 获取当前用户的记账列表
  - `PUT /api/v1/transactions/{transaction_id}`: 修改记录
  - `DELETE /api/v1/transactions/{transaction_id}`: 删除记录
- 认证相关：
  - `POST /api/v1/auth/token`: 根据 user_id 生成一个临时 token

### 外部服务封装

- `wecom_service.py`: 封装与企业微信 API 的交互逻辑
- `ocr_service.py`: 封装直接使用大语言模型识别图片中的信息并提取结构化记账数据的逻辑

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至 [your-email@example.com](mailto:your-email@example.com)