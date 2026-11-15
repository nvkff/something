import os
import zlib
import struct
import math
import shutil

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
rootProject.name = "ShaClock"
include(":app")
""")

# 3. app/build.gradle.kts
os.makedirs("app", exist_ok=True)
with open("app/build.gradle.kts", "w", encoding="utf-8") as f:
    f.write("""plugins {
    id("com.android.application")
}

android {
    namespace = "com.jeremysteckling.facerrel.watchfacepush.shaclock"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.jeremysteckling.facerrel.watchfacepush.shaclock"
        minSdk = 34
        targetSdk = 34
        versionCode = 4
        versionName = "4.0.0"
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
os.makedirs("app/src/main/res/drawable-nodpi", exist_ok=True)
os.makedirs("app/src/main/res/values", exist_ok=True)

if os.path.exists("app/src/main/assets/minecraft.ttf"):
    shutil.copy("app/src/main/assets/minecraft.ttf", "app/src/main/res/font/minecraft.ttf")

# 5. res/values/strings.xml
with open("app/src/main/res/values/strings.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Часы ЩА</string>
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
    <Editable value="false" />
</WatchFaceInfo>
""")

# Генератор PNG
def save_png(filename, w, h, pixel_func):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            r, g, b, a = pixel_func(x, y, w, h)
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

# 8. preview.png (450x450)
save_png("app/src/main/res/drawable-nodpi/preview.png", 450, 450, lambda x, y, w, h: 
    (255, 255, 255, 255) if 215 <= math.hypot(x-225, y-225) <= 222 else (0, 0, 0, 0)
)

# 9. Стрелки (аккуратный классический батон с острием)
# Часовая: ширина 14, длина 110 (точка вращения на y=95)
save_png("app/src/main/res/drawable-nodpi/hand_hour.png", 14, 110, lambda x, y, w, h:
    (255, 255, 255, 255) if 2 <= x <= 11 and 5 <= y <= 95 else (0, 0, 0, 0)
)

# Минутная: ширина 10, длина 165 (точка вращения на y=150)
save_png("app/src/main/res/drawable-nodpi/hand_minute.png", 10, 165, lambda x, y, w, h:
    (255, 255, 255, 255) if 2 <= x <= 7 and 5 <= y <= 150 else (0, 0, 0, 0)
)

# Секундная: ширина 4, длина 190 (красная, точка вращения на y=160)
save_png("app/src/main/res/drawable-nodpi/hand_second.png", 4, 190, lambda x, y, w, h:
    (255, 59, 48, 255) if 1 <= x <= 2 and 5 <= y <= 160 else (0, 0, 0, 0)
)

# Центральная ось
save_png("app/src/main/res/drawable-nodpi/hand_cap.png", 18, 18, lambda x, y, w, h:
    (255, 255, 255, 255) if math.hypot(x-9, y-9) <= 8 and math.hypot(x-9, y-9) >= 2 else (0, 0, 0, 0)
)

# 10. Расчёт 12 надписей "ща" ближе к безелю (R=194)
dial_marks = []
radius = 194
for i in range(12):
    angle_deg = i * 30
    angle_rad = math.radians(angle_deg)
    cx = 225 + radius * math.sin(angle_rad)
    cy = 225 - radius * math.cos(angle_rad)
    x = int(cx - 35)
    y = int(cy - 20)
    
    dial_marks.append(f"""            <PartText x="{x}" y="{y}" width="70" height="40">
                <Text align="CENTER">
                    <Font family="minecraft" size="32" color="#ffffffff" weight="NORMAL">ща</Font>
                </Text>
            </PartText>""")

# 11. res/raw/watchface.xml по официальной структуре WFF
watchface_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
    <Metadata key="CLOCK_TYPE" value="ANALOG" />
    <Metadata key="PREVIEW_TIME" value="10:10:30" />

    <Scene backgroundColor="#ff000000">

        <!-- 12 надписей "ща" -->
        <Group x="0" y="0" width="450" height="450">
{chr(10).join(dial_marks)}
        </Group>

        <!-- Аналоговые стрелки -->
        <AnalogClock x="0" y="0" width="450" height="450">
            <HourHand x="218" y="130" width="14" height="110" pivotX="0.5" pivotY="0.864">
                <PartImage resource="hand_hour" x="0" y="0" width="14" height="110" />
            </HourHand>
            <MinuteHand x="220" y="75" width="10" height="165" pivotX="0.5" pivotY="0.909">
                <PartImage resource="hand_minute" x="0" y="0" width="10" height="165" />
            </MinuteHand>
            <SecondHand x="223" y="65" width="4" height="190" pivotX="0.5" pivotY="0.842">
                <Variant mode="AMBIENT" target="alpha" value="0" />
                <PartImage resource="hand_second" x="0" y="0" width="4" height="190" />
            </SecondHand>
        </AnalogClock>

        <!-- Центральная заклепка -->
        <PartImage resource="hand_cap" x="216" y="216" width="18" height="18" />

    </Scene>
</WatchFace>
"""

with open("app/src/main/res/raw/watchface.xml", "w", encoding="utf-8") as f:
    f.write(watchface_xml)
