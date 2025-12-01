"""
YouTube 구독 채널 필터 검색 프로그램
- Eel 기반 데스크톱 앱
"""

import eel
import os
from auth import (
    get_authenticated_service, get_api_service,
    is_configured, is_authenticated, logout
)
from youtube_api import get_subscriptions, get_channels_batch, get_videos_batch
from rss_fetcher import fetch_all_channels
import cache_manager
import config

# 전역 변수
youtube_service = None
subscriptions = []

# Eel 초기화
eel.init('web')


@eel.expose
def save_api_config(client_id, client_secret, api_key=''):
    """API 설정을 config.py에 저장합니다."""
    try:
        config_content = f'''# YouTube API 설정
# 이 파일은 프로그램에서 자동 생성/수정됩니다.

CLIENT_ID = "{client_id}"
CLIENT_SECRET = "{client_secret}"
API_KEY = "{api_key}"
'''
        config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

        # config 모듈 다시 로드
        import importlib
        importlib.reload(config)

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def get_current_config():
    """현재 저장된 API 설정을 반환합니다."""
    return {
        'clientId': config.CLIENT_ID or '',
        'clientSecret': config.CLIENT_SECRET or '',
        'apiKey': config.API_KEY or ''
    }


@eel.expose
def get_config_status():
    """설정 상태를 반환합니다."""
    global youtube_service

    authenticated = is_authenticated()

    # 인증된 상태라면 자동으로 서비스 연결
    if authenticated and not youtube_service:
        try:
            youtube_service = get_authenticated_service()
        except Exception as e:
            print(f"자동 로그인 실패: {e}")
            authenticated = False

    return {
        'isConfigured': is_configured(),
        'isAuthenticated': authenticated
    }


@eel.expose
def do_login():
    """OAuth 로그인을 수행합니다."""
    global youtube_service

    if not is_configured():
        return {'success': False, 'error': 'config.py에 CLIENT_ID와 CLIENT_SECRET을 입력하세요.'}

    try:
        youtube_service = get_authenticated_service()
        if youtube_service:
            return {'success': True}
        return {'success': False, 'error': '인증에 실패했습니다.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def do_logout():
    """로그아웃하고 캐시를 삭제합니다."""
    global youtube_service, subscriptions

    logout()
    cache_manager.clear_all_cache()
    youtube_service = None
    subscriptions = []

    return {'success': True}


@eel.expose
def load_subscriptions(force_refresh=False):
    """
    구독 채널 목록을 불러옵니다.
    """
    global youtube_service, subscriptions

    # 캐시 확인
    if not force_refresh:
        cached = cache_manager.load_subscriptions()
        if cached:
            # 캐시에 구독자 수가 없으면 API로 조회
            needs_subscriber_count = any(
                'subscriberCount' not in sub or sub.get('subscriberCount') == 0
                for sub in cached
            )

            if needs_subscriber_count:
                try:
                    if not youtube_service:
                        youtube_service = get_authenticated_service()

                    if youtube_service:
                        from youtube_api import get_channels_batch
                        channel_ids = [sub['id'] for sub in cached]
                        channel_stats = get_channels_batch(youtube_service, channel_ids)

                        for sub in cached:
                            stats = channel_stats.get(sub['id'], {})
                            sub['subscriberCount'] = stats.get('subscriberCount', 0)

                        cache_manager.save_subscriptions(cached)
                except Exception as e:
                    print(f"구독자 수 조회 실패: {e}")

            subscriptions = cached
            return {
                'success': True,
                'subscriptions': cached,
                'fromCache': True
            }

    # API 호출
    try:
        if not youtube_service:
            youtube_service = get_authenticated_service()

        if not youtube_service:
            return {'success': False, 'error': '로그인이 필요합니다.'}

        print("구독 채널 목록을 가져오는 중...")
        subs = get_subscriptions(youtube_service)

        if not subs:
            return {'success': False, 'error': '구독 채널이 없습니다.'}

        cache_manager.save_subscriptions(subs)
        subscriptions = subs

        return {
            'success': True,
            'subscriptions': subs,
            'fromCache': False
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def search_videos(filter_config):
    """
    조건에 맞는 영상을 검색합니다.
    """
    global youtube_service, subscriptions

    if not subscriptions:
        return {'success': False, 'error': '먼저 구독 채널을 불러오세요.'}

    try:
        # API 서비스 선택
        api_service = get_api_service()
        if not api_service:
            if not youtube_service:
                youtube_service = get_authenticated_service()
            api_service = youtube_service

        if not api_service:
            return {'success': False, 'error': 'API 키 또는 로그인이 필요합니다.'}

        filter_type = filter_config.get('filterType', 'normal')
        max_subscribers = filter_config.get('maxSubscribers', 10000)
        min_views = filter_config.get('minViews', 10000)
        days_within = filter_config.get('daysWithin', 15)
        mutation_ratio = filter_config.get('mutationRatio', 1.0)

        channel_ids = [sub['id'] for sub in subscriptions]
        print(f"총 {len(channel_ids)}개 채널 검색 시작...")

        # 1단계: 채널 구독자 수 조회
        print("1단계: 채널 정보 조회 중...")
        eel.update_progress("채널 정보 조회 중...", 10)()
        channel_info = get_channels_batch(api_service, channel_ids)

        # 2단계: RSS로 최신 영상 수집
        print("2단계: RSS 피드 수집 중...")
        eel.update_progress("RSS 피드 수집 중...", 30)()

        def rss_progress(current, total):
            percent = 30 + int((current / total) * 40)
            eel.update_progress(f"RSS 수집: {current}/{total}", percent)()

        all_videos = fetch_all_channels(channel_ids, days_within, rss_progress)
        print(f"총 {len(all_videos)}개 영상 수집됨")

        if not all_videos:
            return {
                'success': True,
                'videos': [],
                'stats': {'total': 0, 'filtered': 0}
            }

        # 3단계: 영상 상세 정보 조회
        print("3단계: 영상 정보 조회 중...")
        eel.update_progress("영상 정보 조회 중...", 75)()
        video_ids = [v['videoId'] for v in all_videos]
        video_info = get_videos_batch(api_service, video_ids)

        # 4단계: 필터링
        print("4단계: 필터 적용 중...")
        eel.update_progress("필터 적용 중...", 90)()

        filtered_videos = []
        min_duration = 181  # 쇼츠 제외

        for video in all_videos:
            video_id = video['videoId']
            channel_id = video['channelId']

            v_info = video_info.get(video_id)
            if not v_info:
                continue

            if v_info['duration'] < min_duration:
                continue

            view_count = v_info['viewCount']

            c_info = channel_info.get(channel_id)
            if not c_info:
                continue

            subscriber_count = c_info['subscriberCount']

            # 필터 적용
            if filter_type == 'normal':
                if subscriber_count > max_subscribers:
                    continue
                if view_count < min_views:
                    continue
            else:
                if subscriber_count == 0:
                    continue
                ratio = view_count / subscriber_count
                if ratio < mutation_ratio:
                    continue

            filtered_videos.append({
                'videoId': video_id,
                'title': video['title'],
                'channelId': channel_id,
                'channelTitle': c_info['title'],
                'thumbnail': video['thumbnail'],
                'publishedAt': video['publishedAt'],
                'viewCount': view_count,
                'likeCount': v_info['likeCount'],
                'subscriberCount': subscriber_count,
                'duration': v_info['duration'],
                'ratio': round(view_count / subscriber_count, 2) if subscriber_count > 0 else 0
            })

        filtered_videos.sort(key=lambda x: x['viewCount'], reverse=True)

        eel.update_progress("완료!", 100)()
        print(f"필터링 결과: {len(filtered_videos)}개")

        return {
            'success': True,
            'videos': filtered_videos,
            'stats': {
                'total': len(all_videos),
                'filtered': len(filtered_videos)
            }
        }

    except Exception as e:
        print(f"검색 오류: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def clear_cache():
    """모든 캐시를 삭제합니다."""
    cache_manager.clear_all_cache()
    return {'success': True}


@eel.expose
def get_subscriptions_list():
    """구독 채널 목록을 반환합니다 (팝업용)."""
    global subscriptions
    return subscriptions


@eel.expose
def unsubscribe_channel(channel_id):
    """채널 구독을 취소합니다."""
    global youtube_service, subscriptions

    try:
        if not youtube_service:
            youtube_service = get_authenticated_service()

        if not youtube_service:
            return {'success': False, 'error': '로그인이 필요합니다.'}

        # 구독 ID 찾기 (subscriptions.list로 조회)
        request = youtube_service.subscriptions().list(
            part='id',
            forChannelId=channel_id,
            mine=True
        )
        response = request.execute()

        if not response.get('items'):
            return {'success': False, 'error': '구독 정보를 찾을 수 없습니다.'}

        subscription_id = response['items'][0]['id']

        # 구독 취소
        youtube_service.subscriptions().delete(id=subscription_id).execute()

        # 로컬 목록에서도 제거
        subscriptions = [s for s in subscriptions if s['id'] != channel_id]

        # 캐시 업데이트
        cache_manager.save_subscriptions(subscriptions)

        print(f"채널 구독 취소 완료: {channel_id}")
        return {'success': True}

    except Exception as e:
        print(f"구독 취소 오류: {e}")
        return {'success': False, 'error': str(e)}


def on_close(page, sockets):
    """브라우저 창이 닫히면 프로그램 종료"""
    import os
    print("프로그램을 종료합니다.")
    os._exit(0)


if __name__ == '__main__':
    print("=== YouTube 구독 채널 검색 ===")
    print("브라우저에서 앱을 실행합니다...")

    try:
        eel.start('index.html', size=(1000, 800), close_callback=on_close)
    except EnvironmentError:
        eel.start('index.html', size=(1000, 800), mode='default', close_callback=on_close)
