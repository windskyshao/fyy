# -- coding: utf-8 --
"""假的 LINE webhook：模擬使用者傳訊息，檢查機器人回什麼。"""
import base64
import json

from conftest import ADMIN_UID, FEEDBACK_TOKEN, FakeResponse, load_contract, sign

INTEL_URL = 'https://map.windsky-sky.com/api/intel/line'
INTEL = load_contract('landmap_intel_line.json')


def _put_report(db, key, text, at='2026-11-14 06:30'):
    payload = json.dumps({'text': text, 'at': at}, ensure_ascii=False)
    db.save_app_file(key, base64.b64encode(payload.encode('utf-8')).decode(), '2026-11-14T06:30:05')


# ── webhook 本身 ──
def test_bad_signature_is_rejected(client, line):
    body = json.dumps({'destination': 'Ubot', 'events': []})
    r = client.post('/callback', data=body, headers={'X-Line-Signature': sign(body, 'someone-elses-secret')})
    assert r.status_code == 400
    assert line.replies == []


def test_empty_event_list_ok(client):
    body = json.dumps({'destination': 'Ubot', 'events': []})
    assert client.post('/callback', data=body, headers={'X-Line-Signature': sign(body)}).status_code == 200


# ── 一般指令 ──
def test_install_command_replies_with_install_link(say, line):
    for word in ('安裝', '安裝連結'):
        assert say(word).status_code == 200
    assert len(line.reply_texts) == 2
    assert all('https://fyy-l8a3.onrender.com/install' in t for t in line.reply_texts)
    assert line.pushes == []            # 用回覆，不吃推播額度


def test_my_id_command(say, line):
    say('我的ID', uid='Uabc123')
    assert 'Uabc123' in line.reply_texts[0]


def test_map_command_replies_with_card(say, line):
    say('地圖')
    msg = line.replies[0][1][0]
    assert msg.alt_text == '阿生地圖'


# ── 管理員：檢查 / 守門員 ──
def test_check_shows_watch_and_daily_report(say, line, db):
    _put_report(db, 'landmap_watch_report', '守門員內容')
    _put_report(db, 'landmap_daily_report', '每日檢查內容')
    say('檢查', uid=ADMIN_UID)
    reply = line.reply_texts[0]
    assert '守門員內容' in reply and '每日檢查內容' in reply
    assert reply.index('守門員內容') < reply.index('每日檢查內容')
    assert '更新於 2026-11-14 06:30' in reply


def test_watch_command_shows_only_watch_report(say, line, db):
    _put_report(db, 'landmap_watch_report', '守門員內容')
    _put_report(db, 'landmap_daily_report', '每日檢查內容')
    say('守門員', uid=ADMIN_UID)
    reply = line.reply_texts[0]
    assert '守門員內容' in reply and '每日檢查內容' not in reply


def test_check_with_nothing_stored(say, line):
    say('檢查', uid=ADMIN_UID)
    assert '最近沒有需要注意的狀況' in line.reply_texts[0]


def test_check_cuts_very_long_report(say, line, db):
    _put_report(db, 'landmap_watch_report', '長' * 6000)
    say('守門員', uid=ADMIN_UID)
    reply = line.reply_texts[0]
    assert '太長截斷' in reply and len(reply) < 5000        # LINE 單則上限 5000 字


def test_check_is_silent_for_non_admin(say, line, db):
    """報告含監控地號，非管理員問了要完全沒反應。"""
    _put_report(db, 'landmap_daily_report', '機密')
    for word in ('檢查', '守門員', '報告', '系統'):
        assert say(word, uid='Ustranger').status_code == 200
    assert line.replies == [] and line.pushes == []


def test_quota_command_is_silent_for_non_admin(say, line):
    say('用量', uid='Ustranger')
    assert line.replies == []


# ── 最新行情情報：綁定與轉傳 ──
def test_bind_code_is_sent_to_landmap(say, line, net):
    net.add(INTEL_URL, FakeResponse(200, INTEL['responses']['ok_bind']))
    say('綁定 123456', uid='Utestuser')
    assert net.calls_to(INTEL_URL)[0]['json'] == INTEL['bind']['json']     # 送出去的內容跟範例一字不差
    assert line.reply_texts[0].startswith('✅ 綁定好了')


def test_bind_without_space_also_works(say, line, net):
    net.add(INTEL_URL, FakeResponse(200, INTEL['responses']['ok_bind']))
    say('綁定123456')
    assert net.calls_to(INTEL_URL)[0]['json']['code'] == '123456'


def test_bind_failure_shows_reason(say, line, net):
    net.add(INTEL_URL, FakeResponse(200, {'status': 'ERROR', 'msg': '綁定碼過期'}))
    say('綁定 123456')
    assert line.reply_texts == ['綁定失敗：綁定碼過期']


def test_bind_when_landmap_unreachable(say, line, net):
    import requests
    net.add(INTEL_URL, requests.exceptions.ConnectionError('down'))
    assert say('綁定 123456').status_code == 200
    assert line.reply_texts[0].startswith('綁定失敗：')


def test_bind_ignored_in_group_chat(say, line, net):
    """綁定只在一對一聊天處理，群組裡不可以把碼送出去。"""
    say('綁定 123456', source_type='group')
    assert net.calls_to(INTEL_URL) == []


def test_bind_falls_back_to_push_when_reply_token_expired(say, line, net):
    """Render 剛睡醒時 reply_token 常已過期(TTL 30 秒),reply 會失敗;
    這時改用 push 讓使用者仍能收到綁定結果,避免「什麼都看不到」。"""
    net.add(INTEL_URL, FakeResponse(200, INTEL['responses']['ok_bind']))
    line.reply_error = Exception('Invalid reply token')      # 模擬 reply_token 過期
    assert say('綁定 123456', uid='Utestuser').status_code == 200
    assert line.reply_texts == []                             # reply 失敗,沒存進 replies
    assert len(line.pushes) == 1                              # 改用 push
    to, msgs = line.pushes[0]
    assert to == 'Utestuser'
    assert msgs[0].text.startswith('✅ 綁定好了')


def test_bind_failure_shows_reason_and_still_uses_push_on_reply_fail(say, line, net):
    """綁定失敗(地圖那邊回 ERROR) + reply 又過期 → 失敗訊息也要靠 push 送到。"""
    net.add(INTEL_URL, FakeResponse(200, {'status': 'ERROR', 'msg': '綁定碼過期'}))
    line.reply_error = Exception('Invalid reply token')
    say('綁定 123456', uid='Utestuser')
    assert line.push_texts == ['綁定失敗：綁定碼過期']


def test_forwarded_deal_is_saved_and_summarised(say, line, net):
    def landmap(call):
        if call['json']['action'] == 'check':
            return FakeResponse(200, {'status': 'OK', 'email': 'ming@example.com'})
        return FakeResponse(200, INTEL['responses']['ok_item'])
    net.add(INTEL_URL, landmap)
    say('情報：光華一路100號 成交 3,200萬')
    sent = [c['json'] for c in net.calls_to(INTEL_URL)]
    assert sent[0] == INTEL['check']['json']
    assert sent[1] == INTEL['add']['json']            # 開頭的「情報：」會先拿掉
    reply = line.reply_texts[0]
    assert '已存成最新行情情報' in reply
    assert '高雄市苓雅區光華一路100號' in reply
    assert '成交 3,200萬' in reply
    assert 'lat=22.609800&lng=120.317700' in reply
    assert line.pushes == []


def test_explicit_intel_from_unbound_user_gets_bind_instructions(say, line, net):
    net.add(INTEL_URL, FakeResponse(200, INTEL['responses']['not_bound']))
    say('情報 某某大樓成交')
    assert '還沒綁定阿生地圖帳號' in line.reply_texts[0]
    assert len(net.calls_to(INTEL_URL)) == 1          # 只問有沒有綁定，沒有送內容


def test_intel_empty_result(say, line, net):
    def landmap(call):
        if call['json']['action'] == 'check':
            return FakeResponse(200, {'status': 'OK'})
        return FakeResponse(200, INTEL['responses']['empty'])
    net.add(INTEL_URL, landmap)
    say('情報 今天天氣不錯')
    assert '看不出成交價或位置' in line.reply_texts[0]


def test_intel_money_formatting():
    import app as bot
    assert bot._intel_wan(32000000) == '3,200萬'
    assert bot._intel_wan(100000000) == '1億'
    assert bot._intel_wan(123450000) == '1億2,345萬'
    assert bot._intel_wan(35000) == '4萬'
