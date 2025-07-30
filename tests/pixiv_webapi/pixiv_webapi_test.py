import json
import unittest
from unittest.mock import patch, Mock

import litter
from agents.pixiv import PixivWebAPI, PixivWebAPIException, api
from confctl import config


class TestPixivWebAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config.load_config("config/dev.yaml")
        cls.papi = PixivWebAPI(config.get("pixiv_webapi/token"))

    @patch('requests.Session.get')
    def test_illust(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": False,
            "body": {"illust_id": 12345, "title": "Test Illust"}
        }
        mock_get.return_value = mock_response

        api = PixivWebAPI(php_session_id="1234567890_abcdef")
        result = api.illust(12345)

        self.assertEqual(result['illust_id'], 12345)
        self.assertEqual(result['title'], 'Test Illust')

    @patch('requests.Session.get')
    def test_illust_with_error(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"error": True, "message": "Illust not found"}
        mock_get.return_value = mock_response

        api = PixivWebAPI(php_session_id="1234567890_abcdef")

        with self.assertRaises(PixivWebAPIException):
            api.illust(99999)

    @patch('requests.Session.get')
    def test_illust_pages(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": False,
            "body": [{"page_id": 1, "image_url": "http://example.com/image1.jpg"},
                     {"page_id": 2, "image_url": "http://example.com/image2.jpg"}]
        }
        mock_get.return_value = mock_response

        api = PixivWebAPI(php_session_id="1234567890_abcdef")
        result = api.illust_pages(12345)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['page_id'], 1)
        self.assertEqual(result[1]['page_id'], 2)

    @patch('requests.Session.get')
    def test_user_info(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": False,
            "body": {"user_id": 12345, "username": "test_user"}
        }
        mock_get.return_value = mock_response

        api = PixivWebAPI(php_session_id="1234567890_abcdef")
        result = api.user_info()

        self.assertEqual(result['user_id'], 12345)
        self.assertEqual(result['username'], 'test_user')

    @patch('requests.Session.get')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_download(self, mock_open, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'fakeimagecontent']
        mock_get.return_value = mock_response

        api = PixivWebAPI(php_session_id="1234567890_abcdef")
        api.download('http://example.com/image.jpg', 'path/to/save/image.jpg')

        mock_open.assert_called_once_with('path/to/save/image.jpg', 'wb')
        mock_open().write.assert_called_once_with(b'fakeimagecontent')

    def test_follow_latest_illust(self):
        ret = self.papi.follow_latest_illust()
        with open("assets/pixiv_webapi_json/follow_latest_illust.json", 'w', encoding='utf8') as f:
            json.dump(ret, f, ensure_ascii=False, indent=4)

    def test_api(self):
        litter.connect("127.0.0.1", 56379)
        print(api.top_illust())

if __name__ == '__main__':
    unittest.main()
