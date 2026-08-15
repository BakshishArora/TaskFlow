from taskflow.utils import passwords


def test_hash_and_verify():
    hashed = passwords.hash_password("secret")
    assert hashed != "secret"
    assert passwords.verify_password("secret", hashed)


def test_verify_wrong_password_fails():
    hashed = passwords.hash_password("secret")
    assert not passwords.verify_password("wrong", hashed)


def test_hashes_are_salted():
    assert passwords.hash_password("secret") != passwords.hash_password("secret")
