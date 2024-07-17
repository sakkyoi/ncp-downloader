from typing import Tuple

import random
import base64
import hashlib
from requests import session
import json
from urllib.parse import urlencode, urlparse, parse_qs
import jwt
import time


class NicoChannelAuth:
    def __init__(self, username: str, password: str,
                 site_base: str, platform_id: str, client_id: str, auth0_domain: str, audience: str) -> None:
        self.session = session()

        self.username = username
        self.password = password
        self.site_base = site_base
        self.platform_id = platform_id
        self.client_id = client_id
        self.auth0_domain = auth0_domain
        self.audience = audience

        # this is used to get openid configuration like authorization_endpoint, token_endpoint
        self.openid_configuration = f'https://{self.auth0_domain}/.well-known/openid-configuration'
        self.authorization_endpoint, self.token_endpoint = self.__initial_openid()

        # state
        self.code_verifier = self.__rand()
        self.code_challenge = self.__code_challenge(self.code_verifier)
        self.nonce = self.__btoa(self.__rand())
        self.state = self.__btoa(self.__rand())

        self.redirect_uri = f'https://{self.site_base}/login/login-redirect'
        self.auth0_client = self.__btoa(json.dumps({
            'name': 'auth0-spa-js',
            'version': '2.0.6'
        }))
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Auth0-Client': self.auth0_client
        }

        self.access_token, self.refresh_token = self.__login()

    def __str__(self) -> str:
        self.__auto_refresh()
        return self.access_token

    def __initial_openid(self) -> Tuple[str, str]:
        r = self.session.get(self.openid_configuration)
        openid_configuration = r.json()

        return openid_configuration['authorization_endpoint'], openid_configuration['token_endpoint']

    def __prepare_authorize_url(self) -> str:
        """
        Generate authorize url
        this is important to get code that will be used to get access token
        """
        params = {
            'audience': self.audience,
            'client_id': self.client_id,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256',
            # some ext parameters are missing for site other than nicochannel.jp
            # Those parameters are not important(maybe)
            'ext-group_id': "1",
            'ext-login_enable': 'null',
            'ext-platform_id': self.platform_id,
            'ext-terms': f'https://{self.site_base}/terms__content_type___nfc_terms_of_services',
            'nonce': self.nonce,
            'prompt': 'login',
            'redirect_uri': self.redirect_uri,
            'response_mode': 'query',
            'response_type': 'code',
            'scope': 'openid profile email offline_access',
            'state': self.state,
            'auth0Client': self.auth0_client
        }

        return f'{self.authorization_endpoint}?{urlencode(params)}'

    def __login(self) -> Tuple[str, str]:
        """
        Login

        workflow:
        - get authorize url -> this will redirect to login page
        - post login page with username and password -> this will redirect to redirect uri with code
        - post token endpoint with code -> this will return access token and refresh token
        """
        r_login_page = self.session.get(self.__prepare_authorize_url())
        r_redirect = self.session.post(r_login_page.url, {
            'username': self.username,
            'password': self.password,
            'state': parse_qs(urlparse(r_login_page.url).query)['state'][0]
        }, headers=self.headers)

        r_token = self.session.post(self.token_endpoint, {
            'client_id': self.client_id,
            'code_verifier': self.code_verifier,
            'grant_type': 'authorization_code',
            'code': parse_qs(urlparse(r_redirect.url).query)['code'][0],
            'redirect_uri': self.redirect_uri
        }, headers=self.headers)

        token = r_token.json()
        return token['access_token'], token['refresh_token']

    def __refresh(self) -> Tuple[str, str]:
        """
        Refresh access token

        workflow:
        - post token endpoint with refresh token -> this will return access token and refresh token
        """
        r_token = self.session.post(self.token_endpoint, {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }, headers=self.headers)

        token = r_token.json()

        return token['access_token'], token['refresh_token']

    def __auto_refresh(self) -> None:
        """
        Auto refresh access token
        If access token is expired, refresh it
        If refresh token is expired, login again
        """
        # check if access token is expired
        jwt_payload = jwt.decode(self.access_token, options={"verify_signature": False})
        if jwt_payload['exp'] < int(time.time()):
            # check if refresh token is expired
            jwt_payload = jwt.decode(self.refresh_token, options={"verify_signature": False})
            if jwt_payload['exp'] < int(time.time()):
                self.access_token, self.refresh_token = self.__refresh()
            else:
                self.access_token, self.refresh_token = self.__login()

        # if access token is not expired, do nothing

    @staticmethod
    def __rand(size=43):
        """
        Generate random string
        """
        t = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_~."
        e = ""
        random_values = [random.randint(0, 255) for _ in range(size)]
        for r in random_values:
            e += t[r % len(t)]

        return e

    @staticmethod
    def __btoa(s: str) -> str:
        """
        Encode string to base64
        """
        return base64.b64encode(s.encode('ascii')).decode('ascii')

    @staticmethod
    def __code_challenge(base64_string: str) -> str:
        """
        Generate code challenge from base64 string
        """
        hashed_code = hashlib.sha256(base64_string.encode('ascii')).digest()
        hashed_code_decode = base64.b64encode(hashed_code).decode('ascii')

        return hashed_code_decode.replace('+', '-').replace('/', '_').replace('=', '')


if __name__ == '__main__':
    raise Exception('This file is not meant to be executed')
