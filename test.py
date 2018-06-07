try:
    import httplib
except:
    import http.client as httplib

def have_internet():
    conn = httplib.HTTPConnection("www.google.com", timeout=5)
    try:
        conn.request("HEAD", "/")
        conn.close()
        print("TRUE")
        return True
    except:
        conn.close()
        print("FALSE")
        return False
have_internet()
