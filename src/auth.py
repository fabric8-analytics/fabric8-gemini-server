"""Authorization token handling."""
from functools import wraps

from flask import current_app, request
import jwt
import requests
from os import getenv


from exceptions import HTTPError
from utils import fetch_public_key


def decode_token(token):
    """Decode the authorization token read from the request header."""
    if token is None:
        return {}

    if token.startswith('Bearer '):
        _, token = token.split(' ', 1)

    pub_key = fetch_public_key(current_app)
    audiences = get_audiences()
    decoded_token = None

    for aud in audiences:
        try:
            decoded_token = jwt.decode(token, pub_key, algorithms=['RS256'], audience=aud)
        except jwt.InvalidTokenError:
            current_app.logger.error('Auth Token could not be decoded for audience {}'.format(aud))
            decoded_token = None

        if decoded_token is not None:
            break

    if decoded_token is None:
        raise jwt.InvalidTokenError('Auth token audience cannot be verified.')

    return decoded_token


def get_token_from_auth_header():
    """Get the authorization token read from the request header."""
    return request.headers.get('Authorization')


def get_audiences():
    """Retrieve all JWT audiences."""
    return getenv('BAYESIAN_JWT_AUDIENCE').split(',')


def init_auth_sa_token():
    """Initiate a service token from auth service."""
    auth_server_url = getenv('AUTH_SERVER_URL', 'https://auth.openshift.io')
    endpoint = '{url}/api/token'.format(url=auth_server_url)

    client_id = getenv('SA_CLIENT_ID', '37df5ca3-a075-4ba3-8756-9d4afafd6884')
    client_secret = getenv('SA_CLIENT_SECRET', 'secret')

    payload = {"grant_type": "client_credentials",
               "client_id": client_id,
               "client_secret": client_secret}
    try:
        resp = requests.post(endpoint, json=payload)
    except requests.exceptions.RequestException as e:
        raise e

    if resp.status_code == 200:
        data = resp.json()
        try:
            access_token = data['access_token']
        except IndexError as e:
            raise requests.exceptions.RequestException
        return access_token
    else:
        raise requests.exceptions.RequestException


def login_required(view):  # pragma: no cover
    """Check if the login is required and if the user can be authorized."""
    # NOTE: the actual authentication 401 failures are commented out for now and will be
    # uncommented as soon as we know everything works fine; right now this is purely for
    # being able to tail logs and see if stuff is going fine
    @wraps(view)
    def wrapper(*args, **kwargs):
        # Disable authentication for local setup
        if getenv('DISABLE_AUTHENTICATION') in ('1', 'True', 'true'):
            return view(*args, **kwargs)

        lgr = current_app.logger

        try:
            decoded = decode_token(get_token_from_auth_header())
            if not decoded:
                lgr.exception('Provide an Authorization token with the API request')
                raise HTTPError(401, 'Authentication failed - token missing')

            lgr.info('Successfuly authenticated user {e} using JWT'.
                     format(e=decoded.get('email')))
        except jwt.ExpiredSignatureError as exc:
            lgr.exception('Expired JWT token')
            raise HTTPError(401, 'Authentication failed - token has expired') from exc
        except Exception as exc:
            lgr.exception('Failed decoding JWT token')
            raise HTTPError(401, 'Authentication failed - could not decode JWT token') from exc

        return view(*args, **kwargs)
    return wrapper
