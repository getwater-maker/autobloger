"""
OAuth 2.0 인증 처리 모듈
- config.py에서 키를 읽어옴
"""

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config

# OAuth 스코프 (읽기 전용)
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

# 토큰 파일 경로
TOKEN_FILE = 'token.json'


def get_authenticated_service():
    """
    OAuth 인증된 YouTube API 서비스를 반환합니다.

    Returns:
        YouTube API 서비스 객체 또는 None
    """
    if not config.CLIENT_ID or not config.CLIENT_SECRET:
        print("오류: config.py에 CLIENT_ID와 CLIENT_SECRET을 입력하세요.")
        return None

    creds = None

    # 저장된 토큰 확인
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 토큰이 없거나 유효하지 않으면 인증 진행
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 토큰 갱신
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"토큰 갱신 실패: {e}")
                creds = None

        if not creds:
            # 새로운 인증 진행
            client_config = {
                "installed": {
                    "client_id": config.CLIENT_ID,
                    "client_secret": config.CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"]
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            # 타임아웃 없이 진행, 사용자가 취소하면 예외 발생
            creds = flow.run_local_server(
                port=8080,
                open_browser=True,
                success_message='인증 완료! 이 창을 닫아도 됩니다.'
            )

        # 토큰 저장
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    # YouTube API 서비스 생성
    return build('youtube', 'v3', credentials=creds)


def get_api_service():
    """
    API 키를 사용한 YouTube API 서비스를 반환합니다.
    (인증 불필요한 API 호출용)

    Returns:
        YouTube API 서비스 객체 또는 None
    """
    if not config.API_KEY:
        return None

    return build('youtube', 'v3', developerKey=config.API_KEY)


def is_configured():
    """OAuth 설정이 완료되었는지 확인합니다."""
    return bool(config.CLIENT_ID) and bool(config.CLIENT_SECRET)


def is_authenticated():
    """인증 상태를 확인합니다."""
    if not os.path.exists(TOKEN_FILE):
        return False

    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return creds and (creds.valid or creds.refresh_token)
    except Exception:
        return False


def logout():
    """저장된 토큰을 삭제합니다."""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        return True
    return False
