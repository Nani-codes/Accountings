from app.services.tally_crypto import hash_secret, secrets_equal


def test_hash_secret_stable(monkeypatch):
    monkeypatch.setenv("TALLY_TOKEN_PEPPER", "test-pepper")
    from app.config import Settings
    import app.services.tally_crypto as crypto

    crypto.settings = Settings(_env_file=None)
    a = hash_secret("abc-123")
    b = hash_secret("abc-123")
    assert a == b
    assert a != "abc-123"
    assert secrets_equal("abc-123", a) is True
    assert secrets_equal("wrong", a) is False
