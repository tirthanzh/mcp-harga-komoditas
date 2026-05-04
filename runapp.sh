#!/bin/bash

# 2. Export ke Environment Variable
export HTTP_PROXY="$PROXY_URL"
export HTTPS_PROXY="$PROXY_URL"
export http_proxy="$PROXY_URL"
export https_proxy="$PROXY_URL"

export NO_PROXY="localhost,127.0.0.1,10.1.64.1,10.255.255.9"
export no_proxy="localhost,127.0.0.1,10.1.64.1,10.255.255.9"

echo "Proxy set ke: $PROXY_URL"
echo "Menjalankan script Python..."

python main.py