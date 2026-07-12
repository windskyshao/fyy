# -*- coding: utf-8 -*-
"""阿生生 LINE bot：房地查詢（像「房地小賴」）。
使用者直接打「地址」或「地號」→ 打 landmap 後端 API → 回一張 Flex 卡：
  地號、使用分區、周邊實價(前幾筆)、在地圖上看按鈕。
資料來源：landmap 雲端主機 map.windsky-sky.com（免費地籍/實價；面積/公告現值/建蔽容積因海外主機被地理封鎖，暫不含）。
設計原則：每段查詢各自容錯（拿不到就略過該段，不讓整張卡失敗）；字級用 sm~lg，不用 xs。
"""
import re
import requests
import urllib.parse

LANDMAP = "https://map.windsky-sky.com"
TIMEOUT = 12

# 內政部門牌/地號縣市 → landmap 實價縣市碼（目前實價只有這三縣市）
_CITY_CODE = {"高雄": "E", "臺南": "D", "台南": "D", "屏東": "T"}
# 地政事務所代碼前綴 → 縣市碼（parcel 回的 office 如 EA/EB…、DA…、TA…）
_OFFICE_CITY = {"E": "E", "D": "D", "T": "T"}

_RE_ADDR = re.compile(r"(路|街|大道|巷|弄)\s*[0-9０-９一二三四五六七八九十]{0,12}\s*[0-9０-９一二三四五六七八九十]+\s*號")
_RE_LANDNO = re.compile(r"([一-龥]{1,4}[區鄉鎮市])?\s*([一-龥]{1,8}段)\s*([0-9０-９]+(?:[-‐－][0-9０-９]+)?)\s*(?:地號)?")
_RE_CITY_TOWN = re.compile(r"[一-龥]{1,3}[縣市][一-龥]{1,4}[區鄉鎮市]")


def looks_like_realestate(text):
    """判斷是否為地址/地號查詢（放在股票中文搜尋之前，但條件要嚴，避免誤撞一般詞）。"""
    t = (text or "").strip()
    if len(t) < 4 or len(t) > 40:
        return False
    if _RE_ADDR.search(t):                       # 有「…路/街…N號」
        return True
    if _RE_CITY_TOWN.search(t) and "號" in t:     # 有「X縣市X區…號」
        return True
    if "地號" in t and "段" in t:                  # 明講地號
        return True
    m = _RE_LANDNO.search(t)
    if m and m.group(1):                          # 「X區X段123」含行政區才夠明確
        return True
    return False


def _full2half(s):
    return "".join(chr(ord(c) - 0xFEE0) if "０" <= c <= "９" else c for c in (s or ""))


def _get(path, **params):
    try:
        url = LANDMAP + path + "?" + urllib.parse.urlencode(params)
        r = requests.get(url, timeout=TIMEOUT)
        return r.json()
    except Exception:
        return None


def _city_from_name(name):
    for k, code in _CITY_CODE.items():
        if name.startswith(k) or name.startswith("臺" + k[1:]) or k in name[:4]:
            return code
    return None


def _short_addr(a):
    """去掉「X縣市X區X里N鄰」前綴，讓門牌短一點好讀。"""
    a = _full2half(a or "")
    a = re.sub(r"^[一-龥]{1,3}[縣市]", "", a, count=1)
    a = re.sub(r"^[一-龥]{1,4}[區鄉鎮市]", "", a, count=1)
    a = re.sub(r"^[一-龥]{1,4}里", "", a, count=1)
    a = re.sub(r"^[0-9]{1,3}鄰", "", a, count=1)
    return a


def _unit_wan(up):
    return (f"{up/10000:.1f} 萬/坪") if up else "單價—"


def _roc_ym(dt):
    dt = _full2half(dt or "")
    if len(dt) >= 5 and dt[:3].isdigit():
        return f"{int(dt[:3])}年{int(dt[3:5])}月"
    return ""


def _resolve(text):
    """把使用者輸入轉成 (title, lat, lng, city_code)。地址走 /api/address；地號走 /api/landlocate。"""
    t = text.strip()
    # 先試地號（含行政區才好定位）
    m = _RE_LANDNO.search(t)
    if ("地號" in t or (m and m.group(1))) and m and m.group(2):
        tn = (m.group(1) or "").strip()
        sect = m.group(2)
        no = _full2half(m.group(3)).replace("‐", "-").replace("－", "-")
        a = f"{sect}{no}地號"
        # 縣市碼：輸入含縣市→用之，否則預設高雄 E（使用者主要在高雄）
        city = None
        cm = re.search(r"[一-龥]{1,3}[縣市]", t)
        if cm:
            city = _city_from_name(cm.group(0))
        city = city or "E"
        if not tn:
            return None  # 沒行政區難定位→交回地址流程/或回無法定位
        d = _get("/api/landlocate", city=city, tn=tn, a=a)
        if d and d.get("status") == "OK" and d.get("lat"):
            return (f"{tn}{sect}{no}", d["lat"], d["lng"], city)
    # 地址流程
    d = _get("/api/address", q=t)
    if d and d.get("results"):
        r = d["results"][0]
        if r.get("lat"):
            city = _city_from_name(r.get("name", "")) or "E"
            return (_short_addr(r.get("name", "")) or t, r["lat"], r["lng"], city)
    return None


def _line(label, value, vcolor="#333333"):
    return {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
        {"type": "text", "text": label, "size": "sm", "color": "#8c8c8c", "flex": 2},
        {"type": "text", "text": value, "size": "md", "color": vcolor, "flex": 5, "wrap": True, "weight": "bold"},
    ]}


def query(text):
    """回 (alt_text, flex_contents_dict) 或 None（查無/非房地）。"""
    got = _resolve(text)
    if not got:
        return None
    title, lat, lng, city = got

    # 地號
    parcel = _get("/api/parcel", lat=lat, lng=lng) or {}
    landno_txt = ""
    if parcel.get("status") == "OK" and parcel.get("sectName"):
        landno_txt = f"{parcel.get('sectName','')}{parcel.get('landNo','')}"

    # 使用分區（luzzone 訪客 API）
    zone_txt = ""
    z = _get("/api/luzzone", lat=lat, lng=lng) or {}
    if z.get("status") == "OK" and z.get("zone"):
        zone_txt = z.get("zone") + (f"（{z.get('short')}）" if z.get("short") else "")

    # 周邊實價（前 5 筆）
    lvr_rows = []
    nearby = _get("/api/lvr_nearby", city=city, lat=lat, lng=lng, r=400, n=5) or {}
    total = nearby.get("total") or 0
    for it in (nearby.get("items") or [])[:5]:
        lvr_rows.append({
            "a": _short_addr(it.get("a", "")),
            "up": _unit_wan(it.get("up")),
            "ym": _roc_ym(it.get("dt")),
            "ty": it.get("ty") or it.get("tg") or "",
        })

    # ── 組 Flex ──
    body = [
        {"type": "text", "text": "🏠 房地查詢", "size": "sm", "color": "#e67e22", "weight": "bold"},
        {"type": "text", "text": title, "size": "lg", "weight": "bold", "wrap": True, "margin": "sm", "color": "#222222"},
        {"type": "separator", "margin": "md"},
        {"type": "box", "layout": "vertical", "spacing": "sm", "margin": "md", "contents": []},
    ]
    info = body[3]["contents"]
    if landno_txt:
        info.append(_line("地號", landno_txt, "#1558b0"))
    if zone_txt:
        info.append(_line("使用分區", zone_txt, "#0f7d55"))
    if not info:
        info.append({"type": "text", "text": "此點查無地號（可能在道路或範圍外）", "size": "sm", "color": "#999999", "wrap": True})

    if lvr_rows:
        body.append({"type": "separator", "margin": "lg"})
        body.append({"type": "text", "text": f"📊 周邊實價（{min(len(lvr_rows),5)}／附近{total}筆）",
                     "size": "sm", "color": "#8c4de6", "weight": "bold", "margin": "lg"})
        for row in lvr_rows:
            body.append({"type": "box", "layout": "vertical", "margin": "sm", "spacing": "none", "contents": [
                {"type": "box", "layout": "baseline", "contents": [
                    {"type": "text", "text": row["a"], "size": "sm", "color": "#333333", "flex": 5, "wrap": True},
                    {"type": "text", "text": row["up"], "size": "sm", "color": "#e74c3c", "flex": 3, "align": "end", "weight": "bold"},
                ]},
                {"type": "text", "text": f"{row['ty']}　{row['ym']}", "size": "xs", "color": "#999999"},
            ]})

    gmap = f"https://www.google.com/maps?q={lat},{lng}"
    contents = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "contents": body, "paddingAll": "16px"},
        "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
            {"type": "button", "style": "primary", "color": "#e67e22", "height": "sm",
             "action": {"type": "uri", "label": "📍 在地圖上看", "uri": gmap}},
            {"type": "text", "text": "資料：內政部地籍/實價登錄 · landmap", "size": "xs", "color": "#aaaaaa", "align": "center", "wrap": True},
        ], "paddingAll": "12px"},
    }
    return (f"房地查詢：{title}", contents)
