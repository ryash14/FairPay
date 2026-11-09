"""Turns a password and its salt into the form the database stores."""
import hashlib

from config import config


def hash_password(plain_password, password_salt):
    """PBKDF2-HMAC over the configured rounds, as lower-case hex. The database never holds a password."""
    digest = hashlib.pbkdf2_hmac(config.PASSWORD_HASH_ALGORITHM, plain_password.encode("utf-8"),
                                 password_salt.encode("utf-8"), config.PASSWORD_HASH_ROUNDS)
    return digest.hex()
