"""Generate test fixture images for NomadShots test suite.

Run from workspace root:
    python tests/generate_fixtures.py

Writes all fixture files to tests/fixtures/.
"""
import io
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# GPS coordinates: Ho Chi Minh City
HCM_LAT = 10.7626
HCM_LON = 106.6602


def _deg_to_dms_rational(deg: float):
    """Convert decimal degrees to (degrees, minutes, seconds) as piexif rationals."""
    import piexif

    d = int(abs(deg))
    m_float = (abs(deg) - d) * 60
    m = int(m_float)
    s_float = (m_float - m) * 60
    # Store as rational: numerator/denominator = value * 1e6 / 1e6
    return (
        (d, 1),
        (m, 1),
        (int(s_float * 1_000_000), 1_000_000),
    )


def make_gps_jpeg():
    """JPEG with GPS coordinates + device info."""
    from PIL import Image
    import piexif

    img = Image.new("RGB", (64, 64), color=(128, 64, 32))

    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: _deg_to_dms_rational(HCM_LAT),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: _deg_to_dms_rational(HCM_LON),
    }
    zeroth_ifd = {
        piexif.ImageIFD.Make: b"Apple",
        piexif.ImageIFD.Model: b"iPhone 15 Pro",
        piexif.ImageIFD.Software: b"iOS 17.0",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: b"2024:01:15 10:30:00",
    }
    exif_bytes = piexif.dump({
        "0th": zeroth_ifd,
        "Exif": exif_ifd,
        "GPS": gps_ifd,
    })

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes)
    out = FIXTURES_DIR / "gps_jpeg.jpg"
    out.write_bytes(buf.getvalue())
    print(f"Created {out}")


def make_no_gps_jpeg():
    """JPEG with device info but NO GPS."""
    from PIL import Image
    import piexif

    img = Image.new("RGB", (64, 64), color=(32, 128, 64))

    zeroth_ifd = {
        piexif.ImageIFD.Make: b"Samsung",
        piexif.ImageIFD.Model: b"Galaxy S23",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: b"2024:03:20 08:00:00",
    }
    exif_bytes = piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd})

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes)
    out = FIXTURES_DIR / "no_gps.jpg"
    out.write_bytes(buf.getvalue())
    print(f"Created {out}")


def make_minimal_jpeg():
    """Minimal JPEG with NO EXIF at all."""
    from PIL import Image

    img = Image.new("RGB", (32, 32), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    out = FIXTURES_DIR / "minimal.jpg"
    out.write_bytes(buf.getvalue())
    print(f"Created {out}")


def make_gps_heic():
    """HEIC file with GPS + device info (via pillow-heif + exiftool injection)."""
    try:
        import pillow_heif
        from PIL import Image

        pillow_heif.register_heif_opener()

        img = Image.new("RGB", (64, 64), color=(64, 32, 128))
        out = FIXTURES_DIR / "gps_heic.heic"

        heif_file = pillow_heif.from_pillow(img)
        heif_file.save(str(out))
        print(f"Created base HEIC {out}")

    except Exception as e:
        print(f"WARNING: Could not create HEIC with pillow-heif: {e}")
        print("Falling back to creating a minimal HEIC stub via exiftool")
        # Create a small valid JPEG and convert/inject HEIC metadata via exiftool
        # Instead, create minimal JPEG and rename + tag
        from PIL import Image
        import piexif

        img = Image.new("RGB", (64, 64), color=(64, 32, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        out = FIXTURES_DIR / "gps_heic.heic"
        out.write_bytes(buf.getvalue())
        print(f"Created HEIC fallback (JPEG bytes) {out}")

    # Inject GPS + device info via exiftool
    out = FIXTURES_DIR / "gps_heic.heic"
    cmd = [
        "exiftool",
        "-overwrite_original",
        f"-GPSLatitude={HCM_LAT}",
        f"-GPSLongitude={HCM_LON}",
        "-GPSLatitudeRef=N",
        "-GPSLongitudeRef=E",
        "-Make=Apple",
        "-Model=iPhone 15 Pro",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARNING: exiftool injection failed: {result.stderr.strip()}")
    else:
        print(f"Injected GPS+device into {out}")


def make_gps_upper_heic():
    """Copy of gps_heic.heic with uppercase extension."""
    src = FIXTURES_DIR / "gps_heic.heic"
    dst = FIXTURES_DIR / "GPS_UPPER.HEIC"
    shutil.copy2(src, dst)
    print(f"Created {dst}")


def make_corrupt_jpeg():
    """A few KB of random garbage bytes with .jpg extension."""
    import os

    data = os.urandom(4096)
    out = FIXTURES_DIR / "corrupt.jpg"
    out.write_bytes(data)
    print(f"Created {out}")


def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing fixtures to: {FIXTURES_DIR}")

    make_gps_jpeg()
    make_no_gps_jpeg()
    make_minimal_jpeg()
    make_gps_heic()
    make_gps_upper_heic()
    make_corrupt_jpeg()

    print("\nAll fixtures created.")
    for f in sorted(FIXTURES_DIR.iterdir()):
        print(f"  {f.name}: {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
