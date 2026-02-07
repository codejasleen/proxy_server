import socket
import threading
import time
from datetime import datetime

HOST = "0.0.0.0"
PORT = 8080

client_semaphore = threading.Semaphore(5)

blocked_sites = {
    "facebook.com",
    "instagram.com"
}

CACHE = {}
CACHE_LOCK = threading.Lock()
CACHE_TTL = 60

LOG_FILE = "proxy.log"
LOG_LOCK = threading.Lock()


def log_request(client_ip, host, protocol):
    with LOG_LOCK:
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now()} | {client_ip} | {host} | {protocol}\n")


def tunnel_data(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except:
        pass


def handle_https(client_socket, addr, request_line):
    try:
        target = request_line.split(" ")[1]
        host, port = target.split(":")
        port = int(port)

        if host in blocked_sites:
            client_socket.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            return

        log_request(addr[0], host, "HTTPS")

        print("HTTPS tunnel to:", host, port, flush=True)

        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((host, port))

        client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

        t1 = threading.Thread(target=tunnel_data, args=(client_socket, remote_socket))
        t2 = threading.Thread(target=tunnel_data, args=(remote_socket, client_socket))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        remote_socket.close()

    except Exception as e:
        print("HTTPS Error:", e, flush=True)


def handle_http(client_socket, addr, request):
    try:
        request_str = request.decode(errors="ignore")
        request_line = request_str.split("\r\n")[0]

        cache_key = request_line

        with CACHE_LOCK:
            if cache_key in CACHE:
                response, timestamp = CACHE[cache_key]
                if time.time() - timestamp < CACHE_TTL:
                    print("CACHE HIT:", cache_key, flush=True)
                    client_socket.sendall(response)
                    return
                else:
                    del CACHE[cache_key]

        host = None
        for line in request_str.split("\r\n"):
            if line.lower().startswith("host:"):
                host = line.split(":", 1)[1].strip()
                break

        if not host:
            return

        if host in blocked_sites:
            client_socket.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            return

        log_request(addr[0], host, "HTTP")
        print("HTTP request to:", host, flush=True)

        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.settimeout(15)
        remote_socket.connect((host, 80))
        remote_socket.sendall(request)

        full_response = b""

        while True:
            data = remote_socket.recv(4096)
            if not data:
                break
            full_response += data

        remote_socket.close()

        if full_response:
            client_socket.sendall(full_response)

            with CACHE_LOCK:
                CACHE[cache_key] = (full_response, time.time())
                print("CACHE STORED:", cache_key, flush=True)

    except Exception as e:
        print("HTTP Error:", e, flush=True)


def handle_client(client_socket, addr):
    print("Waiting for semaphore...", flush=True)
    client_semaphore.acquire()

    print("Entered critical section:", addr, flush=True)

    try:
        request = client_socket.recv(4096)
        if not request:
            return

        request_line = request.decode(errors="ignore").split("\r\n")[0]

        if request_line.startswith("CONNECT"):
            handle_https(client_socket, addr, request_line)
        else:
            handle_http(client_socket, addr, request)

    except Exception as e:
        print("Client error:", e, flush=True)

    finally:
        client_socket.close()
        client_semaphore.release()
        print("Connection closed + semaphore released:", addr, flush=True)


proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
proxy.bind((HOST, PORT))
proxy.listen(100)

print("HTTPS + HTTP Proxy running on port", PORT, flush=True)

while True:
    client_socket, addr = proxy.accept()
    thread = threading.Thread(target=handle_client, args=(client_socket, addr))
    thread.start()
