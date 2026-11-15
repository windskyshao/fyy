# -- coding: utf-8 --
"""介面範例測試：拿 tests/contracts 裡「其他程式實際會送的請求」來打 fyy。

這裡失敗＝fyy 跟阿生地圖 / 地籍便民系統講不通了。要改格式請先改範例，兩邊一起對。
"""
import base64
import json
import os

import pytest

from conftest import ADMIN_UID, load_contract

INBOUND = ['feedback_desktop.json', 'feedback_landmap.json', 'report_push_daily.json',
           'report_push_watch.json', 'cadastral_fail.json']


@pytest.mark.parametrize('name', INBOUND)
def test_inbound_sample_is_accepted(name, client, line, db, chart_dir):
    c = load_contract(name)
    r = client.open(c['path'], method=c['method'], headers=c['headers'],
                    data=json.dumps(c['json']).encode('utf-8'))
    exp = c['expect']
    assert r.status_code == exp['status'], r.get_data(as_text=True)

    if 'push_text_contains' in exp:
        assert [to for to, _ in line.pushes] == [ADMIN_UID]      # 只推給管理員一次
        text = line.push_texts[0]
        for piece in exp['push_text_contains']:
            assert piece in text
    if 'saved_key' in exp:
        assert list(db.files) == [exp['saved_key']]
        saved = json.loads(base64.b64decode(db.files[exp['saved_key']][0]).decode('utf-8'))
        assert saved['text'] == c['json']['text'].strip()
        assert saved['at'] == c['json']['at']
        assert line.pushes == []                                  # 只存不推，不吃推播額度
    if 'saved_files' in exp:
        folders = [d for d in os.listdir(chart_dir) if d.startswith('cadfail_')]
        assert len(folders) == 1
        assert sorted(os.listdir(chart_dir / folders[0])) == sorted(exp['saved_files'])


@pytest.mark.parametrize('name', INBOUND)
def test_inbound_sample_needs_token(name, client, line, db):
    """同一則請求，權杖錯就一律拒絕，而且什麼都不做。"""
    c = load_contract(name)
    body = dict(c['json'], token='wrong')
    r = client.open(c['path'], method=c['method'],
                    headers=dict(c['headers'], **{'X-Feedback-Token': 'wrong'}),
                    data=json.dumps(body).encode('utf-8'))
    assert r.status_code == 403
    assert line.pushes == [] and db.files == {}


@pytest.mark.parametrize('name', INBOUND)
def test_inbound_sample_refused_when_server_token_unset(name, client, line, db, monkeypatch):
    """主機沒設 FEEDBACK_TOKEN 時要全部拒絕(fail-closed)，不能變成不檢查。"""
    import app as bot
    monkeypatch.setattr(bot, 'FEEDBACK_TOKEN', '')
    c = load_contract(name)
    body = dict(c['json'], token='')
    headers = {k: v for k, v in c['headers'].items() if k != 'X-Feedback-Token'}
    r = client.open(c['path'], method=c['method'], headers=headers, data=json.dumps(body).encode('utf-8'))
    assert r.status_code == 403
    assert line.pushes == [] and db.files == {}


def test_report_then_admin_reads_it_back(client, say, line):
    """整條路：阿生地圖送報告 → 管理員在 LINE 打「檢查」→ 讀回同一份。"""
    for name in ('report_push_daily.json', 'report_push_watch.json'):
        c = load_contract(name)
        assert client.post(c['path'], headers=c['headers'], data=json.dumps(c['json'])).status_code == 200
    assert say('檢查', uid=ADMIN_UID).status_code == 200
    reply = line.reply_texts[0]
    assert '阿生地圖守門員' in reply
    assert '查 12 筆，都正常' in reply
    assert '更新於 2026-11-14 06:30' in reply
