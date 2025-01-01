import unittest
from unittest.mock import patch, mock_open

from confctl.config import load_config, update_config, get, set, SubConf


class TestConfigTool(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_load_config_json(self, mock_file):
        load_config('config.json')
        mock_file.assert_called_once_with('config.json', 'r')
        self.assertEqual(get('key1'), 'value1')
        self.assertEqual(get('key2/subkey1'), 'subvalue1')

    @patch('builtins.open', new_callable=mock_open, read_data="key1: value1\nkey2:\n  subkey1: subvalue1")
    def test_load_config_yaml(self, mock_file):
        load_config('config.yaml')
        mock_file.assert_called_once_with('config.yaml', 'r')
        self.assertEqual(get('key1'), 'value1')
        self.assertEqual(get('key2/subkey1'), 'subvalue1')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_update_config(self, mock_file):
        load_config('config.json')  # Load initial config
        update_config({'key2': {'subkey1': 'updated_subvalue'}})
        self.assertEqual(get('key2/subkey1'), 'updated_subvalue')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_update_config_nested(self, mock_file):
        load_config('config.json')
        update_config({'key2': {'subkey1': 'updated_subvalue', 'subkey2': 'new_subkey'}})
        self.assertEqual(get('key2/subkey1'), 'updated_subvalue')
        self.assertEqual(get('key2/subkey2'), 'new_subkey')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_get_existing_key(self, mock_file):
        load_config('config.json')
        self.assertEqual(get('key1'), 'value1')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_get_non_existing_key_with_default(self, mock_file):
        load_config('config.json')
        self.assertEqual(get('non_existing_key', default='default_value'), 'default_value')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_get_non_existing_key_without_default(self, mock_file):
        load_config('config.json')
        with self.assertRaises(KeyError):
            get('non_existing_key')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_set_key(self, mock_file):
        load_config('config.json')
        set('key3', 'value3')
        self.assertEqual(get('key3'), 'value3')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_subconf(self, mock_file):
        load_config('config.json')
        subconf = SubConf('key2')
        self.assertEqual(subconf.get('subkey1'), 'subvalue1')
        subconf.set('subkey1', 'new_subvalue')
        self.assertEqual(subconf.get('subkey1'), 'new_subvalue')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_subconf_invalid_parent(self, mock_file):
        load_config('config.json')
        with self.assertRaises(KeyError):
            SubConf('non_existing_key')
        with self.assertRaises(ValueError):
            SubConf('key1')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key1": "value1", "key2": {"subkey1": "subvalue1"}}')
    def test_subconf_get_non_existing_key(self, mock_file):
        load_config('config.json')
        subconf = SubConf('key2')
        self.assertEqual(subconf.get('non_existing_subkey', default='default_value'), 'default_value')


if __name__ == '__main__':
    unittest.main()
