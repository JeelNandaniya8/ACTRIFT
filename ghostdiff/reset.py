"""Explicit reset protocol for independently disposable local test servers."""
from http.client import HTTPConnection, HTTPException
from urllib.parse import urlsplit

RESET_PATH = "/_ghostdiff/reset"

def reset_target(url):
    if not isinstance(url,str) or any(ord(c)<=32 or ord(c)==127 for c in url):
        raise ValueError("Invalid reset target")
    u=urlsplit(url)
    if u.scheme!="http" or u.hostname not in ("127.0.0.1","::1") or u.username is not None or u.password is not None or u.port is None or not 1<=u.port<=65535:
        raise ValueError("Reset requires explicit numeric loopback HTTP addresses with ports")
    return u.hostname,u.port

def reset_backend(url):
    host,port=reset_target(url)
    conn=HTTPConnection(host,port,timeout=3)
    try:
        # Direct connection: no proxy, credentials, user-provided path or redirects.
        conn.request("POST",RESET_PATH,body=b"",headers={"Content-Length":"0"})
        response=conn.getresponse()
        if response.status!=204:
            return False
        return True
    except (OSError,HTTPException):
        return False
    finally:
        conn.close()
