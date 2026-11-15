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
        versionCode = 3
        versionName = "3.0.0"
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
    <Editable value="true" />
</WatchFaceInfo>
""")

# Функция создания валидного PNG из матрицы RGBA
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

# 8. Генерация preview.png (450x450)
def preview_px(x, y, w, h):
    d = math.hypot(x - 225, y - 225)
    c = 255 if (215 <= d <= 222) else 0
    return (c, c, c, 255 if c else 0)

save_png("app/src/main/res/drawable-nodpi/preview.png", 450, 450, preview_px)

# 9. Генерация наборов стрелок (Hour: 24x140, Minute: 16x200, Second: 8x220)
# Стиль 1: Пиксельные (8-Bit Minecraft)
save_png("app/src/main/res/drawable-nodpi/h_pixel_h.png", 24, 140, lambda x, y, w, h: (255, 255, 255, 255) if 4 <= x <= 19 and 8 <= y <= 130 else (0, 0, 0, 0))
save_png("app/src/main/res/drawable-nodpi/h_pixel_m.png", 16, 200, lambda x, y, w, h: (255, 255, 255, 255) if 3 <= x <= 12 and 8 <= y <= 190 else (0, 0, 0, 0))
save_png("app/src/main/res/drawable-nodpi/h_pixel_s.png", 8, 220, lambda x, y, w, h: (255, 59, 48, 255) if 2 <= x <= 5 and 5 <= y <= 210 else (0, 0, 0, 0))

# Стиль 2: Мечи (Дайверы с острием)
def sword_h(x, y, w, h):
    if y > 130 or y < 15: return (0, 0, 0, 0)
    width_at_y = 10 if y > 35 else (x - 12 + (35 - y)*0.4)
    return (255, 255, 255, 255) if abs(x - 12) <= (10 if y > 35 else (y - 15)*0.5) else (0, 0, 0, 0)
save_png("app/src/main/res/drawable-nodpi/h_sword_h.png", 24, 140, sword_h)

def sword_m(x, y, w, h):
    if y > 190 or y < 15: return (0, 0, 0, 0)
    return (255, 255, 255, 255) if abs(x - 8) <= (7 if y > 30 else (y - 15)*0.4) else (0, 0, 0, 0)
save_png("app/src/main/res/drawable-nodpi/h_sword_m.png", 16, 200, sword_m)
save_png("app/src/main/res/drawable-nodpi/h_sword_s.png", 8, 220, lambda x, y, w, h: (255, 204, 0, 255) if 2 <= x <= 5 and 5 <= y <= 210 else (0, 0, 0, 0))

# Стиль 3: Минимализм (Батоны)
save_png("app/src/main/res/drawable-nodpi/h_classic_h.png", 24, 140, lambda x, y, w, h: (255, 255, 255, 255) if 6 <= x <= 17 and 10 <= y <= 130 else (0, 0, 0, 0))
save_png("app/src/main/res/drawable-nodpi/h_classic_m.png", 16, 200, lambda x, y, w, h: (255, 255, 255, 255) if 4 <= x <= 11 and 10 <= y <= 190 else (0, 0, 0, 0))
save_png("app/src/main/res/drawable-nodpi/h_classic_s.png", 8, 220, lambda x, y, w, h: (255, 59, 48, 255) if 3 <= x <= 4 and 5 <= y <= 210 else (0, 0, 0, 0))

# Стиль 4: Скелетоны (Полые рамки)
def skel_h(x, y, w, h):
    if 4 <= x <= 19 and 10 <= y <= 130:
        if 7 <= x <= 16 and 20 <= y <= 115: return (0, 0, 0, 0)
        return (255, 255, 255, 255)
    return (0, 0, 0, 0)
save_png("app/src/main/res/drawable-nodpi/h_skel_h.png", 24, 140, skel_h)

def skel_m(x, y, w, h):
    if 3 <= x <= 12 and 10 <= y <= 190:
        if 5 <= x <= 10 and 20 <= y <= 175: return (0, 0, 0, 0)
        return (255, 255, 255, 255)
    return (0, 0, 0, 0)
save_png("app/src/main/res/drawable-nodpi/h_skel_m.png", 16, 200, skel_m)
save_png("app/src/main/res/drawable-nodpi/h_skel_s.png", 8, 220, lambda x, y, w, h: (0, 229, 255, 255) if 2 <= x <= 5 and 5 <= y <= 210 else (0, 0, 0, 0))

# Стиль 5: Тонкие иглы
save_png("app/src/main/res/drawable-nodpi/h_needle_h.png", 24, 140, lambda x, y, w, h: (255, 255, 255, 255) if 10 <= x <= 13 and 10 <= y <= 130 else (0, 0, 0, 0))
save_png("app/src/main/res/drawable-nodpi/h_needle_m.png", 16, 200, lambda x, y, w, h: (255, 255, 255, 255) if 7 <= x <= 8 and 10 <= y <= 190 else (0, 0, 0, 0))
save_png("app/src/main/res/drawable-nodpi/h_needle_s.png", 8, 220, lambda x, y, w, h: (255, 59, 48, 255) if 3 <= x <= 4 and 5 <= y <= 210 else (0, 0, 0, 0))

# Центральная заглушка
save_png("app/src/main/res/drawable-nodpi/hand_cap.png", 24, 24, lambda x, y, w, h: (255, 255, 255, 255) if math.hypot(x-12, y-12) <= 10 and math.hypot(x-12, y-12) >= 3 else (0, 0, 0, 0))

# 10. Расчёт 12 надписей "ща" ближе к безелю (R=196px, безопасный отступ 13px)
dial_marks = []
radius = 196
for i in range(12):
    angle_deg = i * 30
    angle_rad = math.radians(angle_deg)
    cx = 225 + radius * math.sin(angle_rad)
    cy = 225 - radius * math.cos(angle_rad)
    
    x = int(cx - 35)
    y = int(cy - 22)
    
    dial_marks.append(f"""            <PartText x="{x}" y="{y}" width="70" height="44">
                <Text align="CENTER">
                    <Font family="minecraft" size="33" color="#ffffffff" weight="NORMAL">ща</Font>
                </Text>
            </PartText>""")

# 11. watchface.xml со стрелками по спецификации WFF
watchface_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
    <Metadata key="CLOCK_TYPE" value="ANALOG" />
    <Metadata key="PREVIEW_TIME" value="10:10:30" />

    <UserConfigurations>
        <ListConfiguration id="hands_style" displayName="Стиль стрелок" defaultValue="pixel">
            <ListOption id="pixel" displayName="1. Пиксельные" />
            <ListOption id="sword" displayName="2. Мечи" />
            <ListOption id="classic" displayName="3. Минимализм" />
            <ListOption id="skeleton" displayName="4. Скелетоны" />
            <ListOption id="needle" displayName="5. Тонкие иглы" />
        </ListConfiguration>
    </UserConfigurations>

    <Scene backgroundColor="#ff000000">

        <!-- 12 надписей "ща" ближе к безелю -->
        <Group x="0" y="0" width="450" height="450">
{chr(10).join(dial_marks)}
        </Group>

        <!-- 1. Пиксельные стрелки -->
        <Condition>
            <Expressions>
                <Expression name="is_pixel">[CONFIGURATION.hands_style] == 'pixel'</Expression>
            </Expressions>
            <Compare expression="is_pixel">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_pixel_h" x="213" y="105" width="24" height="140" pivotX="0.5" pivotY="0.857" />
                    <MinuteHand resource="h_pixel_m" x="217" y="45" width="16" height="200" pivotX="0.5" pivotY="0.9" />
                    <SecondHand resource="h_pixel_s" x="221" y="25" width="8" height="220" pivotX="0.5" pivotY="0.909">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- 2. Мечи -->
        <Condition>
            <Expressions>
                <Expression name="is_sword">[CONFIGURATION.hands_style] == 'sword'</Expression>
            </Expressions>
            <Compare expression="is_sword">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_sword_h" x="213" y="105" width="24" height="140" pivotX="0.5" pivotY="0.857" />
                    <MinuteHand resource="h_sword_m" x="217" y="45" width="16" height="200" pivotX="0.5" pivotY="0.9" />
                    <SecondHand resource="h_sword_s" x="221" y="25" width="8" height="220" pivotX="0.5" pivotY="0.909">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- 3. Минимализм -->
        <Condition>
            <Expressions>
                <Expression name="is_classic">[CONFIGURATION.hands_style] == 'classic'</Expression>
            </Expressions>
            <Compare expression="is_classic">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_classic_h" x="213" y="105" width="24" height="140" pivotX="0.5" pivotY="0.857" />
                    <MinuteHand resource="h_classic_m" x="217" y="45" width="16" height="200" pivotX="0.5" pivotY="0.9" />
                    <SecondHand resource="h_classic_s" x="221" y="25" width="8" height="220" pivotX="0.5" pivotY="0.909">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- 4. Скелетоны -->
        <Condition>
            <Expressions>
                <Expression name="is_skeleton">[CONFIGURATION.hands_style] == 'skeleton'</Expression>
            </Expressions>
            <Compare expression="is_skeleton">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_skel_h" x="213" y="105" width="24" height="140" pivotX="0.5" pivotY="0.857" />
                    <MinuteHand resource="h_skel_m" x="217" y="45" width="16" height="200" pivotX="0.5" pivotY="0.9" />
                    <SecondHand resource="h_skel_s" x="221" y="25" width="8" height="220" pivotX="0.5" pivotY="0.909">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- 5. Тонкие иглы -->
        <Condition>
            <Expressions>
                <Expression name="is_needle">[CONFIGURATION.hands_style] == 'needle'</Expression>
            </Expressions>
            <Compare expression="is_needle">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h_needle_h" x="213" y="105" width="24" height="140" pivotX="0.5" pivotY="0.857" />
                    <MinuteHand resource="h_needle_m" x="217" y="45" width="16" height="200" pivotX="0.5" pivotY="0.9" />
                    <SecondHand resource="h_needle_s" x="221" y="25" width="8" height="220" pivotX="0.5" pivotY="0.909">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- Центральная заглушка оси стрелок -->
        <PartImage resource="hand_cap" x="213" y="213" width="24" height="24" />

    </Scene>
</WatchFace>
"""

with open("app/src/main/res/raw/watchface.xml", "w", encoding="utf-8") as f:
    f.write(watchface_xml)
