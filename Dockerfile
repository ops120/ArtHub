FROM python:3.9-slim

LABEL maintainer="ops120"
LABEL description="白嫖大师 - 通用 AI 客户端"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY src/ ./src/
COPY templates/ ./templates/
COPY conf/ ./conf/
COPY moark_image_edit_ui.py ./

RUN mkdir -p outputs logs data

EXPOSE 11111

ENV PYTHONUNBUFFERED=1
ENV LANG=zh_CN.UTF-8

CMD ["python", "moark_image_edit_ui.py", "--server-port", "11111", "--server-name", "0.0.0.0"]
