#!/usr/bin/env python3
"""Refresh ONLY development/test fake provisioning profiles for unsigned CI builds.

These profiles are not Apple-issued and cannot install/sign an app on devices.
"""
import datetime
import pathlib
import plistlib
import subprocess
import tempfile

root = pathlib.Path("build-system/fake-codesigning")
profiles = root / "profiles"
p12 = root / "certs" / "SelfSigned.p12"

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    identity = tmp / "identity.pem"
    subprocess.run([
        "openssl", "pkcs12", "-in", str(p12), "-out", str(identity),
        "-nodes", "-passin", "pass:"
    ], check=True)
    for profile in sorted(profiles.glob("*.mobileprovision")):
        decoded = tmp / "profile.plist"
        subprocess.run(["security", "cms", "-D", "-i", str(profile), "-o", str(decoded)], check=True)
        with decoded.open("rb") as f:
            data = plistlib.load(f)
        now = datetime.datetime.now(datetime.timezone.utc)
        data["CreationDate"] = now
        data["ExpirationDate"] = now + datetime.timedelta(days=365)
        with decoded.open("wb") as f:
            plistlib.dump(data, f)
        out = tmp / "signed.mobileprovision"
        subprocess.run([
            "openssl", "cms", "-sign", "-binary", "-nodetach",
            "-in", str(decoded), "-signer", str(identity), "-inkey", str(identity),
            "-outform", "DER", "-out", str(out)
        ], check=True)
        profile.write_bytes(out.read_bytes())
        print("Refreshed test profile:", profile.name)
