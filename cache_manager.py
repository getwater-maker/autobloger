"""
캐시 관리 모듈
- 구독 목록, 채널 정보 캐싱
- 캐시 만료 확인 (24시간)
"""

import os
import json
from datetime import datetime, timedelta

CACHE_DIR = 'cache'
CACHE_EXPIRY_HOURS = 24

# 캐시 파일 경로
SUBSCRIPTIONS_CACHE = os.path.join(CACHE_DIR, 'subscriptions.json')
CHANNELS_CACHE = os.path.join(CACHE_DIR, 'channels.json')
VIDEOS_CACHE = os.path.join(CACHE_DIR, 'videos.json')


def _ensure_cache_dir():
    """캐시 디렉토리가 없으면 생성합니다."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def _is_cache_valid(cache_file):
    """캐시 파일이 유효한지 확인합니다 (24시간 이내)."""
    if not os.path.exists(cache_file):
        return False

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cached_time = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
        expiry_time = cached_time + timedelta(hours=CACHE_EXPIRY_HOURS)

        return datetime.now() < expiry_time
    except Exception:
        return False


def _save_cache(cache_file, data):
    """데이터를 캐시 파일에 저장합니다."""
    _ensure_cache_dir()

    cache_data = {
        'cached_at': datetime.now().isoformat(),
        'data': data
    }

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)


def _load_cache(cache_file):
    """캐시 파일에서 데이터를 불러옵니다."""
    if not _is_cache_valid(cache_file):
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('data')
    except Exception:
        return None


# 구독 목록 캐시
def save_subscriptions(subscriptions):
    """구독 목록을 캐시에 저장합니다."""
    _save_cache(SUBSCRIPTIONS_CACHE, subscriptions)
    print(f"구독 목록 {len(subscriptions)}개 캐시 저장 완료")


def load_subscriptions():
    """캐시에서 구독 목록을 불러옵니다."""
    data = _load_cache(SUBSCRIPTIONS_CACHE)
    if data:
        print(f"캐시에서 구독 목록 {len(data)}개 로드")
    return data


# 채널 정보 캐시
def save_channels(channels):
    """채널 정보를 캐시에 저장합니다."""
    _save_cache(CHANNELS_CACHE, channels)
    print(f"채널 정보 {len(channels)}개 캐시 저장 완료")


def load_channels():
    """캐시에서 채널 정보를 불러옵니다."""
    data = _load_cache(CHANNELS_CACHE)
    if data:
        print(f"캐시에서 채널 정보 {len(data)}개 로드")
    return data


# 캐시 삭제
def clear_all_cache():
    """모든 캐시를 삭제합니다."""
    cache_files = [SUBSCRIPTIONS_CACHE, CHANNELS_CACHE, VIDEOS_CACHE]

    for cache_file in cache_files:
        if os.path.exists(cache_file):
            os.remove(cache_file)

    print("모든 캐시 삭제 완료")


def clear_subscriptions_cache():
    """구독 목록 캐시만 삭제합니다."""
    if os.path.exists(SUBSCRIPTIONS_CACHE):
        os.remove(SUBSCRIPTIONS_CACHE)
        print("구독 목록 캐시 삭제 완료")


def get_cache_info():
    """캐시 상태 정보를 반환합니다."""
    info = {}

    for name, path in [('subscriptions', SUBSCRIPTIONS_CACHE),
                       ('channels', CHANNELS_CACHE),
                       ('videos', VIDEOS_CACHE)]:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                info[name] = {
                    'exists': True,
                    'cached_at': data.get('cached_at'),
                    'count': len(data.get('data', []))
                }
            except Exception:
                info[name] = {'exists': False}
        else:
            info[name] = {'exists': False}

    return info
