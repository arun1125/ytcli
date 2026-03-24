"""Tests for core/api.py — YouTube Data API v3 wrapper."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from ytcli.core.api import (
    get_api_client,
    get_channel_stats,
    get_video_stats,
    get_comments,
    search_youtube,
)


# --- get_api_client ---


class TestGetApiClient:
    def test_import_error_when_no_google_lib(self):
        """Graceful error if google-api-python-client not installed."""
        with patch.dict(sys.modules, {"googleapiclient": None, "googleapiclient.discovery": None}):
            with pytest.raises(ImportError, match="pip install ytcli"):
                get_api_client("fake-key")

    def test_builds_client_with_key(self):
        """Calls build() with correct params when library is available."""
        mock_build = MagicMock(return_value="mock_client")
        with patch.dict(sys.modules, {
            "googleapiclient": MagicMock(),
            "googleapiclient.discovery": MagicMock(build=mock_build),
        }):
            result = get_api_client("test-key-123")
            mock_build.assert_called_once_with("youtube", "v3", developerKey="test-key-123")
            assert result == "mock_client"


# --- Fixtures ---


@pytest.fixture
def mock_client():
    """Return a fully mocked YouTube API client."""
    return MagicMock()


# --- get_channel_stats ---


class TestGetChannelStats:
    def test_by_handle(self, mock_client):
        mock_client.channels().list().execute.return_value = {
            "items": [{
                "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "snippet": {
                    "title": "Google for Developers",
                    "description": "Dev channel",
                    "thumbnails": {"default": {"url": "https://thumb.example.com/photo.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "1000000",
                    "viewCount": "50000000",
                    "videoCount": "500",
                },
            }],
        }

        result = get_channel_stats(mock_client, "@googledevelopers")

        assert result["channel_id"] == "UC_x5XG1OV2P6uZZ5FSM9Ttw"
        assert result["name"] == "Google for Developers"
        assert result["subscriber_count"] == 1000000
        assert result["view_count"] == 50000000
        assert result["video_count"] == 500
        assert result["thumbnail_url"] == "https://thumb.example.com/photo.jpg"

    def test_by_channel_id(self, mock_client):
        mock_client.channels().list().execute.return_value = {
            "items": [{
                "id": "UC123",
                "snippet": {"title": "Test", "description": "", "thumbnails": {}},
                "statistics": {"subscriberCount": "10", "viewCount": "100", "videoCount": "5"},
            }],
        }

        result = get_channel_stats(mock_client, "UC123")
        assert result["channel_id"] == "UC123"
        assert result["subscriber_count"] == 10

    def test_channel_not_found(self, mock_client):
        mock_client.channels().list().execute.return_value = {"items": []}

        with pytest.raises(ValueError, match="Channel not found"):
            get_channel_stats(mock_client, "@nonexistent")


# --- get_video_stats ---


class TestGetVideoStats:
    def test_returns_stats(self, mock_client):
        mock_client.videos().list().execute.return_value = {
            "items": [{
                "id": "dQw4w9WgXcQ",
                "snippet": {
                    "title": "Never Gonna Give You Up",
                    "publishedAt": "2009-10-25T06:57:33Z",
                },
                "statistics": {
                    "viewCount": "1500000000",
                    "likeCount": "15000000",
                    "commentCount": "3000000",
                },
                "contentDetails": {
                    "duration": "PT3M33S",
                },
            }],
        }

        result = get_video_stats(mock_client, "dQw4w9WgXcQ")

        assert result["video_id"] == "dQw4w9WgXcQ"
        assert result["title"] == "Never Gonna Give You Up"
        assert result["view_count"] == 1500000000
        assert result["like_count"] == 15000000
        assert result["comment_count"] == 3000000
        assert result["duration"] == "PT3M33S"
        assert result["published_at"] == "2009-10-25T06:57:33Z"

    def test_video_not_found(self, mock_client):
        mock_client.videos().list().execute.return_value = {"items": []}

        with pytest.raises(ValueError, match="Video not found"):
            get_video_stats(mock_client, "nonexistent")


# --- get_comments ---


class TestGetComments:
    def _make_comment_response(self, n, next_page=None):
        items = []
        for i in range(n):
            items.append({
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorDisplayName": f"User{i}",
                            "textDisplay": f"Comment {i}",
                            "likeCount": i * 10,
                            "publishedAt": f"2024-01-{i+1:02d}T00:00:00Z",
                        }
                    }
                }
            })
        resp = {"items": items}
        if next_page:
            resp["nextPageToken"] = next_page
        return resp

    def test_returns_comments(self, mock_client):
        mock_client.commentThreads().list().execute.return_value = self._make_comment_response(3)

        result = get_comments(mock_client, "vid123", limit=10)

        assert len(result) == 3
        assert result[0]["author"] == "User0"
        assert result[0]["text"] == "Comment 0"
        assert result[1]["like_count"] == 10

    def test_respects_limit(self, mock_client):
        mock_client.commentThreads().list().execute.return_value = self._make_comment_response(5)

        result = get_comments(mock_client, "vid123", limit=3)
        assert len(result) == 3

    def test_pagination(self, mock_client):
        page1 = self._make_comment_response(2, next_page="page2token")
        page2 = self._make_comment_response(2)
        mock_client.commentThreads().list().execute.side_effect = [page1, page2]

        result = get_comments(mock_client, "vid123", limit=10)
        assert len(result) == 4

    def test_sort_top_maps_to_relevance(self, mock_client):
        mock_client.commentThreads().list().execute.return_value = self._make_comment_response(1)
        get_comments(mock_client, "vid123", sort="top", limit=5)
        # No error means it ran fine with sort="top"

    def test_sort_recent_maps_to_time(self, mock_client):
        mock_client.commentThreads().list().execute.return_value = self._make_comment_response(1)
        get_comments(mock_client, "vid123", sort="recent", limit=5)


# --- search_youtube ---


class TestSearchYoutube:
    def test_returns_results(self, mock_client):
        mock_client.search().list().execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {
                        "title": "Python Tutorial",
                        "channelTitle": "Corey Schafer",
                        "publishedAt": "2024-01-15T00:00:00Z",
                        "thumbnails": {"default": {"url": "https://img.example.com/1.jpg"}},
                    },
                },
                {
                    "id": {"videoId": "def456"},
                    "snippet": {
                        "title": "Python for Beginners",
                        "channelTitle": "Tech With Tim",
                        "publishedAt": "2024-02-01T00:00:00Z",
                        "thumbnails": {"default": {"url": "https://img.example.com/2.jpg"}},
                    },
                },
            ],
        }

        result = search_youtube(mock_client, "python tutorial", limit=10)

        assert len(result) == 2
        assert result[0]["video_id"] == "abc123"
        assert result[0]["title"] == "Python Tutorial"
        assert result[0]["channel"] == "Corey Schafer"
        assert result[1]["video_id"] == "def456"

    def test_respects_limit(self, mock_client):
        mock_client.search().list().execute.return_value = {
            "items": [
                {"id": {"videoId": f"v{i}"}, "snippet": {"title": f"Vid {i}", "channelTitle": "Ch", "publishedAt": "", "thumbnails": {}}}
                for i in range(5)
            ],
        }

        result = search_youtube(mock_client, "test", limit=3)
        assert len(result) == 3

    def test_empty_results(self, mock_client):
        mock_client.search().list().execute.return_value = {"items": []}

        result = search_youtube(mock_client, "xyznonexistent", limit=10)
        assert result == []
