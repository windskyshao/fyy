# -- coding: utf-8 --
"""油價每週推播：省推播額度的幾道關卡。"""
import datetime

import pytest

import app as bot


def _eff(days):
    d = datetime.datetime.utcnow() + datetime.timedelta(hours=8) + datetime.timedelta(days=days)
    return d.strftime('%Y/%m/%d')


@pytest.fixture
def oil(monkeypatch):
    """oil(data) → 假裝油價資料源回這份。"""
    def _set(data):
        monkeypatch.setattr(bot, 'oil_price', lambda force=False: data)
    return _set


TEXT_ONLY = {'prices': {'92': '29.0', '95': '30.5'}, 'forecast': {'汽油調整': '漲0.2'}}


def test_no_change_week_is_not_pushed(client, oil, line, db):
    db.followers = ['U1', 'U2']
    oil(dict(TEXT_ONLY, effective_date=_eff(1), deltas={'92': 0, '95': 0.0, '柴油': '0'}))
    r = client.get('/cron/oil_price')
    assert r.status_code == 200 and 'no price change' in r.get_data(as_text=True)
    assert line.pushes == []
    assert db.cron.get('oil_price')                 # 記下今天處理過，同一天不再重複判斷


def test_price_change_is_pushed_to_every_follower_once(client, oil, line, db):
    db.followers = ['U1', 'U2', 'U3']
    oil(dict(TEXT_ONLY, effective_date=_eff(1), deltas={'92': 0.2, '95': 0.2}))
    assert 'sent=3' in client.get('/cron/oil_price').get_data(as_text=True)
    assert [to for to, _ in line.pushes] == ['U1', 'U2', 'U3']
    # 排程重試再打一次：不可以重複推
    assert 'already sent today' in client.get('/cron/oil_price').get_data(as_text=True)
    assert len(line.pushes) == 3


@pytest.mark.parametrize('days', [-1, 8])
def test_stale_data_is_not_pushed_and_can_retry_later(days, client, oil, line, db):
    db.followers = ['U1']
    oil(dict(TEXT_ONLY, effective_date=_eff(days), deltas={'92': 0.2}))
    assert 'data not fresh' in client.get('/cron/oil_price').get_data(as_text=True)
    assert line.pushes == []
    assert 'oil_price' not in db.cron               # 沒記錄 → 下一次排程還能再試


def test_missing_effective_date_is_not_pushed(client, oil, line, db):
    db.followers = ['U1']
    oil(dict(TEXT_ONLY))
    assert 'data not fresh' in client.get('/cron/oil_price').get_data(as_text=True)
    assert line.pushes == []


def test_test_mode_only_reaches_admin_and_does_not_block_real_run(client, oil, line, db):
    db.followers = ['U1', 'U2']
    oil(dict(TEXT_ONLY, effective_date=_eff(1), deltas={'92': 0.2}))
    assert 'sent=1 (test)' in client.get('/cron/oil_price?test=1').get_data(as_text=True)
    assert [to for to, _ in line.pushes] == [bot.ADMIN_USER_ID]
    assert 'oil_price' not in db.cron
