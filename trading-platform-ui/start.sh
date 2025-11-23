#!/bin/bash

# Start SSH
service ssh start


# Start Redis
redis-server /etc/redis/redis.conf --daemonize yes


# Start Flask app
python app.py