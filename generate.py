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
        versionCode = 7
        versionName = "7.0.0"
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

    <string name="marks_style_label">Метки «ща»</string>
    <string name="marks_4_ticks">4 «ща» + чёрточки</string>
    <string name="marks_12">12 «ща» (все)</string>
    <string name="marks_6_ticks">6 «ща» + чёрточки</string>
    <string name="marks_4_only">Только 4 «ща»</string>

    <string name="hands_style_label">Стиль стрелок</string>
    <string name="style_0">1. Пиксельные (8-Bit)</string>
    <string name="style_1">2. Мечи (Дайвер)</string>
    <string name="style_2">3. Копья (Dauphine)</string>
    <string name="style_3">4. Минимализм</string>
    <string name="style_4">5. Скелетоны</string>
    <string name="style_5">6. Булавки</string>
    <string name="style_6">7. Пилот (Жирные)</string>
    <string name="style_7">8. Тонкие иглы</string>

    <string name="color_label">Цветовая тема</string>
    <string name="color_0">Классика (Чёрно-белый)</string>
    <string name="color_1">Монохром</string>
    <string name="color_2">Терминал (Зелёный)</string>
    <string name="color_3">Янтарь</string>
    <string name="color_4">Киберпанк (Неон)</string>
    <string name="color_5">Полночь (Тёмно-синий)</string>
    <string name="color_6">Бордо</string>
    <string name="color_7">Изумруд</string>
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

# 9. Стрелки (рисуем в белом цвете #ffffff с прозрачным фоном, чтобы работал tintColor из темы!)
WHITE = (255, 255, 255, 255)
EMPTY = (0, 0, 0, 0)

# Все часовые: 24x132, pivot(12, 110) -> x=213, y=115, pivotY=0.833
# Все минутные: 20x180, pivot(10, 155) -> x=215, y=70, pivotY=0.861
# Все секундные: 8x210, pivot(4, 175) -> x=221, y=50, pivotY=0.833

# Стиль 0: Пиксельные (8-Bit Minecraft, блочная сетка 4x4)
def pixel_h(x, y, w, h):
    bx, by = x // 4, y // 4
    if by in (0, 1) and bx in (2, 3): return WHITE
    if by in (2, 3) and bx in (1, 2, 3, 4): return WHITE
    if by in (4, 5) and bx in (0, 1, 2, 3, 4, 5): return WHITE
    if 6 <= by <= 25 and bx in (1, 4): return WHITE
    if 26 <= by <= 31 and bx in (1, 2, 3, 4): return WHITE
    return EMPTY
save_png("app/src/main/res/drawable/h0_h.png", 24, 132, pixel_h)

def pixel_m(x, y, w, h):
    bx, by = x // 4, y // 4
    if by in (0, 1) and bx == 2: return WHITE
    if by in (2, 3) and bx in (1, 2, 3): return WHITE
    if by in (4, 5) and bx in (0, 1, 2, 3, 4): return WHITE
    if 6 <= by <= 36 and bx in (1, 3): return WHITE
    if 37 <= by <= 43 and bx in (1, 2, 3): return WHITE
    return EMPTY
save_png("app/src/main/res/drawable/h0_m.png", 20, 180, pixel_m)
save_png("app/src/main/res/drawable/h0_s.png", 8, 210, lambda x, y, w, h: WHITE if 2 <= x <= 5 and 4 <= y <= 204 else EMPTY)

# Стиль 1: Мечи (Дайверские)
def sword_h(x, y, w, h):
    if y < 6 or y > 125: return EMPTY
    hw = 7.0 if y > 28 else (y - 6) * (7.0 / 22.0)
    return WHITE if abs(x - 11.5) <= hw else EMPTY
save_png("app/src/main/res/drawable/h1_h.png", 24, 132, sword_h)

def sword_m(x, y, w, h):
    if y < 6 or y > 175: return EMPTY
    hw = 5.0 if y > 26 else (y - 6) * (5.0 / 20.0)
    return WHITE if abs(x - 9.5) <= hw else EMPTY
save_png("app/src/main/res/drawable/h1_m.png", 20, 180, sword_m)
save_png("app/src/main/res/drawable/h1_s.png", 8, 210, lambda x, y, w, h: WHITE if 3 <= x <= 4 and 4 <= y <= 204 else EMPTY)

# Стиль 2: Копья (Треугольные Dauphine)
def dauphine_h(x, y, w, h):
    if y < 4 or y > 126: return EMPTY
    if y <= 110:
        hw = 0.8 + (y - 4) * (7.5 / 106.0)
    else:
        hw = 8.3 - (y - 110) * (5.0 / 16.0)
    return WHITE if abs(x - 11.5) <= hw else EMPTY
save_png("app/src/main/res/drawable/h2_h.png", 24, 132, dauphine_h)

def dauphine_m(x, y, w, h):
    if y < 4 or y > 175: return EMPTY
    if y <= 155:
        hw = 0.7 + (y - 4) * (5.5 / 151.0)
    else:
        hw = 6.2 - (y - 155) * (4.0 / 20.0)
    return WHITE if abs(x - 9.5) <= hw else EMPTY
save_png("app/src/main/res/drawable/h2_m.png", 20, 180, dauphine_m)
save_png("app/src/main/res/drawable/h2_s.png", 8, 210, lambda x, y, w, h: WHITE if 3 <= x <= 4 and 4 <= y <= 204 else EMPTY)

# Стиль 3: Минимализм (Батоны)
save_png("app/src/main/res/drawable/h3_h.png", 24, 132, lambda x, y, w, h: WHITE if 8 <= x <= 15 and 10 <= y <= 122 else EMPTY)
save_png("app/src/main/res/drawable/h3_m.png", 20, 180, lambda x, y, w, h: WHITE if 7 <= x <= 12 and 8 <= y <= 172 else EMPTY)
save_png("app/src/main/res/drawable/h3_s.png", 8, 210, lambda x, y, w, h: WHITE if 3 <= x <= 4 and 4 <= y <= 204 else EMPTY)

# Стиль 4: Скелетоны (Полые рамки)
def skel_h(x, y, w, h):
    if 6 <= x <= 17 and 8 <= y <= 125:
        if 9 <= x <= 14 and 18 <= y <= 102: return EMPTY
        return WHITE
    return EMPTY
save_png("app/src/main/res/drawable/h4_h.png", 24, 132, skel_h)

def skel_m(x, y, w, h):
    if 6 <= x <= 13 and 8 <= y <= 175:
        if 8 <= x <= 11 and 18 <= y <= 148: return EMPTY
        return WHITE
    return EMPTY
save_png("app/src/main/res/drawable/h4_m.png", 20, 180, skel_m)
save_png("app/src/main/res/drawable/h4_s.png", 8, 210, lambda x, y, w, h: WHITE if 3 <= x <= 4 and 4 <= y <= 204 else EMPTY)

# Стиль 5: Булавки (Лоллипоп / Бреге с кольцом у острия)
def lolli_h(x, y, w, h):
    d = math.hypot(x - 11.5, y - 34)
    if 4.0 <= d <= 8.5: return WHITE
    if 10 <= x <= 13 and ((6 <= y <= 26) or (42 <= y <= 124)): return WHITE
    return EMPTY
save_png("app/src/main/res/drawable/h5_h.png", 24, 132, lolli_h)

def lolli_m(x, y, w, h):
    d = math.hypot(x - 9.5, y - 34)
    if 3.5 <= d <= 7.5: return WHITE
    if 8 <= x <= 11 and ((6 <= y <= 27) or (41 <= y <= 172)): return WHITE
    return EMPTY
save_png("app/src/main/res/drawable/h5_m.png", 20, 180, lolli_m)

def lolli_s(x, y, w, h):
    if math.hypot(x - 3.5, y - 40) <= 3.5: return WHITE
    if 3 <= x <= 4 and 4 <= y <= 204: return WHITE
    return EMPTY
save_png("app/src/main/res/drawable/h5_s.png", 8, 210, lolli_s)

# Стиль 6: Пилот (Жирные широкие с треугольным концом)
def pilot_h(x, y, w, h):
    if y < 6 or y > 125: return EMPTY
    hw = 8.0 if y > 22 else (y - 6) * (8.0 / 16.0)
    return WHITE if abs(x - 11.5) <= hw else EMPTY
save_png("app/src/main/res/drawable/h6_h.png", 24, 132, pilot_h)

def pilot_m(x, y, w, h):
    if y < 6 or y > 175: return EMPTY
    hw = 6.0 if y > 20 else (y - 6) * (6.0 / 14.0)
    return WHITE if abs(x - 9.5) <= hw else EMPTY
save_png("app/src/main/res/drawable/h6_m.png", 20, 180, pilot_m)
save_png("app/src/main/res/drawable/h6_s.png", 8, 210, lambda x, y, w, h: WHITE if 2 <= x <= 5 and 4 <= y <= 204 else EMPTY)

# Стиль 7: Тонкие иглы
save_png("app/src/main/res/drawable/h7_h.png", 24, 132, lambda x, y, w, h: WHITE if 10 <= x <= 13 and 8 <= y <= 125 else EMPTY)
save_png("app/src/main/res/drawable/h7_m.png", 20, 180, lambda x, y, w, h: WHITE if 9 <= x <= 10 and 6 <= y <= 175 else EMPTY)
save_png("app/src/main/res/drawable/h7_s.png", 8, 210, lambda x, y, w, h: WHITE if 3 <= x <= 4 and 4 <= y <= 204 else EMPTY)

# Центральная ТОЧКА (сплошная точка)
save_png("app/src/main/res/drawable/hand_cap.png", 18, 18, lambda x, y, w, h:
    WHITE if math.hypot(x - 8.5, y - 8.5) <= 6.0 else EMPTY
)

# 10. Вспомогательная функция генерации меток "ща" и рисок по кругу (R = 199px)
def make_mark_text(i, radius=199):
    angle_rad = math.radians(i * 30)
    cx = 225 + radius * math.sin(angle_rad)
    cy = 225 - radius * math.cos(angle_rad)
    x = int(cx - 25)
    y = int(cy - 18)
    return f"""                    <PartText x="{x}" y="{y}" width="50" height="36" alpha="255">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                        <Text align="CENTER">
                            <Font family="minecraft" size="32" color="#ffffffff">ща</Font>
                        </Text>
                    </PartText>
                    <PartText x="{x}" y="{y}" width="50" height="36" alpha="0">
                        <Variant mode="AMBIENT" target="alpha" value="255" />
                        <Text align="CENTER">
                            <Font family="minecraft" size="32" color="#00000000">
                                <Outline color="#ffffffff" width="1">ща</Outline>
                            </Font>
                        </Text>
                    </PartText>"""

def make_tick_line(i, r_inner=196, r_outer=212):
    angle_rad = math.radians(i * 30)
    sx = round(225 + r_inner * math.sin(angle_rad), 1)
    sy = round(225 - r_inner * math.cos(angle_rad), 1)
    ex = round(225 + r_outer * math.sin(angle_rad), 1)
    ey = round(225 - r_outer * math.cos(angle_rad), 1)
    return f"""                        <Line startX="{sx}" startY="{sy}" endX="{ex}" endY="{ey}">
                            <Stroke color="#ffffffff" thickness="3" cap="ROUND" />
                        </Line>"""

# Вариант 0: 4 "ща" (12, 3, 6, 9) + 8 рисок
opt0_marks = [make_mark_text(i) for i in (0, 3, 6, 9)]
opt0_ticks = [make_tick_line(i) for i in range(12) if i not in (0, 3, 6, 9)]
opt0_xml = "\n".join(opt0_marks) + '\n                    <PartDraw x="0" y="0" width="450" height="450">\n' + "\n".join(opt0_ticks) + '\n                    </PartDraw>'

# Вариант 1: 12 "ща"
opt1_xml = "\n".join([make_mark_text(i) for i in range(12)])

# Вариант 2: 6 "ща" (четные: 12, 2, 4, 6, 8, 10) + 6 рисок
opt2_marks = [make_mark_text(i) for i in range(0, 12, 2)]
opt2_ticks = [make_tick_line(i) for i in range(1, 12, 2)]
opt2_xml = "\n".join(opt2_marks) + '\n                    <PartDraw x="0" y="0" width="450" height="450">\n' + "\n".join(opt2_ticks) + '\n                    </PartDraw>'

# Вариант 3: Только 4 "ща" (12, 3, 6, 9) без рисок
opt3_xml = "\n".join([make_mark_text(i) for i in (0, 3, 6, 9)])

# Генерация 8 блоков AnalogClock
hand_options_xml = []
for idx in range(8):
    hand_options_xml.append(f"""            <ListOption id="{idx}">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand resource="h{idx}_h" x="213" y="115" width="24" height="132" pivotX="0.5" pivotY="0.833" tintColor="[CONFIGURATION.themeColor.1]" />
                    <MinuteHand resource="h{idx}_m" x="215" y="70" width="20" height="180" pivotX="0.5" pivotY="0.861" tintColor="[CONFIGURATION.themeColor.1]" />
                    <SecondHand resource="h{idx}_s" x="221" y="50" width="8" height="210" pivotX="0.5" pivotY="0.833" tintColor="[CONFIGURATION.themeColor.2]">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                    </SecondHand>
                </AnalogClock>
            </ListOption>""")

# 11. Валидный watchface.xml
watchface_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
    <Metadata key="CLOCK_TYPE" value="ANALOG" />
    <Metadata key="PREVIEW_TIME" value="10:10:30" />

    <UserConfigurations>
        <ListConfiguration id="marks_style" displayName="marks_style_label" defaultValue="0">
            <ListOption id="0" displayName="marks_4_ticks" />
            <ListOption id="1" displayName="marks_12" />
            <ListOption id="2" displayName="marks_6_ticks" />
            <ListOption id="3" displayName="marks_4_only" />
        </ListConfiguration>

        <ListConfiguration id="hands_style" displayName="hands_style_label" defaultValue="0">
            <ListOption id="0" displayName="style_0" />
            <ListOption id="1" displayName="style_1" />
            <ListOption id="2" displayName="style_2" />
            <ListOption id="3" displayName="style_3" />
            <ListOption id="4" displayName="style_4" />
            <ListOption id="5" displayName="style_5" />
            <ListOption id="6" displayName="style_6" />
            <ListOption id="7" displayName="style_7" />
        </ListConfiguration>

        <ColorConfiguration id="themeColor" displayName="color_label" defaultValue="0">
            <ColorOption id="0" displayName="color_0" colors="#ff000000 #ffffffff #ffff3b30" />
            <ColorOption id="1" displayName="color_1" colors="#ff000000 #ffffffff #ff9e9e9e" />
            <ColorOption id="2" displayName="color_2" colors="#ff000000 #ff00e676 #ffffffff" />
            <ColorOption id="3" displayName="color_3" colors="#ff000000 #ffffab00 #ffff3b30" />
            <ColorOption id="4" displayName="color_4" colors="#ff000000 #ff00e5ff #ffff2d55" />
            <ColorOption id="5" displayName="color_5" colors="#ff0a1628 #ffffffff #ffffd600" />
            <ColorOption id="6" displayName="color_6" colors="#ff1e070b #ffffffff #ffffab00" />
            <ColorOption id="7" displayName="color_7" colors="#ff071c12 #ffffffff #ff00e676" />
        </ColorConfiguration>
    </UserConfigurations>

    <Scene backgroundColor="#ff000000">

        <!-- Фон (в AOD всегда гаснет до чистого чёрного #ff000000) -->
        <Group x="0" y="0" width="450" height="450">
            <Variant mode="AMBIENT" target="alpha" value="0" />
            <PartDraw x="0" y="0" width="450" height="450">
                <Rectangle x="0" y="0" width="450" height="450">
                    <Fill color="[CONFIGURATION.themeColor.0]" />
                </Rectangle>
            </PartDraw>
        </Group>

        <!-- Метки "ща" (окрашиваются цветом темы) -->
        <ListConfiguration id="marks_style">
            <ListOption id="0">
                <Group x="0" y="0" width="450" height="450" tintColor="[CONFIGURATION.themeColor.1]">
{opt0_xml}
                </Group>
            </ListOption>
            <ListOption id="1">
                <Group x="0" y="0" width="450" height="450" tintColor="[CONFIGURATION.themeColor.1]">
{opt1_xml}
                </Group>
            </ListOption>
            <ListOption id="2">
                <Group x="0" y="0" width="450" height="450" tintColor="[CONFIGURATION.themeColor.1]">
{opt2_xml}
                </Group>
            </ListOption>
            <ListOption id="3">
                <Group x="0" y="0" width="450" height="450" tintColor="[CONFIGURATION.themeColor.1]">
{opt3_xml}
                </Group>
            </ListOption>
        </ListConfiguration>

        <!-- 8 стилей стрелок -->
        <ListConfiguration id="hands_style">
{chr(10).join(hand_options_xml)}
        </ListConfiguration>

        <!-- Сплошная точка по центру -->
        <Group x="0" y="0" width="450" height="450" tintColor="[CONFIGURATION.themeColor.1]">
            <PartImage x="216" y="216" width="18" height="18">
                <Image resource="hand_cap" />
            </PartImage>
        </Group>

    </Scene>
</WatchFace>
"""

with open("app/src/main/res/raw/watchface.xml", "w", encoding="utf-8") as f:
    f.write(watchface_xml)
