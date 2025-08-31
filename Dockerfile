# 使用Python 3.11作为基础镜像
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 从构建阶段复制安装的依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制项目文件
COPY . .

# 创建log目录（用于图片识别服务访问临时图片文件）
RUN mkdir -p log

# 暴露端口
EXPOSE 8000

# 设置环境变量，使用.env文件
ENV ENV_FILE=.env

# 启动命令
# 如果.env文件存在，则加载其中的环境变量
CMD ["sh", "-c", "if [ -f $ENV_FILE ]; then export $(cat $ENV_FILE | xargs); fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]