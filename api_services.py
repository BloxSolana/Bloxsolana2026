# File: api_services.py (Cập nhật phần gọi API MK)

MK_API_KEY   = os.getenv("MK_API_KEY", "").strip()
MK_API_URL   = os.getenv("MK_API_URL", "https://api.number1.vn/v1").strip()
NP_API_KEY   = os.getenv("NP_API_KEY", "").strip()
SLVN_API_KEY = os.getenv("SLVN_API_KEY", "").strip()

async def api_request(method, endpoint, json_data=None, params=None, api_type="MK"):
    url = ""
    headers = {}
    if api_type == "MK":
        base_url = MK_API_URL.rstrip('/')
        url = f"{base_url}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {MK_API_KEY}", "Content-Type": "application/json"}
    elif api_type == "NP":
        url = f"https://api.number2.vn/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {NP_API_KEY}", "Content-Type": "application/json"}
    elif api_type == "SLVN":
        url = f"https://api.slvn.vn/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {SLVN_API_KEY}", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, json=json_data, params=params, headers=headers, timeout=20) as resp:
                text = await resp.text()
                try:
                    data = await resp.json()
                except:
                    data = {"raw": text}
                if resp.status >= 400:
                    return None, f"HTTP {resp.status}: {text}"
                return data, None
        except Exception as e:
            return None, str(e)
            
