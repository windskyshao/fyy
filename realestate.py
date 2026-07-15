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
from collections import Counter

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


def _total_wan(pr):
    """總價元 → 『X,XXX萬』（同地圖卡片 lvrTotalWan）。"""
    try:
        pr = float(pr)
    except (TypeError, ValueError):
        return ""
    return f"{round(pr/10000):,}萬" if pr else ""


_FLOOR_IN_RE = re.compile(r"號\s*([0-9]+|[一二兩三四五六七八九十百]+)\s*樓(?:\s*[之\-‐－–—]\s*([0-9]+|[一二三四五六七八九十]+))?")   # 之X／-X／各式連字號都當戶號
_CN_F = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _extract_floor(text):
    """從輸入門牌抽『樓層』字串（如 7樓 / 五樓之3），供標題顯示。"""
    m = _FLOOR_IN_RE.search(_full2half(text or ""))
    if not m:
        return ""
    s = m.group(1) + "樓"
    if m.group(2):
        s += "之" + m.group(2)
    return s


def _floor_num(s):
    """樓層字串(中文/阿拉伯、『樓』或『層』) → 樓層數，供比對本標的樓層。"""
    s = _full2half(s or "")
    m = re.search(r"([0-9]+|[一二兩三四五六七八九十]+)\s*[樓層]", s)
    if not m:
        return None
    t = m.group(1)
    if t.isdigit():
        return int(t)
    if t == "十":
        return 10
    if t.startswith("十"):
        return 10 + _CN_F.get(t[1:], 0)
    if "十" in t:
        a, _, b = t.partition("十")
        return _CN_F.get(a, 0) * 10 + (_CN_F.get(b, 0) if b else 0)
    return _CN_F.get(t)


_UNIT_RE = re.compile(r"[樓層]\s*[之\-‐－–—]\s*([0-9]+|[一二兩三四五六七八九十]+)")


def _unit_num(s):
    """門牌『之X』的戶號（阿拉伯/中文、之或各式連字號皆可）→ 數字；無戶號則 None。"""
    s = _full2half(s or "")
    m = _UNIT_RE.search(s)
    if not m:
        return None
    t = m.group(1)
    if t.isdigit():
        return int(t)
    if t == "十":
        return 10
    if t.startswith("十"):
        return 10 + _CN_F.get(t[1:], 0)
    if "十" in t:
        a, _, b = t.partition("十")
        return _CN_F.get(a, 0) * 10 + (_CN_F.get(b, 0) if b else 0)
    return _CN_F.get(t)


def _bkey(a):
    """門牌取到『號』為止＝同一棟(去樓層/之X)。"""
    a = _short_addr(a)
    m = re.match(r"^(.*?[0-9]+號)", a)
    return m.group(1) if m else a


def _dtnum(it):
    return int(_full2half(str(it.get("dt") or "0")) or "0")


def _latest(rows):
    return max(rows, key=_dtnum) if rows else None


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
    """使用分區字串 → 住/商/工/農/其他 大類。"""
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


_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_NUM_CN = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七"}


def _zlevel(s):
    """使用分區(取土地明細細分區 zd) → (大類, 層級)。層級抓「第X種」——住/商才有;工(甲乙丙)/農無層級→None。
    例：'都市：其他:第五種住宅區'→('住',5)、'特定第五種住宅區（特定住5）'→('住',5)、'乙種工業區'→('工',None)。"""
    cls = _zclass(s)
    m = re.search(r"第([一二三四五六七八九十])(?:之[一二三四五六七八九十])?種", s or "")
    return cls, (_CN_NUM.get(m.group(1)) if m else None)


def _zshort(cls, lvl):
    if cls in ("住", "商") and lvl in _NUM_CN:
        return cls + _NUM_CN[lvl]          # 住五 / 商三
    return {"住": "住宅區", "商": "商業區", "工": "工業區", "農": "農業區"}.get(cls, "其他分區")


# 特殊交易(與前端 LVR_SP_RE 一致)：備註含真正影響價格的關鍵字才算(排除中性的預售/分件登記)
_SP_RE = re.compile(r"親友|員工|共有人|股東|特殊關係|債務|抵償|拍賣|法拍|增建|加蓋|夾層|未登記|外推|瑕疵|凶|事故|急買|急賣|贈與|交換|毛胚|清水|協議價購|標讓售|標售|僅車位|車位交易|農作物|地上權|保留地|傢俱|家俱|裝潢|設備費|家電")


def _is_special(nt):
    return bool(nt and _SP_RE.search(nt))


def query(text):
    """地址／地號 → (alt_text, flex) 或 None。"""
    got = _resolve(text)
    if not got:
        return None
    title, lat, lng, city = got
    is_land = bool(_RE_SECT.search(text)) and ("號" not in text.replace("地號", ""))
    return _card(title, lat, lng, city, text, is_land)


def name_query(text):
    """社區名／公寓大廈名 關鍵字 → (alt_text, flex) 或 None（給非地址/地號的名稱用，放最後才試）。"""
    t = (text or "").strip()
    if len(t) < 2:
        return None
    d = _get("/api/community_search", q=t, city="E")
    results = (d or {}).get("results") or []
    if not results:
        return None
    best = next((r for r in results if (r.get("name") or "") == t), None)   # 完全同名優先
    if not best:
        if len(t) < 3:
            return None                                                     # 太短的部分比對不採，避免亂配
        best = results[0]                                                   # 否則取最相符/最熱門者
    return _card(best["name"], best["lat"], best["lng"], best.get("city", "E"), best["name"], False)


def _card(title, lat, lng, city, text, is_land):
    """由（名稱/門牌 ＋ 座標）組實價卡。text 供抽樓層/地號；is_land 決定土地或建物配對。"""
    floor = _extract_floor(text)                       # 保留使用者輸入的樓層（地理編碼會丟樓層）
    title_disp = (title + floor) if (floor and "樓" not in title) else title

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

    subj_key = _bkey(title)
    rep = None                                        # 代表戶(同棟)：供社區/屋齡/樓高與型態判斷；本標的門牌則另需精準比對
    if is_land:
        # 目標分區：優先用標的自己土地明細的細分區(zd)，否則用 luzzone，再退主檔粗分
        tcls, tlvl = _zlevel(self_rec.get("zd") or zone_txt or self_rec.get("zn") or self_rec.get("nz"))
        lands = [it for it in items if _cat_of(it) == "土地"]

        def _score(it):
            icls, ilvl = _zlevel(it.get("zd") or it.get("zn") or it.get("nz"))
            d = it.get("dist", 99999)
            if icls != tcls:
                return (2, 0, d)                       # 不同大類→最後(商不配住)
            if tlvl and ilvl:
                return (0, abs(ilvl - tlvl), d)         # 同大類：層級差越小越前(住五→住五=0,住四/六=1…遞減)
            return (1 if (tlvl or ilvl) else 0, 0, d)   # 工/農無層級→同類即可;一邊有層級一邊無→次之
        pool = sorted(lands, key=_score)
        match_label = "土地／" + _zshort(tcls, tlvl)
        selfrow = self_rec if (self_rec and _cat_of(self_rec) == "土地") else None   # 土地：以 API 地號身分比對＝本標的
        rep = selfrow
    else:
        blds = [it for it in items if _cat_of(it) != "土地"]
        sameb = [it for it in blds if _bkey(it.get("a")) == subj_key]
        # 本標的門牌成交：認『同號＋同樓層＋同戶(之X)』精準比對；查無(如該戶全新未成交)＝不硬湊別戶充當本標的
        selfrow = None
        if floor and sameb:
            fnum = _floor_num(floor)
            unum = _unit_num(floor)                                # 輸入指定的戶號(之X)；沒指定則 None
            def _is_subj(it):
                a = it.get("a") or ""
                if _floor_num(it.get("fl") or a) != fnum:
                    return False
                return _unit_num(a) == unum if unum is not None else True   # 有指定戶→需精準同戶；沒指定→同樓層即可
            selfrow = _latest([it for it in sameb if _is_subj(it)])
        # 代表戶：精準本標的 → 同棟最常見住宅型態(避1樓店面帶偏)最新一筆 → API self（供社區/屋齡/樓高與型態）
        rep = selfrow
        if not rep and sameb:
            modal = Counter(_cat_of(it) for it in sameb).most_common(1)[0][0]
            rep = _latest([it for it in sameb if _cat_of(it) == modal]) or _latest(sameb)
        if not rep and self_rec and _cat_of(self_rec) != "土地":
            rep = self_rec
        tgt = _cat_of(rep) if rep else ""
        if tgt and tgt not in ("土地", "其他"):
            pool = [it for it in blds if _cat_of(it) == tgt]
            match_label = tgt
        else:
            pool = blds
            match_label = "各類建物" + ("（該門牌無成交可判型態）" if not tgt else "")

    # 第一筆＝本標的門牌成交；其餘依成交日新→舊
    def _samerec(x, y):
        return bool(x) and bool(y) and x.get("a") == y.get("a") and x.get("dt") == y.get("dt") and x.get("up") == y.get("up")
    rest = sorted([it for it in pool if not _samerec(it, selfrow)], key=_dtnum, reverse=True)
    ordered = ([selfrow] if selfrow else []) + rest

    lvr_rows = []
    for i, it in enumerate(ordered[:6]):
        flr = _full2half(it.get("fl") or "").strip()
        ftt = _full2half(it.get("ft") or "").strip()
        rm, hl, bt = it.get("rm"), it.get("hl"), it.get("bt")
        lvr_rows.append({
            "a": _short_addr(it.get("a", "")),
            "com": (it.get("com") or "").strip(),                                      # 社區名稱
            "up": _unit_wan(it.get("up")),
            "tot": _total_wan(it.get("pr")),                                          # 總價
            "pg": (f"{_full2half(str(it.get('pg')))}坪" if it.get("pg") else ""),      # 坪數
            "age": (f"屋齡{it.get('age')}" if it.get("age") not in (None, "") else ""),  # 屋齡
            "fl": (flr + ("／" + ftt if ftt else "")) if flr else ftt,                 # 樓層/總樓
            "layout": (f"{rm or 0}房{hl or 0}廳{bt or 0}衛" if (rm or hl or bt) else ""),  # 格局
            "pk": (it.get("pk") or "").strip(),                                       # 車位類別
            "pkn": it.get("pkn"),                                                     # 車位數量(landmap 由「交易筆棟數」拆出)
            "ym": _roc_ym(it.get("dt")),
            "ty": _cat_of(it),
            "sp": _is_special(it.get("nt")),      # 特殊交易(親友/員工/債務抵償…)→標紅
            "self": bool(selfrow) and i == 0,     # 本標的門牌
        })

    # ── 組 Flex ──
    body = [
        {"type": "text", "text": "🏠 房地查詢", "size": "sm", "color": "#e67e22", "weight": "bold"},
        {"type": "text", "text": title_disp, "size": "lg", "weight": "bold", "wrap": True, "margin": "sm", "color": "#222222"},
        {"type": "separator", "margin": "md"},
        {"type": "box", "layout": "vertical", "spacing": "sm", "margin": "md", "contents": []},
    ]
    info = body[3]["contents"]
    # 本標的：社區名稱／屋齡／總樓層（建物；來源＝本標的門牌成交，社區名再退社區API）
    if not is_land:
        s = rep or {}
        subj_com = (s.get("com") or "").strip()
        if not subj_com:
            subj_com = ((_get("/api/lvr_community", city=city, lat=lat, lng=lng) or {}).get("com") or "").strip()
        if subj_com:
            info.append(_line("社區", subj_com, "#8c4de6"))
    if landno_txt:
        info.append(_line("地號", landno_txt, "#1558b0"))
    if zone_txt:
        info.append(_line("使用分區", zone_txt, "#0f7d55"))
    if not is_land:
        agft = []
        if (rep or {}).get("age") not in (None, ""):
            agft.append(f"約{rep['age']}年")
        _ft = _full2half((rep or {}).get("ft") or "").strip()
        if _ft:
            agft.append(f"共{_ft}")
        if agft:
            info.append(_line("屋齡‧樓高", "　".join(agft), "#555555"))
    if not info:
        info.append({"type": "text", "text": "此點查無地號（可能在道路或範圍外）", "size": "sm", "color": "#999999", "wrap": True})

    if lvr_rows:
        body.append({"type": "separator", "margin": "lg"})
        body.append({"type": "text", "text": f"📊 周邊實價 · {match_label}", "size": "sm", "color": "#8c4de6", "weight": "bold", "margin": "lg"})
        _note = f"（同類 {len(lvr_rows)} 筆，附近共 {total} 筆" + ("；第一筆為本標的門牌" if selfrow else "；本戶查無成交，以下為周邊同類") + "）"
        body.append({"type": "text", "text": _note, "size": "sm", "color": "#555555", "wrap": True})
        for row in lvr_rows:
            top = [
                {"type": "text", "text": ("◉ " if row["self"] else "") + (row["a"] or "—"), "size": "sm", "color": ("#1558b0" if row["self"] else "#333333"), "flex": 6, "wrap": True, "weight": "bold"},
                {"type": "text", "text": row["up"], "size": "sm", "color": "#e74c3c", "flex": 4, "align": "end", "weight": "bold"},
            ]
            midL = (row["com"] + "｜" if row["com"] else "") + f"{row['ty']}　{row['ym']}" + ("　🔴特殊" if row["sp"] else "")
            mid = [{"type": "text", "text": midL, "size": "sm", "color": ("#e74c3c" if row["sp"] else "#555555"), "flex": 6, "wrap": True}]
            if row["tot"]:
                mid.append({"type": "text", "text": "總價 " + row["tot"], "size": "sm", "color": "#333333", "flex": 4, "align": "end", "weight": "bold"})
            if row["pkn"]:
                pk_disp = f"🅿{row['pkn']}位" + ("·" + row["pk"] if row["pk"] else "")   # 車位數量(+類別)
            elif row["pk"]:
                pk_disp = "🅿" + row["pk"]
            else:
                pk_disp = ""
            meta = "　".join(x for x in [row["pg"], row["age"], row["fl"], row["layout"], pk_disp] if x)
            rowbox = {"type": "box", "layout": "vertical", "margin": "md", "spacing": "xs", "contents": [
                {"type": "box", "layout": "baseline", "contents": top},
                {"type": "box", "layout": "baseline", "contents": mid},
            ]}
            if meta:
                rowbox["contents"].append({"type": "text", "text": meta, "size": "sm", "color": "#555555", "wrap": True})
            if row["self"]:
                rowbox.update({"backgroundColor": "#eef4ff", "cornerRadius": "6px", "paddingAll": "8px"})
            body.append(rowbox)

    # 深連結回我們自己的地圖：帶座標+門牌 → 自動落點；mode 讓地圖用「原查詢方式」呈現(地址→地址模式、地號→地籍模式)
    maplink = f"{LANDMAP}/?lat={lat}&lng={lng}&door={urllib.parse.quote(title_disp)}&mode={'sect' if is_land else 'addr'}"
    contents = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "contents": body, "paddingAll": "16px"},
        "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
            {"type": "button", "style": "primary", "color": "#e67e22", "height": "sm",
             "action": {"type": "uri", "label": "📍 在地圖上看（建號/實價）", "uri": maplink}},
            {"type": "text", "text": "資料：內政部地籍/實價登錄 · landmap", "size": "xs", "color": "#aaaaaa", "align": "center", "wrap": True},
        ], "paddingAll": "12px"},
    }
    return (f"房地查詢：{title_disp}", contents)
