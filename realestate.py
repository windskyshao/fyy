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

_RE_ADDR = re.compile(r"(路|街|大道|巷|弄|段)\s*[0-9０-９一二三四五六七八九十]{0,12}\s*[0-9０-９一二三四五六七八九十]+\s*號")
_RE_SECT = re.compile(r"[一-龥]{1,6}段\s*[0-9０-９]")                                      # 「X段+數字」= 地籍地號特徵
_RE_LANDNO = re.compile(r"([一-龥]{1,4}[區鄉鎮市])?\s*([一-龥]{1,6}段)\s*([0-9０-９]+(?:[-‐－][0-9０-９]+)?)")
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
    # 「X段+數字」且沒有建物門牌號（把「地號」二字排除後不含「號」）＝ 地號查詢（免打「地號」二字）
    if _RE_SECT.search(t) and "號" not in t.replace("地號", ""):
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


def _parse_landno(t):
    """從「(高雄市)大寮區山子頂段2442(地號)」抽出 (city, tn, sect, no)。先去縣市前綴，再抓行政區/段/號。"""
    s = t.strip()
    city = None
    cm = re.match(r"^\s*([一-龥]{1,3}[縣市])", s)   # 先剝掉縣市，避免把「高雄市」的「市」誤當行政區
    if cm:
        city = _city_from_name(cm.group(1))
        s = s[cm.end():]
    m = _RE_LANDNO.search(s)
    if not m:
        return None
    tn = (m.group(1) or "").strip()
    sect = m.group(2)
    no = _full2half(m.group(3)).replace("‐", "-").replace("－", "-")
    return (city or "E", tn, sect, no)


def _resolve(text):
    """輸入 → (title, lat, lng, city_code)。地號（X段+數字）只走 landlocate；否則走地址。"""
    t = text.strip()
    # 地號查詢：有「X段+數字」且沒有建物門牌號 → 只用地號定位，不 fallback 到地址（避免亂定位到不相干路口）
    if _RE_SECT.search(t) and "號" not in t.replace("地號", ""):
        p = _parse_landno(t)
        if p and p[1]:                         # 必須有行政區才能定位（landlocate 需要鄉鎮市區）
            city, tn, sect, no = p
            d = _get("/api/landlocate", city=city, tn=tn, a=f"{sect}{no}地號")
            if d and d.get("status") == "OK" and d.get("lat"):
                return (f"{tn}{sect}{no}", d["lat"], d["lng"], city)
        return None                            # 地號查無 / 缺行政區 → 交上層回提示，不改猜地址
    # 地址查詢
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


_ZNAME = {"住": "住宅區", "商": "商業區", "工": "工業區", "農": "農業區", "其他": "其他分區"}


def _cat_of(p):
    """實價登錄類別（同前端 lvrCatOf）：土地 / 住宅大樓 / 華廈 / 公寓 / 套房 / 透天厝 / 店面 /
    辦公商業大樓 / 工廠 / 廠辦 / 倉庫 / 農舍 / 其他。"""
    if (p.get("tg") or "") == "土地":
        return "土地"
    ty = p.get("ty") or ""
    return re.split(r"[(（]", ty)[0] if ty else (p.get("tg") or "其他")


def _zclass(s):
    """使用分區字串 → 住/商/工/農/其他 大類。實價登錄只分到這五類（沒有第幾種層級），故只能大類配對。"""
    s = s or ""
    if "商" in s:
        return "商"
    if "工" in s:
        return "工"
    if "住" in s:
        return "住"
    if "農" in s:
        return "農"
    return "其他"


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

    # ── 周邊實價：依「查詢標的的類別」配對 ──
    #   地號(土地) → 只配土地，且同分區大類(住/商/工/農/其他；實價登錄無「第幾種」層級)，非都市配使用分區
    #   地址(建物) → 抓該門牌自己成交過的型態(self)，配同型態建物(住宅大樓/透天/…各別)；無成交可判→顯示各類建物
    #   同類不足時，才以鄰近的其他墊底
    is_land = bool(_RE_SECT.search(text)) and ("號" not in text.replace("地號", ""))
    nb_params = dict(city=city, lat=lat, lng=lng, r=1000, grouped=1)
    if is_land:
        pp = _parse_landno(text)
        if pp:
            nb_params.update(kind="land", sect=pp[2], landno=pp[3])
    else:
        nb_params.update(kind="bldg", door=title)
    nearby = _get("/api/lvr_nearby", **nb_params) or {}
    items = nearby.get("items") or []
    self_rec = nearby.get("self") or {}
    total = nearby.get("total") or 0

    if is_land:
        tz = _zclass(zone_txt or self_rec.get("zn") or self_rec.get("nz"))
        lands = [it for it in items if _cat_of(it) == "土地"]
        same = [it for it in lands if _zclass(it.get("zn") or it.get("nz")) == tz]
        picked = same + [it for it in lands if it not in same]
        match_label = "土地／" + _ZNAME.get(tz, tz)
    else:
        tgt = _cat_of(self_rec) if self_rec else ""
        blds = [it for it in items if _cat_of(it) != "土地"]
        if tgt and tgt not in ("土地", "其他"):
            same = [it for it in blds if _cat_of(it) == tgt]
            picked = same + [it for it in blds if it not in same]
            match_label = tgt
        else:
            picked = blds
            match_label = "各類建物" + ("（該門牌無成交可判型態）" if not tgt else "")

    lvr_rows = []
    for it in picked[:5]:
        lvr_rows.append({
            "a": _short_addr(it.get("a", "")),
            "up": _unit_wan(it.get("up")),
            "ym": _roc_ym(it.get("dt")),
            "ty": _cat_of(it),
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
        body.append({"type": "text", "text": f"📊 周邊實價 · {match_label}", "size": "sm", "color": "#8c4de6", "weight": "bold", "margin": "lg"})
        body.append({"type": "text", "text": f"（同類 {len(lvr_rows)} 筆，附近共 {total} 筆）", "size": "xs", "color": "#aaaaaa"})
        for row in lvr_rows:
            body.append({"type": "box", "layout": "vertical", "margin": "sm", "spacing": "none", "contents": [
                {"type": "box", "layout": "baseline", "contents": [
                    {"type": "text", "text": row["a"], "size": "sm", "color": "#333333", "flex": 5, "wrap": True},
                    {"type": "text", "text": row["up"], "size": "sm", "color": "#e74c3c", "flex": 3, "align": "end", "weight": "bold"},
                ]},
                {"type": "text", "text": f"{row['ty']}　{row['ym']}", "size": "xs", "color": "#999999"},
            ]})

    # 深連結回我們自己的地圖：帶座標+門牌 → 自動落點、帶出建號/周邊實價/使用分區
    maplink = f"{LANDMAP}/?lat={lat}&lng={lng}&door={urllib.parse.quote(title)}"
    contents = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "contents": body, "paddingAll": "16px"},
        "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
            {"type": "button", "style": "primary", "color": "#e67e22", "height": "sm",
             "action": {"type": "uri", "label": "📍 在地圖上看（建號/實價）", "uri": maplink}},
            {"type": "text", "text": "資料：內政部地籍/實價登錄 · landmap", "size": "xs", "color": "#aaaaaa", "align": "center", "wrap": True},
        ], "paddingAll": "12px"},
    }
    return (f"房地查詢：{title}", contents)
