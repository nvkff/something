import os
import json
import zlib
import struct
import zipfile
import urllib.request
import shutil

# 0. Встроенный чистый PNG-декодер и энкодер (без Pillow и без pip)
def read_png_rgba(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    idat = bytearray()
    plte = None
    trns = None
    w = h = depth = ctype = 0
    while pos < len(data):
        length = struct.unpack("!I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            w, h, depth, ctype, _, _, _ = struct.unpack("!IIBBBBB", chunk_data)
        elif tag == b"PLTE":
            plte = chunk_data
        elif tag == b"tRNS":
            trns = chunk_data
        elif tag == b"IDAT":
            idat.extend(chunk_data)
        elif tag == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    bpp_map = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    row_bytes = (w * bpp_map[ctype] * depth + 7) // 8
    filt_bpp = max(1, (bpp_map[ctype] * depth + 7) // 8)

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        return b if pb <= pc else c

    rows = []
    idx = 0
    prev = bytearray(row_bytes)
    for _ in range(h):
        ftype = raw[idx]
        idx += 1
        scan = bytearray(raw[idx:idx + row_bytes])
        idx += row_bytes
        for i in range(row_bytes):
            a = scan[i - filt_bpp] if i >= filt_bpp else 0
            b = prev[i]
            c = prev[i - filt_bpp] if i >= filt_bpp else 0
            if ftype == 1:
                scan[i] = (scan[i] + a) & 0xff
            elif ftype == 2:
                scan[i] = (scan[i] + b) & 0xff
            elif ftype == 3:
                scan[i] = (scan[i] + ((a + b) >> 1)) & 0xff
            elif ftype == 4:
                scan[i] = (scan[i] + paeth(a, b, c)) & 0xff
        prev = scan
        rows.append(scan)

    pixels = []
    for y in range(h):
        row = rows[y]
        prow = []
        if ctype == 6 and depth == 8:
            for x in range(w):
                prow.append((row[x * 4], row[x * 4 + 1], row[x * 4 + 2], row[x * 4 + 3]))
        elif ctype == 2 and depth == 8:
            for x in range(w):
                prow.append((row[x * 3], row[x * 3 + 1], row[x * 3 + 2], 255))
        elif ctype == 4 and depth == 8:
            for x in range(w):
                g = row[x * 2]
                prow.append((g, g, g, row[x * 2 + 1]))
        elif ctype == 3:
            if depth == 8:
                vals = list(row)
            else:
                vals = []
                mask = (1 << depth) - 1
                for byte in row:
                    for shift in range(8 - depth, -1, -depth):
                        vals.append((byte >> shift) & mask)
            for x in range(w):
                pi = vals[x]
                r, g, b = plte[pi * 3], plte[pi * 3 + 1], plte[pi * 3 + 2]
                a = trns[pi] if (trns is not None and pi < len(trns)) else 255
                prow.append((r, g, b, a))
        elif ctype == 0:
            if depth == 8:
                vals = list(row)
            else:
                vals = []
                mask = (1 << depth) - 1
                for byte in row:
                    for shift in range(8 - depth, -1, -depth):
                        vals.append((byte >> shift) & mask)
            maxv = (1 << depth) - 1
            for x in range(w):
                g = vals[x] * 255 // maxv
                prow.append((g, g, g, 255))
        pixels.append(prow)
    return w, h, pixels

def write_png_rgba(filename, w, h, pixels):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for r, g, b, a in pixels[y]:
            raw.extend((r, g, b, a))

    def chunk(t, d):
        return struct.pack("!I", len(d)) + t + d + struct.pack("!I", zlib.crc32(t + d) & 0xffffffff)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    with open(filename, "wb") as f:
        f.write(png)

def upscale_nearest(pixels, src_w, src_h, dst_w, dst_h):
    out = []
    for y in range(dst_h):
        sy = (y * src_h) // dst_h
        srow = pixels[sy]
        out.append([srow[(x * src_w) // dst_w] for x in range(dst_w)])
    return out

# 1. Корневой build.gradle.kts
with open("build.gradle.kts", "w", encoding="utf-8") as f:
    f.write("""plugins {
    id("com.android.application") version "8.4.1" apply false
}
""")

# 2. settings.gradle.kts
with open("settings.gradle.kts", "w", encoding="utf-8") as f:
    f.write("""pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "MinecraftClock"
include(":app")
""")

# 3. app/build.gradle.kts
os.makedirs("app", exist_ok=True)
with open("app/build.gradle.kts", "w", encoding="utf-8") as f:
    f.write("""plugins {
    id("com.android.application")
}

android {
    namespace = "com.jeremysteckling.facerrel.watchfacepush.mcclock"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.jeremysteckling.facerrel.watchfacepush.mcclock"
        minSdk = 34
        targetSdk = 34
        versionCode = 2
        versionName = "2.0.0"
    }

    signingConfigs {
        create("release") {
            storeFile = rootProject.file("release.keystore")
            storePassword = "123456"
            keyAlias = "watchkey"
            keyPassword = "123456"
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = false
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
""")

# 4. Очистка и создание папок
if os.path.exists("app/src/main/java"):
    shutil.rmtree("app/src/main/java")
if os.path.exists("app/src/main/res"):
    shutil.rmtree("app/src/main/res")

os.makedirs("app/src/main/res/xml", exist_ok=True)
os.makedirs("app/src/main/res/raw", exist_ok=True)
os.makedirs("app/src/main/res/font", exist_ok=True)
os.makedirs("app/src/main/res/drawable", exist_ok=True)
os.makedirs("app/src/main/res/values", exist_ok=True)

if os.path.exists("app/src/main/assets/minecraft.ttf"):
    shutil.copy("app/src/main/assets/minecraft.ttf", "app/src/main/res/font/minecraft.ttf")

# 5. res/values/strings.xml
with open("app/src/main/res/values/strings.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Minecraft</string>
    <string name="show_digits_label">Цифры времени</string>
    <string name="digits_off">1. Чистый (как в игре)</string>
    <string name="digits_on">2. С цифрами снизу</string>
</resources>
""")

# 6. AndroidManifest.xml
with open("app/src/main/AndroidManifest.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature
        android:name="android.hardware.type.watch"
        android:required="true" />

    <application
        android:extractNativeLibs="false"
        android:hasCode="false"
        android:label="@string/app_name">

        <property
            android:name="com.google.wear.watchface.format.version"
            android:value="1" />

    </application>
</manifest>
""")

# 7. res/xml/watch_face_info.xml
with open("app/src/main/res/xml/watch_face_info.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<WatchFaceInfo>
    <Preview value="@drawable/preview" />
    <Editable value="true" />
</WatchFaceInfo>
""")

# 8. Скачивание оригинальных 64 текстур clock_00..clock_63 с сервера Mojang
manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
with urllib.request.urlopen(manifest_url) as resp:
    manifest = json.loads(resp.read().decode("utf-8"))

latest_release = manifest["latest"]["release"]
version_url = next(v["url"] for v in manifest["versions"] if v["id"] == latest_release)

with urllib.request.urlopen(version_url) as resp:
    version_data = json.loads(resp.read().decode("utf-8"))

client_jar_url = version_data["downloads"]["client"]["url"]
jar_path = "/tmp/mc_client.jar"
urllib.request.urlretrieve(client_jar_url, jar_path)

preview_448 = None
with zipfile.ZipFile(jar_path, "r") as zf:
    names = zf.namelist()
    for k in range(64):
        target_suffix = f"textures/item/clock_{k:02d}.png"
        entry = next(n for n in names if n.endswith(target_suffix))
        raw_png = zf.read(entry)
        sw, sh, spixels = read_png_rgba(raw_png)
        scaled = upscale_nearest(spixels, sw, sh, 448, 448)
        write_png_rgba(f"app/src/main/res/drawable/clock_{k:02d}.png", 448, 448, scaled)
        if k == 0:
            preview_448 = scaled

# Генерируем preview.png (450x450 с черным фоном и clock_00 в центре)
prev_pixels = [[(0, 0, 0, 255)] * 450 for _ in range(450)]
for y in range(448):
    for x in range(448):
        r, g, b, a = preview_448[y][x]
        if a > 0:
            prev_pixels[y + 1][x + 1] = (r, g, b, 255)
write_png_rgba("app/src/main/res/drawable/preview.png", 450, 450, prev_pixels)

# 9. Генерация watchface.xml со всеми 64 оригинальными кадрами
expressions = []
compares = []

for k in range(64):
    expressions.append(
        f'                <Expression name="f_{k}">floor(((([HOUR_0_23] * 60 + [MINUTE] + 731) % 1440) * 64) / 1440) == {k}</Expression>'
    )
    compares.append(f"""            <Compare expression="f_{k}">
                <Group x="1" y="1" width="448" height="448">
                    <PartImage x="0" y="0" width="448" height="448">
                        <Image resource="clock_{k:02d}" />
                    </PartImage>
                </Group>
            </Compare>""")

watchface_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
    <Metadata key="CLOCK_TYPE" value="ANALOG" />
    <Metadata key="PREVIEW_TIME" value="12:00:00" />

    <UserConfigurations>
        <ListConfiguration id="show_digits" displayName="show_digits_label" defaultValue="0">
            <ListOption id="0" displayName="digits_off" />
            <ListOption id="1" displayName="digits_on" />
        </ListConfiguration>
    </UserConfigurations>

    <Scene backgroundColor="#ff000000">

        <!-- 64 оригинальных спрайта из Minecraft (в AOD приглушаются для экономии экрана) -->
        <Group x="0" y="0" width="450" height="450">
            <Variant mode="AMBIENT" target="alpha" value="110" />
            <Condition>
                <Expressions>
{chr(10).join(expressions)}
                </Expressions>
{chr(10).join(compares)}
            </Condition>
        </Group>

        <!-- Опциональные цифры времени снизу -->
        <ListConfiguration id="show_digits">
            <ListOption id="0">
                <Group x="0" y="0" width="1" height="1" />
            </ListOption>
            <ListOption id="1">
                <Group x="0" y="0" width="450" height="450">
                    <DigitalClock x="125" y="290" width="200" height="58">
                        <TimeText x="3" y="3" width="194" height="52" format="HH:mm" hourFormat="24" align="CENTER">
                            <Font family="minecraft" size="34" color="#ff3a2204" />
                        </TimeText>
                        <TimeText x="0" y="0" width="194" height="52" format="HH:mm" hourFormat="24" align="CENTER">
                            <Font family="minecraft" size="34" color="#ffffffff" />
                        </TimeText>
                    </DigitalClock>
                </Group>
            </ListOption>
        </ListConfiguration>

    </Scene>
</WatchFace>
"""

with open("app/src/main/res/raw/watchface.xml", "w", encoding="utf-8") as f:
    f.write(watchface_xml)
