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
    remote_socket = None
    try:
        # Parse the CONNECT request
        target = request_line.split(" ")[1]
        
        # Handle both "host:port" and just "host" formats
        if ":" in target:
            host, port = target.split(":")
            port = int(port)
        else:
            host = target
            port = 443  # Default HTTPS port
        
        print(f"[HTTPS] Request from {addr[0]} to {host}:{port}", flush=True)

        # Check if site is blocked
        if host in blocked_sites:
            error_msg = f"[HTTPS] Blocked site: {host}"
            print(error_msg, flush=True)
            client_socket.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\nSite blocked by proxy")
            return

        # Log the request
        log_request(addr[0], host, "HTTPS")

        # Try to resolve the hostname first
        try:
            import socket as sock_module
            resolved_ip = sock_module.gethostbyname(host)
            print(f"[HTTPS] Resolved {host} to {resolved_ip}", flush=True)
        except sock_module.gaierror as dns_error:
            error_msg = f"[HTTPS] DNS resolution failed for {host}: {dns_error}"
            print(error_msg, flush=True)
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\nDNS resolution failed")
            return

        # Create socket and set timeout
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.settimeout(10)  # 10 second timeout
        
        print(f"[HTTPS] Connecting to {host}:{port}...", flush=True)
        
        # Try to connect to the remote server
        try:
            remote_socket.connect((host, port))
            print(f"[HTTPS] Successfully connected to {host}:{port}", flush=True)
        except socket.timeout:
            error_msg = f"[HTTPS] Connection timeout to {host}:{port}"
            print(error_msg, flush=True)
            client_socket.sendall(b"HTTP/1.1 504 Gateway Timeout\r\n\r\nConnection timeout")
            return
        except ConnectionRefusedError:
            error_msg = f"[HTTPS] Connection refused by {host}:{port}"
            print(error_msg, flush=True)
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\nConnection refused")
            return
        except OSError as conn_error:
            error_msg = f"[HTTPS] Connection error to {host}:{port}: {conn_error}"
            print(error_msg, flush=True)
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\nConnection failed")
            return

        # Send success response to client
        client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        print(f"[HTTPS] Tunnel established for {host}:{port}", flush=True)

        # Remove timeout for data transfer
        remote_socket.settimeout(None)

        # Create bidirectional tunnel
        t1 = threading.Thread(target=tunnel_data, args=(client_socket, remote_socket))
        t2 = threading.Thread(target=tunnel_data, args=(remote_socket, client_socket))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        print(f"[HTTPS] Tunnel closed for {host}:{port}", flush=True)

    except ValueError as parse_error:
        error_msg = f"[HTTPS] Invalid CONNECT request format: {parse_error}"
        print(error_msg, flush=True)
        try:
            client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\nInvalid request format")
        except:
            pass
    except Exception as e:
        error_msg = f"[HTTPS] Unexpected error: {type(e).__name__}: {e}"
        print(error_msg, flush=True)
        try:
            client_socket.sendall(b"HTTP/1.1 500 Internal Server Error\r\n\r\nProxy error")
        except:
            pass
    finally:
        # Clean up remote socket
        if remote_socket:
            try:
                remote_socket.close()
            except:
                pass


def handle_http(client_socket, addr, request):
    remote_socket = None
    try:
        request_str = request.decode(errors="ignore")
        request_line = request_str.split("\r\n")[0]

        cache_key = request_line

        # Check cache first
        with CACHE_LOCK:
            if cache_key in CACHE:
                response, timestamp = CACHE[cache_key]
                if time.time() - timestamp < CACHE_TTL:
                    print(f"[HTTP] CACHE HIT: {cache_key}", flush=True)
                    client_socket.sendall(response)
                    return
                else:
                    del CACHE[cache_key]

        # Extract host from request
        host = None
        for line in request_str.split("\r\n"):
            if line.lower().startswith("host:"):
                host = line.split(":", 1)[1].strip()
                break

        if not host:
            print(f"[HTTP] No host header found in request from {addr[0]}", flush=True)
            client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\nNo host header")
            return

        # Check if site is blocked
        if host in blocked_sites:
            print(f"[HTTP] Blocked site: {host}", flush=True)
            client_socket.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\nSite blocked by proxy")
            return

        log_request(addr[0], host, "HTTP")
        print(f"[HTTP] Request from {addr[0]} to {host}", flush=True)

        # Create socket and connect
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.settimeout(15)
        
        try:
            remote_socket.connect((host, 80))
            print(f"[HTTP] Connected to {host}:80", flush=True)
        except socket.timeout:
            print(f"[HTTP] Connection timeout to {host}:80", flush=True)
            client_socket.sendall(b"HTTP/1.1 504 Gateway Timeout\r\n\r\nConnection timeout")
            return
        except socket.gaierror as dns_error:
            print(f"[HTTP] DNS resolution failed for {host}: {dns_error}", flush=True)
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\nDNS resolution failed")
            return
        except ConnectionRefusedError:
            print(f"[HTTP] Connection refused by {host}:80", flush=True)
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\nConnection refused")
            return
        except OSError as conn_error:
            print(f"[HTTP] Connection error to {host}:80: {conn_error}", flush=True)
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\nConnection failed")
            return

        # Send request
        remote_socket.sendall(request)

        # Receive response
        full_response = b""
        while True:
            data = remote_socket.recv(4096)
            if not data:
                break
            full_response += data

        remote_socket.close()
        remote_socket = None

        # Send response to client
        if full_response:
            client_socket.sendall(full_response)

            # Cache the response
            with CACHE_LOCK:
                CACHE[cache_key] = (full_response, time.time())
                print(f"[HTTP] CACHE STORED: {cache_key}", flush=True)
        else:
            print(f"[HTTP] Empty response from {host}", flush=True)

    except Exception as e:
        error_msg = f"[HTTP] Unexpected error: {type(e).__name__}: {e}"
        print(error_msg, flush=True)
        try:
            client_socket.sendall(b"HTTP/1.1 500 Internal Server Error\r\n\r\nProxy error")
        except:
            pass
    finally:
        if remote_socket:
            try:
                remote_socket.close()
            except:
                pass


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
