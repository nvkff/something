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
        versionCode = 6
        versionName = "6.0.0"
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
    <string name="app_name">Часы ЩА</string>
    <string name="hands_style_label">Стиль стрелок</string>
    <string name="style_pixel">1. Пиксельные</string>
    <string name="style_sword">2. Мечи</string>
    <string name="style_classic">3. Минимализм</string>
    <string name="style_skeleton">4. Скелетоны</string>
    <string name="style_needle">5. Тонкие иглы</string>
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
save_png("app/src/main/res/drawable/preview.png", 450, 450, lambda x, y, w, h:
    (255, 255, 255, 255) if 215 <= math.hypot(x - 225, y - 225) <= 222 else (0, 0, 0, 255)
)

# 9. Стрелки
# Стиль 0: Настоящие блочные пиксельные стрелки (сетка 4x4 пикселя)
# Часовая 24x132 (6x33 блоков, ось вращения на y=110 -> pivotY=0.833)
def pixel_h(x, y, w, h):
    bx, by = x // 4, y // 4
    if by in (0, 1) and bx in (2, 3): return (255, 255, 255, 255)
    if by in (2, 3) and bx in (1, 2, 3, 4): return (255, 255, 255, 255)
    if by in (4, 5) and bx in (0, 1, 2, 3, 4, 5): return (255, 255, 255, 255)
    if 6 <= by <= 25:
        if bx in (1, 4): return (255, 255, 255, 255)
        if bx in (2, 3): return (0, 0, 0, 255)
    if 26 <= by <= 31 and bx in (1, 2, 3, 4): return (255, 255, 255, 255)
    return (0, 0, 0, 0)
save_png("app/src/main/res/drawable/h_pixel_h.png", 24, 132, pixel_h)

# Минутная 20x180 (5x45 блоков, ось вращения на y=155 -> pivotY=0.861)
def pixel_m(x, y, w, h):
    bx, by = x // 4, y // 4
    if by in (0, 1) and bx == 2: return (255, 255, 255, 255)
    if by in (2, 3) and bx in (1, 2, 3): return (255, 255, 255, 255)
    if by in (4, 5) and bx in (0, 1, 2, 3, 4): return (255, 255, 255, 255)
    if 6 <= by <= 36:
        if bx in (1, 3): return (255, 255, 255, 255)
        if bx == 2: return (0, 0, 0, 255)
    if 37 <= by <= 43 and bx in (1, 2, 3): return (255, 255, 255, 255)
    return (0, 0, 0, 0)
save_png("app/src/main/res/drawable/h_pixel_m.png", 20, 180, pixel_m)

save_png("app/src/main/res/drawable/h_pixel_s.png", 8, 210, lambda x, y, w, h:
    (255, 59, 48, 255) if 2 <= x <= 5 and 4 <= y <= 204 else (0, 0, 0, 0)
)

# Стиль 1: Мечи (Дайверские с острием)
def sword_h(x, y, w, h):
    if y < 6 or y > 125: return (0, 0, 0, 0)
    half_w = 7.0 if y > 28 else (y - 6) * (7.0 / 22.0)
    return (255, 255, 255, 255) if abs(x - 9.5) <= half_w else (0, 0, 0, 0)
save_png("app/src/main/res/drawable/h_sword_h.png", 20, 130, sword_h)

def sword_m(x, y, w, h):
    if y < 6 or y > 175: return (0, 0, 0, 0)
    half_w = 5.0 if y > 26 else (y - 6) * (5.0 / 20.0)
    return (255, 255, 255, 255) if abs(x - 7.5) <= half_w else (0, 0, 0, 0)
save_png("app/src/main/res/drawable/h_sword_m.png", 16, 180, sword_m)

save_png("app/src/main/res/drawable/h_sword_s.png", 8, 210, lambda x, y, w, h:
    (255, 204, 0, 255) if 3 <= x <= 4 and 4 <= y <= 204 else (0, 0, 0, 0)
)

# Стиль 2: Минимализм (Батоны)
save_png("app/src/main/res/drawable/h_classic_h.png", 20, 130, lambda x, y, w, h:
    (255, 255, 255, 255) if 6 <= x <= 13 and 10 <= y <= 122 else (0, 0, 0, 0)
)
save_png("app/src/main/res/drawable/h_classic_m.png", 16, 180, lambda x, y, w, h:
    (255, 255, 255, 255) if 5 <= x <= 10 and 8 <= y <= 172 else (0, 0, 0, 0)
)
save_png("app/src/main/res/drawable/h_classic_s.png", 8, 210, lambda x, y, w, h:
    (255, 59, 48, 255) if 3 <= x <= 4 and 4 <= y <= 204 else (0, 0, 0, 0)
)

# Стиль 3: Скелетоны (Полые рамки)
def skel_h(x, y, w, h):
    if 4 <= x <= 15 and 8 <= y <= 125:
        if 7 <= x <= 12 and 18 <= y <= 102: return (0, 0, 0, 0)
        return (255, 255, 255, 255)
    return (0, 0, 0, 0)
save_png("app/src/main/res/drawable/h_skel_h.png", 20, 130, skel_h)

def skel_m(x, y, w, h):
    if 4 <= x <= 11 and 8 <= y <= 175:
        if 6 <= x <= 9 and 18 <= y <= 148: return (0, 0, 0, 0)
        return (255, 255, 255, 255)
    return (0, 0, 0, 0)
save_png("app/src/main/res/drawable/h_skel_m.png", 16, 180, skel_m)

save_png("app/src/main/res/drawable/h_skel_s.png", 8, 210, lambda x, y, w, h:
    (0, 229, 255, 255) if 3 <= x <= 4 and 4 <= y <= 204 else (0, 0, 0, 0)
)

# Стиль 4: Тонкие иглы
save_png("app/src/main/res/drawable/h_needle_h.png", 20, 130, lambda x, y, w, h:
    (255, 255, 255, 255) if 8 <= x <= 11 and 8 <= y <= 125 else (0, 0, 0, 0)
)
save_png("app/src/main/res/drawable/h_needle_m.png", 16, 180, lambda x, y, w, h:
    (255, 255, 255, 255) if 7 <= x <= 8 and 6 <= y <= 175 else (0, 0, 0, 0)
)
save_png("app/src/main/res/drawable/h_needle_s.png", 8, 210, lambda x, y, w, h:
    (255, 59, 48, 255) if 3 <= x <= 4 and 4 <= y <= 204 else (0, 0, 0, 0)
)

# Центральная заглушка (кольцо)
save_png("app/src/main/res/drawable/hand_cap.png", 20, 20, lambda x, y, w, h:
    (255, 255, 255, 255) if 3 <= math.hypot(x - 9.5, y - 9.5) <= 8 else ((0, 0, 0, 255) if math.hypot(x - 9.5, y - 9.5) < 3 else (0, 0, 0, 0))
)

# 10. Расчёт 12 надписей "ща" близко к безелю (R=192px)
dial_marks = []
radius = 192
for i in range(12):
    angle_deg = i * 30
    angle_rad = math.radians(angle_deg)
    cx = 225 + radius * math.sin(angle_rad)
    cy = 225 - radius * math.cos(angle_rad)
    x = int(cx - 32)
    y = int(cy - 20)

    dial_marks.append(f"""            <PartText x="{x}" y="{y}" width="64" height="40" alpha="255">
                <Variant mode="AMBIENT" target="alpha" value="0" />
                <Text align="CENTER">
                    <Font family="minecraft" size="32" color="#ffffffff">ща</Font>
                </Text>
            </PartText>""")

    dial_marks.append(f"""            <PartText x="{x}" y="{y}" width="64" height="40" alpha="0">
                <Variant mode="AMBIENT" target="alpha" value="255" />
                <Text align="CENTER">
                    <Font family="minecraft" size="32" color="#00000000">
                        <Outline color="#ffffffff" width="1">ща</Outline>
                    </Font>
                </Text>
            </PartText>""")

# 11. Валидный watchface.xml по спецификации WFF v1
watchface_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
    <Metadata key="CLOCK_TYPE" value="ANALOG" />
    <Metadata key="PREVIEW_TIME" value="10:10:30" />

    <UserConfigurations>
        <ListConfiguration id="hands_style" displayName="hands_style_label" defaultValue="0">
            <ListOption id="0" displayName="style_pixel" />
            <ListOption id="1" displayName="style_sword" />
            <ListOption id="2" displayName="style_classic" />
            <ListOption id="3" displayName="style_skeleton" />
            <ListOption id="4" displayName="style_needle" />
        </ListConfiguration>
    </UserConfigurations>

    <Scene backgroundColor="#ff000000">

        <!-- 12 одинаковых надписей "ща" по кругу -->
        <Group x="0" y="0" width="450" height="450">
{chr(10).join(dial_marks)}
        </Group>

        <!-- Выбор стиля стрелок -->
        <ListConfiguration id="hands_style">
            <ListOption id="0">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_pixel_h" x="213" y="115" width="24" height="132" pivotX="0.5" pivotY="0.833" />
                    <MinuteHand resource="h_pixel_m" x="215" y="70" width="20" height="180" pivotX="0.5" pivotY="0.861" />
                    <SecondHand resource="h_pixel_s" x="221" y="50" width="8" height="210" pivotX="0.5" pivotY="0.833">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </ListOption>
            <ListOption id="1">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_sword_h" x="215" y="115" width="20" height="130" pivotX="0.5" pivotY="0.846" />
                    <MinuteHand resource="h_sword_m" x="217" y="70" width="16" height="180" pivotX="0.5" pivotY="0.861" />
                    <SecondHand resource="h_sword_s" x="221" y="50" width="8" height="210" pivotX="0.5" pivotY="0.833">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </ListOption>
            <ListOption id="2">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_classic_h" x="215" y="115" width="20" height="130" pivotX="0.5" pivotY="0.846" />
                    <MinuteHand resource="h_classic_m" x="217" y="70" width="16" height="180" pivotX="0.5" pivotY="0.861" />
                    <SecondHand resource="h_classic_s" x="221" y="50" width="8" height="210" pivotX="0.5" pivotY="0.833">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </ListOption>
            <ListOption id="3">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_skel_h" x="215" y="115" width="20" height="130" pivotX="0.5" pivotY="0.846" />
                    <MinuteHand resource="h_skel_m" x="217" y="70" width="16" height="180" pivotX="0.5" pivotY="0.861" />
                    <SecondHand resource="h_skel_s" x="221" y="50" width="8" height="210" pivotX="0.5" pivotY="0.833">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </ListOption>
            <ListOption id="4">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_needle_h" x="215" y="115" width="20" height="130" pivotX="0.5" pivotY="0.846" />
                    <MinuteHand resource="h_needle_m" x="217" y="70" width="16" height="180" pivotX="0.5" pivotY="0.861" />
                    <SecondHand resource="h_needle_s" x="221" y="50" width="8" height="210" pivotX="0.5" pivotY="0.833">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </ListOption>
        </ListConfiguration>

        <!-- Центральная заглушка оси стрелок (строго внутри Group) -->
        <Group x="0" y="0" width="450" height="450">
            <PartImage x="215" y="215" width="20" height="20">
                <Image resource="hand_cap" />
            </PartImage>
        </Group>

    </Scene>
</WatchFace>
"""

with open("app/src/main/res/raw/watchface.xml", "w", encoding="utf-8") as f:
    f.write(watchface_xml)
