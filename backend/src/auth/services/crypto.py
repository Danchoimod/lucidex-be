from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

# Đưa BcryptHasher lên trước Argon2Hasher để nó dùng Bcrypt làm mặc định (nhẹ máy, không bị lỗi RAM)
password_hash = PasswordHash((BcryptHasher(), Argon2Hasher()))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its hash."""
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash from a plain text password."""
    return password_hash.hash(password)