# -- coding: utf-8 --
"""通訊錄下載權限：阿生地圖登入＋公司同事驗證；舊共用權杖只在過渡期有效。

請求的樣子對應 landreg-desktop/main.py 的 _contacts_headers()：
  X-Landmap-Session = 阿生地圖登入憑證，X-Contacts-Token = 舊共用權杖(過渡期)
阿生地圖的回應樣子在 tests/contracts/landmap_auth_company.json。
"""
import base64

import pytest
import requests

import app as bot
from conftest import TEST_ENV, FakeResponse, load_contract

COMPANY_URL = 'https://map.windsky-sky.com/api/auth/company'
LEGACY = {'X-Contacts-Token': TEST_ENV['CONTACTS_DL_TOKEN']}
SESSION = {'X-Landmap-Session': 'sess-abc'}
XLSX = b'PK\x03\x04' + b'x' * 200


@pytest.fixture
def stored(db):
    db.save_app_file('contacts_xlsx', base64.b64encode(XLSX).decode(), '2026-11-01T10:00:00')


@pytest.fixture
def landmap(net):
    """landmap('member') → 阿生地圖照範例回「是公司成員」。"""
    samples = load_contract('landmap_auth_company.json')['responses']

    def _set(kind):
        s = samples[kind]
        net.add(COMPANY_URL, FakeResponse(s['status'], s['json']))
    return _set


@pytest.fixture
def legacy_open(monkeypatch):
    monkeypatch.setattr(bot, 'CONTACTS_LEGACY_UNTIL', '2099-12-31')


@pytest.fixture
def legacy_closed(monkeypatch):
    monkeypatch.setattr(bot, 'CONTACTS_LEGACY_UNTIL', '2000-01-01')


# ── 阿生地圖登入 ──
@pytest.mark.parametrize('kind', ['member', 'admin'])
def test_staff_session_downloads_file(kind, client, stored, landmap, legacy_closed, net):
    landmap(kind)
    r = client.get('/contacts/download', headers=SESSION)
    assert r.status_code == 200
    assert r.data == XLSX
    assert r.headers['X-Contacts-Updated'] == '2026-11-01T10:00:00'
    assert net.calls_to(COMPANY_URL)[0]['cookies'] == {'session': 'sess-abc'}


@pytest.mark.parametrize('kind', ['not_staff', 'blocked'])
def test_non_staff_session_is_403_not_staff(kind, client, stored, landmap, legacy_closed):
    landmap(kind)
    r = client.get('/contacts/download', headers=SESSION)
    assert r.status_code == 403
    assert r.get_json() == {'status': 'NOT_STAFF'}      # 主程式靠這個字顯示「帳號還沒被認定是同事」


def test_non_staff_is_refused_even_with_valid_legacy_token(client, stored, landmap, legacy_open):
    landmap('not_staff')
    r = client.get('/contacts/download', headers=dict(SESSION, **LEGACY))
    assert r.status_code == 403


def test_expired_session_is_401_login_required(client, stored, landmap, legacy_closed):
    landmap('not_logged_in')
    r = client.get('/contacts/download', headers=SESSION)
    assert r.status_code == 401
    assert r.get_json() == {'status': 'LOGIN_REQUIRED'}


def test_no_credentials_is_401(client, stored, legacy_open, net):
    r = client.get('/contacts/download')
    assert r.status_code == 401
    assert net.calls_to(COMPANY_URL) == []


def test_staff_result_cached_for_10_minutes(client, stored, landmap, legacy_closed, net):
    landmap('member')
    for _ in range(3):
        assert client.get('/contacts/download', headers=SESSION).status_code == 200
    assert len(net.calls_to(COMPANY_URL)) == 1
    bot._CO_CACHE.update({k: (ok, how, t - 601) for k, (ok, how, t) in bot._CO_CACHE.items()})
    assert client.get('/contacts/download', headers=SESSION).status_code == 200
    assert len(net.calls_to(COMPANY_URL)) == 2


# ── 阿生地圖連不上 ──
def test_landmap_down_and_never_verified_is_503(client, stored, net, legacy_closed):
    net.add(COMPANY_URL, requests.exceptions.ConnectionError('down'))
    r = client.get('/contacts/download', headers=SESSION)
    assert r.status_code == 503
    assert r.get_json() == {'status': 'ERROR'}


def test_landmap_down_but_verified_within_7_days_still_allowed(client, stored, landmap, net, legacy_closed):
    landmap('member')
    assert client.get('/contacts/download', headers=SESSION).status_code == 200
    # 三天後阿生地圖掛了
    bot._CO_CACHE.update({k: (ok, how, t - 3 * 86400) for k, (ok, how, t) in bot._CO_CACHE.items()})
    net.add(COMPANY_URL, requests.exceptions.ConnectionError('down'))
    assert client.get('/contacts/download', headers=SESSION).status_code == 200


def test_landmap_down_and_verified_more_than_7_days_ago_is_503(client, stored, landmap, net, legacy_closed):
    landmap('member')
    assert client.get('/contacts/download', headers=SESSION).status_code == 200
    bot._CO_CACHE.update({k: (ok, how, t - 8 * 86400) for k, (ok, how, t) in bot._CO_CACHE.items()})
    net.add(COMPANY_URL, requests.exceptions.ConnectionError('down'))
    assert client.get('/contacts/download', headers=SESSION).status_code == 503


def test_landmap_down_falls_back_to_legacy_token_during_transition(client, stored, net, legacy_open):
    net.add(COMPANY_URL, requests.exceptions.ConnectionError('down'))
    assert client.get('/contacts/download', headers=dict(SESSION, **LEGACY)).status_code == 200


def test_landmap_garbage_reply_is_treated_as_down(client, stored, net, legacy_closed):
    net.add(COMPANY_URL, FakeResponse(502, None, text='<html>Bad gateway</html>'))
    assert client.get('/contacts/download', headers=SESSION).status_code == 503


# ── 舊共用權杖 ──
def test_legacy_token_works_during_transition(client, stored, legacy_open):
    assert client.get('/contacts/download', headers=LEGACY).status_code == 200
    assert client.get('/contacts/download?token=' + TEST_ENV['CONTACTS_DL_TOKEN']).status_code == 200


def test_legacy_token_refused_after_transition(client, stored, legacy_closed):
    r = client.get('/contacts/download', headers=LEGACY)
    assert r.status_code == 401
    assert r.get_json() == {'status': 'LOGIN_REQUIRED'}


def test_legacy_token_still_works_on_the_last_day(client, stored, monkeypatch):
    import datetime
    today_tw = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d')
    monkeypatch.setattr(bot, 'CONTACTS_LEGACY_UNTIL', today_tw)
    assert client.get('/contacts/download', headers=LEGACY).status_code == 200


def test_wrong_legacy_token_refused(client, stored, legacy_open):
    assert client.get('/contacts/download', headers={'X-Contacts-Token': 'nope'}).status_code == 401


def test_legacy_token_refused_when_server_token_unset(client, stored, legacy_open, monkeypatch):
    monkeypatch.setattr(bot, 'CONTACTS_DL_TOKEN', '')
    assert client.get('/contacts/download', headers={'X-Contacts-Token': ''}).status_code == 401


# ── 檔案本身 ──
def test_download_404_when_nothing_uploaded(client, legacy_open):
    assert client.get('/contacts/download', headers=LEGACY).status_code == 404


def test_meta_reports_version(client, stored, legacy_open):
    r = client.get('/contacts/meta', headers=LEGACY)
    assert r.get_json() == {'updated': '2026-11-01T10:00:00', 'exists': True}


def test_meta_when_empty(client, legacy_open):
    assert client.get('/contacts/meta', headers=LEGACY).get_json() == {'updated': '', 'exists': False}


def test_meta_needs_the_same_permission(client, stored, legacy_closed):
    assert client.get('/contacts/meta', headers=LEGACY).status_code == 401


# ── 上傳(管理者) ──
def _upload(client, token, raw=XLSX):
    import io
    return client.post('/contacts/upload', headers={'X-Contacts-Admin-Token': token},
                       data={'file': (io.BytesIO(raw), '通訊錄.xlsx')}, content_type='multipart/form-data')


def test_admin_upload_then_staff_download_roundtrip(client, db, legacy_open):
    r = _upload(client, TEST_ENV['CONTACTS_ADMIN_TOKEN'])
    assert r.status_code == 200 and r.get_json() == {'ok': True, 'size': len(XLSX)}
    assert client.get('/contacts/download', headers=LEGACY).data == XLSX


def test_upload_refuses_wrong_or_download_token(client, db):
    assert _upload(client, 'nope').status_code == 403
    assert _upload(client, TEST_ENV['CONTACTS_DL_TOKEN']).status_code == 403    # 下載權杖不能拿來上傳
    assert db.files == {}


def test_upload_refused_when_admin_token_unset(client, db, monkeypatch):
    monkeypatch.setattr(bot, 'CONTACTS_ADMIN_TOKEN', '')
    assert _upload(client, '').status_code == 403


def test_upload_refuses_tiny_file(client, db):
    assert _upload(client, TEST_ENV['CONTACTS_ADMIN_TOKEN'], raw=b'tiny').status_code == 400
    assert db.files == {}
