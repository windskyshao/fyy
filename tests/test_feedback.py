# -- coding: utf-8 --
"""意見回饋 /feedback、地籍圖失敗回報 /cadastral_fail、報告存放 /report_push 的細節。"""
import base64
import os

from conftest import ADMIN_UID, FEEDBACK_TOKEN

H = {'X-Feedback-Token': FEEDBACK_TOKEN}


def _fb(client, ip='1.2.3.4', **body):
    body.setdefault('message', 'hi')
    return client.post('/feedback', json=body, headers=dict(H, **{'X-Forwarded-For': ip}))


def test_feedback_same_ip_limited_to_6_per_hour(client, line):
    codes = [_fb(client).status_code for _ in range(7)]
    assert codes == [200] * 6 + [429]
    assert len(line.pushes) == 6            # 第 7 則沒有推出去
    assert _fb(client, ip='5.6.7.8').status_code == 200     # 別的 IP 不受影響


def test_feedback_whole_site_limited_to_40_per_hour(client, line):
    codes = [_fb(client, ip='10.0.0.%d' % i).status_code for i in range(41)]
    assert codes == [200] * 40 + [429]
    assert len(line.pushes) == 40


def test_feedback_limit_resets_after_an_hour(client):
    import app as bot
    for _ in range(6):
        _fb(client)
    assert _fb(client).status_code == 429
    bot._FB_HITS[:] = [(ip, t - 3601) for ip, t in bot._FB_HITS]    # 假裝過了一小時
    assert _fb(client).status_code == 200


def test_feedback_rejected_token_does_not_use_up_quota(client):
    for _ in range(10):
        assert client.post('/feedback', json={'message': 'x'}, headers={'X-Feedback-Token': 'bad'}).status_code == 403
    assert _fb(client).status_code == 200


def test_feedback_long_message_is_cut(client, line):
    assert _fb(client, message='字' * 5000).status_code == 200
    assert '字' * 3000 in line.push_texts[0]
    assert '字' * 3001 not in line.push_texts[0]


def test_feedback_screenshot_saved_and_sent(client, line, chart_dir):
    png = b'\x89PNG fake'
    assert _fb(client, screenshot_b64=base64.b64encode(png).decode()).status_code == 200
    files = os.listdir(chart_dir)
    assert len(files) == 1 and files[0].startswith('feedback_') and files[0].endswith('.png')
    assert (chart_dir / files[0]).read_bytes() == png
    _to, msgs = line.pushes[0]
    assert len(msgs) == 2
    assert msgs[1].original_content_url.endswith('/charts/' + files[0])
    # 存下來的截圖真的抓得到
    assert client.get('/charts/' + files[0]).data == png


def test_feedback_oversized_screenshot_dropped_but_text_still_sent(client, line, chart_dir):
    assert _fb(client, screenshot_b64='A' * (8 * 1024 * 1024 + 4)).status_code == 200
    assert os.listdir(chart_dir) == []
    assert len(line.pushes[0][1]) == 1


def test_feedback_defaults_for_missing_fields(client, line):
    assert client.post('/feedback', json={}, headers=H).status_code == 200
    text = line.push_texts[0]
    assert '版本：未知' in text and '來自：匿名' in text and '內容：(無內容)' in text


def test_feedback_form_post_also_works(client, line):
    r = client.post('/feedback', data={'token': FEEDBACK_TOKEN, 'name': '表單', 'message': '用表單送'})
    assert r.status_code == 200
    assert '來自：表單' in line.push_texts[0]


def test_feedback_reports_500_when_line_push_fails(client, line):
    line.push_error = RuntimeError('quota')
    assert _fb(client).status_code == 500


def test_cadastral_fail_without_items_is_400(client, line):
    assert client.post('/cadastral_fail', json={'items': []}, headers=H).status_code == 400
    assert line.pushes == []


def test_cadastral_fail_keeps_at_most_20_items(client, line):
    items = [{'filename': 'f%d.pdf' % i, 'reason': 'x'} for i in range(25)]
    assert client.post('/cadastral_fail', json={'items': items}, headers=H).status_code == 200
    text = line.push_texts[0]
    assert '地籍圖處理失敗 20 張' in text
    assert 'f19.pdf' in text and 'f20.pdf' not in text
    assert line.pushes[0][0] == ADMIN_UID


def test_cadastral_fail_bad_base64_still_reports(client, line):
    items = [{'filename': 'a.pdf', 'reason': '壞檔', 'pdf_b64': '!!!not-base64'}]
    assert client.post('/cadastral_fail', json={'items': items}, headers=H).status_code == 200
    assert '原因：壞檔' in line.push_texts[0]


def test_report_push_empty_text_is_400(client, db):
    assert client.post('/report_push', json={'text': '   '}, headers=H).status_code == 400
    assert db.files == {}


def test_report_push_daily_and_watch_are_kept_separately(client, db):
    client.post('/report_push', json={'text': '每日'}, headers=H)
    client.post('/report_push', json={'text': '守門員', 'kind': 'watch'}, headers=H)
    client.post('/report_push', json={'text': '每日新版'}, headers=H)
    assert sorted(db.files) == ['landmap_daily_report', 'landmap_watch_report']
    import json
    assert json.loads(base64.b64decode(db.files['landmap_daily_report'][0]))['text'] == '每日新版'
    assert json.loads(base64.b64decode(db.files['landmap_watch_report'][0]))['text'] == '守門員'
