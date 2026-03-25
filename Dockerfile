FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Patch MCP library: fix ClosedResourceError, add stream buffer, cleanup stale sessions, keepalive ping
COPY patches/sse.py /usr/local/lib/python3.12/site-packages/mcp/server/sse.py

COPY . .

ENV PORT=3000
EXPOSE 3000

CMD ["python", "server.py", "streamable-http"]
