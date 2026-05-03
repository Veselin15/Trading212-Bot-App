"""CryptoStore round-trip for dual Trading212 key pairs."""

from __future__ import annotations

from pathlib import Path

from app.crypto_store import CryptoStore, SecretPayload


def test_crypto_store_roundtrip_practice_and_live(tmp_path: Path) -> None:
    store = CryptoStore(tmp_path)
    p = SecretPayload(
        practice_api_key="p-key",
        practice_secret_key="p-sec",
        live_api_key="l-key",
        live_secret_key=None,
    )
    store.save(p)
    out = store.load()
    assert out is not None
    assert out.practice_api_key == "p-key"
    assert out.practice_secret_key == "p-sec"
    assert out.live_api_key == "l-key"
    assert out.live_secret_key is None
