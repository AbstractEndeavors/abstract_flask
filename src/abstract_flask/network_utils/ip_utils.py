from .imports import get_request_info,socket
def get_host_ip():
    try:
        # Attempt to connect to an Internet host in order to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        try:
            # Use a public DNS server address
            s.connect(("8.8.8.8", 80))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
    except Exception as e:
        print(f"Error obtaining IP: {e}")
        return '127.0.0.1'
def get_user_ip(req):
   user_ip = req.remote_addr
   return user_ip

def get_ip_addr(req=None,ip_addr=None):
    return get_request_info(req=req,
                         obj=ip_addr,
                         res_type='ip_addr')



