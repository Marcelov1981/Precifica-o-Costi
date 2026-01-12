import os
import hashlib
import secrets

def hash_password(password):
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${dk.hex()}"

def verify_password(password, stored):
    try:
        salt, hexhash = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return dk.hex() == hexhash

def is_master_password(password):
    mp = os.environ.get("MASTER_PASSWORD")
    return bool(mp) and password == mp
