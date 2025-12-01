"""
YouTube API 호출 모듈
- 구독 채널 목록 조회
- 채널 정보 배치 조회
- 영상 정보 배치 조회
"""

import re


def get_subscriptions(youtube):
    """
    구독 채널 목록을 가져옵니다 (구독자 수 포함).

    Args:
        youtube: OAuth 인증된 YouTube API 서비스

    Returns:
        list: [{'id': 채널ID, 'title': 채널명, 'thumbnail': 썸네일URL, 'subscriberCount': 구독자수}, ...]
    """
    subscriptions = []
    next_page_token = None

    # 1단계: 구독 채널 ID 목록 수집
    while True:
        request = youtube.subscriptions().list(
            part='snippet',
            mine=True,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get('items', []):
            snippet = item['snippet']
            subscriptions.append({
                'id': snippet['resourceId']['channelId'],
                'title': snippet['title'],
                'thumbnail': snippet['thumbnails']['default']['url'],
                'description': snippet.get('description', '')[:100]
            })

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    # 2단계: 채널별 구독자 수 조회
    if subscriptions:
        channel_ids = [sub['id'] for sub in subscriptions]
        channel_stats = get_channels_batch(youtube, channel_ids)

        for sub in subscriptions:
            stats = channel_stats.get(sub['id'], {})
            sub['subscriberCount'] = stats.get('subscriberCount', 0)

    return subscriptions


def get_channels_batch(youtube, channel_ids):
    """
    채널 정보를 배치로 가져옵니다 (50개씩).

    Args:
        youtube: YouTube API 서비스
        channel_ids: 채널 ID 리스트

    Returns:
        dict: {채널ID: {'subscriberCount': 구독자수, 'title': 채널명}, ...}
    """
    if not channel_ids:
        return {}

    result = {}
    batch_size = 50

    for i in range(0, len(channel_ids), batch_size):
        batch = channel_ids[i:i + batch_size]

        try:
            request = youtube.channels().list(
                part='snippet,statistics',
                id=','.join(batch)
            )
            response = request.execute()

            for item in response.get('items', []):
                channel_id = item['id']
                stats = item['statistics']
                snippet = item['snippet']

                result[channel_id] = {
                    'subscriberCount': int(stats.get('subscriberCount', 0)),
                    'title': snippet.get('title', ''),
                    'thumbnail': snippet['thumbnails']['default']['url']
                }

        except Exception as e:
            print(f"채널 정보 조회 실패 (배치 {i // batch_size + 1}): {e}")

    return result


def get_videos_batch(youtube, video_ids):
    """
    영상 정보를 배치로 가져옵니다 (50개씩).

    Args:
        youtube: YouTube API 서비스
        video_ids: 영상 ID 리스트

    Returns:
        dict: {영상ID: {'viewCount': 조회수, 'duration': 길이(초)}, ...}
    """
    if not video_ids:
        return {}

    result = {}
    batch_size = 50

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i + batch_size]

        try:
            request = youtube.videos().list(
                part='statistics,contentDetails',
                id=','.join(batch)
            )
            response = request.execute()

            for item in response.get('items', []):
                video_id = item['id']
                stats = item['statistics']
                content = item['contentDetails']

                result[video_id] = {
                    'viewCount': int(stats.get('viewCount', 0)),
                    'likeCount': int(stats.get('likeCount', 0)),
                    'commentCount': int(stats.get('commentCount', 0)),
                    'duration': parse_duration(content.get('duration', 'PT0S'))
                }

        except Exception as e:
            print(f"영상 정보 조회 실패 (배치 {i // batch_size + 1}): {e}")

    return result


def parse_duration(duration_str):
    """
    ISO 8601 기간 형식을 초 단위로 변환합니다.

    Args:
        duration_str: 'PT1H2M3S' 형식의 문자열

    Returns:
        int: 총 초
    """
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)

    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds
