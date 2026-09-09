import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8001/api/sessions",
    method="OPTIONS",
    headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    }
)

try:
    with urllib.request.urlopen(req) as response:
        print("Status Code:", response.getcode())
        print("Headers:", response.headers)
except Exception as e:
    print("Error:", e)
    if hasattr(e, "headers"):
        print("Headers:", e.headers)
