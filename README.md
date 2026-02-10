# Proxy Server on AWS (Python + Multithreading + Semaphore)

A custom HTTP/HTTPS proxy server built using Python sockets and deployed on an AWS EC2 instance.
The proxy sits between the user and the internet, forwards requests, blocks selected domains, manages concurrent users using OS synchronization concepts, and runs as a background Linux service.

---

## 📌 Project Overview

This project demonstrates how a real proxy server works internally:

* Accepts client web requests
* Forwards them to target websites
* Returns responses back to users
* Supports HTTP and HTTPS
* Blocks restricted domains
* Handles multiple users using threads
* Limits concurrency using semaphore
* Uses mutex for safe logging
* Runs as a Linux background service using systemctl
* Deployed on AWS EC2

---

## 🧠 Key Concepts Implemented

### Networking

* Socket programming
* HTTP request forwarding
* HTTPS tunneling using CONNECT
* Client-server architecture

### Operating Systems

* Multithreading
* Semaphore (limit active clients)
* Mutex (safe logging & counters)
* Critical section handling
* Idle timeout management

### Cloud & Deployment

* AWS EC2 instance
* SSH secure remote access
* systemd service management
* Public & private IP networking

---

## 🏗️ Architecture

User Browser
↓
Proxy Server (AWS EC2)
↓
Internet Websites

Control channel:

Laptop → SSH → AWS → Proxy

---

## ⚙️ Features

* HTTP request forwarding
* HTTPS secure tunneling
* Domain blocking (Facebook, Instagram, etc.)
* Activity logging
* Queue tracking (Active vs Waiting users)
* Idle timeout auto-release
* Multithreaded request handling
* Background execution using systemctl

---

## 📁 Project Files

| File          | Purpose                      |
| ------------- | ---------------------------- |
| server.py     | Main proxy implementation    |
| proxy.service | Linux systemd service config |
| proxy.log     | Runtime activity logs        |

---

## 🔐 AWS Setup Steps

### 1. Create EC2 instance

* Choose Ubuntu
* Create new key pair → download `.pem`

### 2. Connect using SSH

```
ssh -i proxy-key.pem ubuntu@<public-ip>
```

### 3. Upload server.py

```
nano server.py
```

Paste proxy code.

---

## 🚀 Running Proxy Manually

```
python3 server.py
```

Runs until terminal closes.

---

## ⚙️ Running as Background Service

Create service file:

```
sudo nano /etc/systemd/system/proxy.service
```

Add:

```
[Unit]
Description=Python Proxy Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/ubuntu/server.py
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

Enable and start:

```
sudo systemctl daemon-reexec
sudo systemctl enable proxy
sudo systemctl start proxy
```

---

## 🧪 Testing Proxy

From local machine:

```
curl -x http://<public-ip>:8080 http://example.com
```

HTTPS test:

```
curl -x http://<public-ip>:8080 https://example.com
```

Blocked site test:

```
curl -x http://<public-ip>:8080 http://facebook.com
```

---

## 📊 Logs

View live activity:

```
sudo journalctl -u proxy -f
```

Log file:

```
tail -f proxy.log
```

Shows:

* Active clients
* Waiting queue
* Allowed requests
* Blocked requests
* Timeout releases

---

## 🔄 Request Flow

1. Browser sends request to proxy
2. Proxy accepts connection
3. Semaphore checks available slot
4. Thread created
5. Block list checked
6. HTTP forwarded OR HTTPS tunneled
7. Response returned
8. Connection closed
9. Semaphore released

---

## 🎓 Learning Outcomes

This project demonstrates real-world concepts:

* Computer Networks
* Operating Systems
* Cloud Computing
* Cybersecurity basics
* System-level programming
* Service deployment

---

## 📈 Future Enhancements

* Web dashboard for analytics
* Request caching
* Intrusion detection
* Traffic monitoring graphs
* Load balancing support

---

## 👨‍💻 Author

Proxy Server built as a learning project combining OS, networking, and cloud deployment to understand how real internet gateways operate.
