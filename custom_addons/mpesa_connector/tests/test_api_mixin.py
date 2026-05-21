from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock
from odoo.exceptions import UserError


class TestMpesaAPIMixin(TransactionCase):

    def setUp(self):
        super().setUp()
        self.mixin = self.env['mpesa.api.mixin']

    def test_daraja_sandbox_url(self):
        url = self.mixin._daraja_url(sandbox=True)
        self.assertIn('sandbox.safaricom', url)

    def test_daraja_live_url(self):
        url = self.mixin._daraja_url(sandbox=False)
        self.assertIn('api.safaricom', url)
        self.assertNotIn('sandbox', url)

    @patch('requests.get')
    def test_get_access_token_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'access_token': 'test_token_123'}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        token = self.mixin._get_access_token('key', 'secret', sandbox=True)
        self.assertEqual(token, 'test_token_123')

    @patch('requests.get')
    def test_get_access_token_failure_raises_user_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.RequestException("Connection refused")

        with self.assertRaises(UserError):
            self.mixin._get_access_token('bad_key', 'bad_secret', sandbox=True)

    @patch('requests.post')
    @patch('requests.get')
    def test_stk_push_success(self, mock_get, mock_post):
        mock_get.return_value.json.return_value = {'access_token': 'tok'}
        mock_get.return_value.raise_for_status = MagicMock()

        mock_post.return_value.json.return_value = {
            'CheckoutRequestID': 'ws_CO_TEST_123',
            'MerchantRequestID': 'MR_TEST_456',
            'ResponseCode': '0',
        }
        mock_post.return_value.raise_for_status = MagicMock()

        result = self.mixin._stk_push(
            token='tok',
            shortcode='174379',
            passkey='testpasskey',
            phone='254712345678',
            amount=100,
            callback_url='https://test.com/callback',
            account_ref='TEST001',
            sandbox=True
        )
        self.assertIn('CheckoutRequestID', result)
