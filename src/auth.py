"""Authorization token handling."""
from functools import wraps

from flask import current_app, request
import jwt
from os import getenv

from exceptions import HTTPError
from utils import fetch_public_key, fetch_service_public_keys


def decode_user_token(token):
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


def decode_service_token(token):  # pragma: no cover
    """Decode OSIO service token."""
    # TODO: Merge this function and user token function once audience is removed from user tokens.
    if token is None:
        return {}

    if token.startswith('Bearer '):
        _, token = token.split(' ', 1)

    pub_keys = fetch_service_public_keys(current_app)
    decoded_token = None

    # Since we have multiple public keys, we need to verify against every public key.
    # Token can be decoded by any one of the available public keys.
    for pub_key in pub_keys:
        try:
            pub_key = pub_key.get("key", "")
            pub_key = '-----BEGIN PUBLIC KEY-----\n{pkey}\n-----END PUBLIC KEY-----'\
                .format(pkey=pub_key)
            decoded_token = jwt.decode(token, pub_key, algorithms=['RS256'])
        except jwt.InvalidTokenError:
            current_app.logger.error("Auth token couldn't be decoded for public key: {}"
                                     .format(pub_key))
            decoded_token = None

        if decoded_token:
            break

    if not decoded_token:
        raise jwt.InvalidTokenError('Auth token cannot be verified.')

    return decoded_token


def get_token_from_auth_header():
    """Get the authorization token read from the request header."""
    return request.headers.get('Authorization')


def get_audiences():
    """Retrieve all JWT audiences."""
    return getenv('BAYESIAN_JWT_AUDIENCE').split(',')


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
            decoded = decode_user_token(get_token_from_auth_header())
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


def service_token_required(view):  # pragma: no cover
    """Check if the request contains a valid service token."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        # Disable authentication for local setup
        if getenv('DISABLE_AUTHENTICATION') in ('1', 'True', 'true'):
            return view(*args, **kwargs)

        lgr = current_app.logger

        try:
            decoded = decode_service_token(get_token_from_auth_header())
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
