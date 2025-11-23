FROM python:3.11-slim

WORKDIR /app

# Install services
RUN apt-get update && apt-get install -y \
    curl \
    openssh-server \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH with weak settings
RUN mkdir -p /var/run/sshd && \
    echo 'root:password123' | chpasswd && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "PermitEmptyPasswords yes" >> /etc/ssh/sshd_config

# Configure Redis without authentication
RUN mkdir -p /etc/redis && \
    echo "bind 0.0.0.0" > /etc/redis/redis.conf && \
    echo "protected-mode no" >> /etc/redis/redis.conf && \
    echo "port 6379" >> /etc/redis/redis.conf

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create simple startup script
RUN echo '#!/bin/bash' > /start.sh && \
    echo 'service ssh start' >> /start.sh && \
    echo 'redis-server /etc/redis/redis.conf &' >> /start.sh && \
    echo 'python /app/app.py' >> /start.sh && \
    chmod +x /start.sh

EXPOSE 5000 22 6379

ENV FLASK_RUN_PORT=5000

CMD ["/start.sh"]