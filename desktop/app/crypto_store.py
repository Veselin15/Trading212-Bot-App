from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _get_machine_guid() -> str:
    # Windows-specific: MachineGuid is stable per OS install.
    try:
        import winreg  # type: ignore

        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(value)
    except Exception:
        return ""


def _derive_fernet_key(*, machine_guid: str, salt: bytes) -> bytes:
    material = (machine_guid or "unknown-machine").encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(material))


@dataclass(frozen=True)
class SecretPayload:
    t212_api_key: str
    t212_secret_key: str | None = None


class CryptoStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._salt_path = self.base_dir / "salt.bin"
        self._cipher_path = self.base_dir / "secrets.bin"

    def _load_or_create_salt(self) -> bytes:
        if self._salt_path.exists():
            return self._salt_path.read_bytes()
        salt = os.urandom(16)
        self._salt_path.write_bytes(salt)
        return salt

    def _fernet(self) -> Fernet:
        salt = self._load_or_create_salt()
        machine_guid = _get_machine_guid()
        key = _derive_fernet_key(machine_guid=machine_guid, salt=salt)
        return Fernet(key)

    def save(self, payload: SecretPayload) -> None:
        f = self._fernet()
        raw = json.dumps({"t212_api_key": payload.t212_api_key, "t212_secret_key": payload.t212_secret_key}).encode(
            "utf-8"
        )
        token = f.encrypt(raw)
        self._cipher_path.write_bytes(token)

    def load(self) -> SecretPayload | None:
        if not self._cipher_path.exists():
            return None
        f = self._fernet()
        token = self._cipher_path.read_bytes()
        raw = f.decrypt(token)
        obj = json.loads(raw.decode("utf-8"))
        return SecretPayload(t212_api_key=str(obj.get("t212_api_key") or ""), t212_secret_key=obj.get("t212_secret_key"))

    def clear(self) -> None:
        self._cipher_path.unlink(missing_ok=True)
