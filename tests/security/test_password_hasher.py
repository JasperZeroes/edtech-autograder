from app.infrastructure.security import Argon2PasswordHasher


def test_hash_does_not_store_plain_password() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert password_hash.startswith("$argon2")


def test_verify_accepts_correct_password() -> None:
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash("password123")

    assert hasher.verify("password123", password_hash) is True


def test_verify_rejects_incorrect_password() -> None:
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash("password123")

    assert hasher.verify("wrong-password", password_hash) is False


def test_hashes_use_random_salts() -> None:
    hasher = Argon2PasswordHasher()

    first = hasher.hash("password123")
    second = hasher.hash("password123")

    assert first != second


def test_hasher_supports_128_character_passwords() -> None:
    hasher = Argon2PasswordHasher()
    password = "x" * 128

    password_hash = hasher.hash(password)

    assert hasher.verify(password, password_hash) is True


def test_verify_rejects_malformed_hash() -> None:
    hasher = Argon2PasswordHasher()

    assert hasher.verify("password123", "not-a-valid-hash") is False
