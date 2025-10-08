# 使用官方的 Python 3.10 slim 版本作为基础环境
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制所有项目文件到容器的 /app 目录下
COPY . /app

# 设置环境变量，告诉 Python 模块的搜索路径
ENV PYTHONPATH=/app

# 安装所有 Python 依赖，使用国内源加速
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 容器启动时要执行的命令
# 注意：这里的端口号应与 docker-compose.yml 中后端服务暴露的端口一致
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
