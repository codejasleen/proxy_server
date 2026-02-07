# Cloud Proxy Server (HTTP + HTTPS)

A multithreaded cloud proxy server built using Python and deployed on AWS.

Features:
- HTTP forwarding
- HTTPS tunneling
- Multithreading
- Semaphore-based concurrency control
- Domain blocking
- Logging
- In-memory caching
- Deployed using systemd on AWS

Architecture:

Client → AWS Proxy → Target Server → Response → Client

The target server sees AWS IP, not client IP.

---

## How to run locally

python server.py

---

## How to use deployed proxy

curl -x http://<AWS_PUBLIC_IP>:8080 https://api.ipify.org

Expected output:
AWS IP address

---

## Deployment

Running on AWS EC2 Ubuntu using systemd service.
