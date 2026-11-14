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
rootProject.name = "WordClock"
include(":app")
""")

# 3. app/build.gradle.kts
os.makedirs("app", exist_ok=True)
with open("app/build.gradle.kts", "w", encoding="utf-8") as f:
    f.write("""plugins {
    id("com.android.application")
}

android {
    namespace = "com.jeremysteckling.facerrel.watchfacepush.wordclock"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.jeremysteckling.facerrel.watchfacepush.wordclock"
        minSdk = 34
        targetSdk = 34
        versionCode = 10
        versionName = "10.0.0"
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

# 4. Очистка и подготовка папок
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
    <string name="app_name">Словами</string>
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

# 8. Генерация растрового preview.png (450x450)
w, h = 450, 450
raw = bytearray()
for y in range(h):
    raw.append(0)
    for x in range(w):
        d = math.hypot(x - 225, y - 225)
        c = 255 if (200 <= d <= 212) else 0
        raw.extend((c, c, c, 255))

def chunk(t, d):
    return struct.pack("!I", len(d)) + t + d + struct.pack("!I", zlib.crc32(t + d) & 0xffffffff)

png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 6, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    + chunk(b"IEND", b"")
)
with open("app/src/main/res/drawable/preview.png", "wb") as f:
    f.write(png)

# 9. Генерация res/raw/watchface.xml (выравнивание по ПРАВОЙ стенке align="END")
nom = ["", "час", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать"]
gen = ["", "первого", "второго", "третьего", "четвертого", "пятого", "шестого", "седьмого", "восьмого", "девятого", "десятого", "одиннадцатого", "двенадцатого"]

def make_part_text(line, y, is_bold):
    # Поле начинается на x=22 и имеет ширину 350 -> правая стенка стоит ровно на 22 + 350 = 372px (отступ 78px справа)
    x_pos = 22
    box_w = 350
    font_size = 35
    parts = []
    
    # 1. Основной слой для активного экрана (в AOD гаснет alpha=0)
    parts.append(f"""                <PartText x="{x_pos}" y="{y}" width="{box_w}" height="52" alpha="255">
                    <Variant mode="AMBIENT" target="alpha" value="0" />
                    <Text align="END">
                        <Font family="minecraft" size="{font_size}" color="#ffffffff">{line}</Font>
                    </Text>
                </PartText>""")
    
    # Если строка жирная (сам час) — дублируем со сдвигом на 2px влево для чистого пиксельного Bold
    if is_bold:
        parts.append(f"""                <PartText x="{x_pos - 2}" y="{y}" width="{box_w}" height="52" alpha="255">
                    <Variant mode="AMBIENT" target="alpha" value="0" />
                    <Text align="END">
                        <Font family="minecraft" size="{font_size}" color="#ffffffff">{line}</Font>
                    </Text>
                </PartText>""")

    # 2. Контурный слой (только белая рамка вокруг букв) для режима AOD!
    outline_w = 2 if is_bold else 1
    parts.append(f"""                <PartText x="{x_pos}" y="{y}" width="{box_w}" height="52" alpha="0">
                    <Variant mode="AMBIENT" target="alpha" value="255" />
                    <Text align="END">
                        <Font family="minecraft" size="{font_size}" color="#00000000">
                            <Outline color="#ffffffff" width="{outline_w}">{line}</Outline>
                        </Font>
                    </Text>
                </PartText>""")
    
    return "\n".join(parts)

def make_group(lines, bold_idx):
    n = len(lines)
    start_y = 176 if n == 2 else (146 if n == 3 else 116)
    step = 50
    parts = [make_part_text(lines[i], start_y + i * step, i == bold_idx) for i in range(n)]
    return '            <Group x="0" y="0" width="450" height="450">\n' + "\n".join(parts) + '\n            </Group>'

expressions = []
compares = []

# А) Ровный час (minute == 0, для каждого часа 0..23)
for h in range(24):
    h12 = 12 if h % 12 == 0 else h % 12
    tod = "утра" if 4 <= h <= 11 else ("дня" if 12 <= h <= 16 else ("вечера" if 17 <= h <= 22 else "ночи"))
    if h12 == 1:
        lines = ["час", tod]
    elif 2 <= h12 <= 4:
        lines = [nom[h12], "часа", tod]
    else:
        lines = [nom[h12], "часов", tod]
    name = f"m0_h{h}"
    expressions.append(f'                <Expression name="{name}">([MINUTE] == 0) &amp;&amp; ([HOUR_0_23] == {h})</Expression>')
    compares.append(f'            <Compare expression="{name}">\n{make_group(lines, 0)}\n            </Compare>')

# Б) Первая половина часа (1..30 минут)
m_first_half = {
    1: ["одна", "минута"], 2: ["две", "минуты"], 3: ["три", "минуты"], 4: ["четыре", "минуты"],
    5: ["пять", "минут"], 6: ["шесть", "минут"], 7: ["семь", "минут"], 8: ["восемь", "минут"],
    9: ["девять", "минут"], 10: ["десять", "минут"], 11: ["одиннадцать", "минут"], 12: ["двенадцать", "минут"],
    13: ["тринадцать", "минут"], 14: ["четырнадцать", "минут"], 15: ["четверть"],
    16: ["шестнадцать", "минут"], 17: ["семнадцать", "минут"], 18: ["восемнадцать", "минут"],
    19: ["девятнадцать", "минут"], 20: ["двадцать", "минут"], 21: ["двадцать", "одна", "минута"],
    22: ["двадцать", "две", "минуты"], 23: ["двадцать", "три", "минуты"], 24: ["двадцать", "четыре", "минуты"],
    25: ["двадцать", "пять", "минут"], 26: ["двадцать", "шесть", "минут"], 27: ["двадцать", "семь", "минут"],
    28: ["двадцать", "восемь", "минут"], 29: ["двадцать", "девять", "минут"], 30: ["половина"]
}

for m, m_lines in m_first_half.items():
    total_n = len(m_lines) + 1
    start_y = 176 if total_n == 2 else (146 if total_n == 3 else 116)
    step = 50
    parts = [make_part_text(m_lines[i], start_y + i * step, False) for i in range(len(m_lines))]
    name = f"min_{m}"
    expressions.append(f'                <Expression name="{name}">[MINUTE] == {m}</Expression>')
    compares.append(f'            <Compare expression="{name}">\n            <Group x="0" y="0" width="450" height="450">\n' + "\n".join(parts) + '\n            </Group>\n            </Compare>')

# В) Прямой счёт (31..34, 36..39) — "час тридцать один", "два тридцать два"
m_direct = {
    31: ["тридцать", "один"], 32: ["тридцать", "два"], 33: ["тридцать", "три"], 34: ["тридцать", "четыре"],
    36: ["тридцать", "шесть"], 37: ["тридцать", "семь"], 38: ["тридцать", "восемь"], 39: ["тридцать", "девять"]
}
for m, m_lines in m_direct.items():
    start_y = 146
    step = 50
    parts = [make_part_text(m_lines[i], start_y + (i + 1) * step, False) for i in range(len(m_lines))]
    name = f"min_{m}"
    expressions.append(f'                <Expression name="{name}">[MINUTE] == {m}</Expression>')
    compares.append(f'            <Compare expression="{name}">\n            <Group x="0" y="0" width="450" height="450">\n' + "\n".join(parts) + '\n            </Group>\n            </Compare>')

# Г) Обратный отсчёт (35 и 40..59)
m_second_half = {
    35: ["без", "двадцати", "пяти"], 40: ["без", "двадцати"], 41: ["без", "девятнадцати"],
    42: ["без", "восемнадцати"], 43: ["без", "семнадцати"], 44: ["без", "шестнадцати"],
    45: ["без", "четверти"], 46: ["без", "четырнадцати"], 47: ["без", "тринадцати"],
    48: ["без", "двенадцати"], 49: ["без", "одиннадцати"], 50: ["без", "десяти"],
    51: ["без", "девяти"], 52: ["без", "восьми"], 53: ["без", "семи"], 54: ["без", "шести"],
    55: ["без", "пяти"], 56: ["без", "четырех", "минут"], 57: ["без", "трех", "минут"],
    58: ["без", "двух", "минут"], 59: ["без", "одной", "минуты"]
}
for m, m_lines in m_second_half.items():
    total_n = len(m_lines) + 1
    start_y = 176 if total_n == 2 else (146 if total_n == 3 else 116)
    step = 50
    parts = [make_part_text(m_lines[i], start_y + i * step, False) for i in range(len(m_lines))]
    name = f"min_{m}"
    expressions.append(f'                <Expression name="{name}">[MINUTE] == {m}</Expression>')
    compares.append(f'            <Compare expression="{name}">\n            <Group x="0" y="0" width="450" height="450">\n' + "\n".join(parts) + '\n            </Group>\n            </Compare>')

# Отдельный Condition для строки ЧАСА (жирный акцент + контур в AOD)
hour_expressions = []
hour_compares = []

for h12 in range(1, 13):
    nextH = 12 if (h12 + 1) % 12 == 0 else (h12 + 1) % 12
    
    # 1) Первая половина часа с 2 строками всего (минуты=15, 30 -> y = 176 + 50 = 226)
    n1 = f"hg2_h{h12}"
    hour_expressions.append(f'                <Expression name="{n1}">([HOUR_1_12] == {h12}) &amp;&amp; (([MINUTE] == 15) || ([MINUTE] == 30))</Expression>')
    hour_compares.append(f'            <Compare expression="{n1}">\n            <Group x="0" y="0" width="450" height="450">\n{make_part_text(gen[nextH], 226, True)}\n            </Group>\n            </Compare>')

    # 2) Первая половина часа с 3 строками всего (1..14, 16..20 -> y = 146 + 2*50 = 246)
    n2 = f"hg3_h{h12}"
    hour_expressions.append(f'                <Expression name="{n2}">([HOUR_1_12] == {h12}) &amp;&amp; ((([MINUTE] &gt;= 1) &amp;&amp; ([MINUTE] &lt;= 14)) || (([MINUTE] &gt;= 16) &amp;&amp; ([MINUTE] &lt;= 20)))</Expression>')
    hour_compares.append(f'            <Compare expression="{n2}">\n            <Group x="0" y="0" width="450" height="450">\n{make_part_text(gen[nextH], 246, True)}\n            </Group>\n            </Compare>')

    # 3) Первая половина часа с 4 строками всего (21..29 -> y = 116 + 3*50 = 266)
    n3 = f"hg4_h{h12}"
    hour_expressions.append(f'                <Expression name="{n3}">([HOUR_1_12] == {h12}) &amp;&amp; (([MINUTE] &gt;= 21) &amp;&amp; ([MINUTE] &lt;= 29))</Expression>')
    hour_compares.append(f'            <Compare expression="{n3}">\n            <Group x="0" y="0" width="450" height="450">\n{make_part_text(gen[nextH], 266, True)}\n            </Group>\n            </Compare>')

    # 4) Прямой счёт (31..34, 36..39) — текущий час h12 на 1-й строке (y = 146)
    n4 = f"hd_h{h12}"
    hour_expressions.append(f'                <Expression name="{n4}">([HOUR_1_12] == {h12}) &amp;&amp; ((([MINUTE] &gt;= 31) &amp;&amp; ([MINUTE] &lt;= 34)) || (([MINUTE] &gt;= 36) &amp;&amp; ([MINUTE] &lt;= 39)))</Expression>')
    hour_compares.append(f'            <Compare expression="{n4}">\n            <Group x="0" y="0" width="450" height="450">\n{make_part_text(nom[h12], 146, True)}\n            </Group>\n            </Compare>')

    # 5) Вторая половина часа с 3 строками всего (40..55 -> y = 146 + 2*50 = 246)
    n5 = f"hn3_h{h12}"
    hour_expressions.append(f'                <Expression name="{n5}">([HOUR_1_12] == {h12}) &amp;&amp; (([MINUTE] &gt;= 40) &amp;&amp; ([MINUTE] &lt;= 55))</Expression>')
    hour_compares.append(f'            <Compare expression="{n5}">\n            <Group x="0" y="0" width="450" height="450">\n{make_part_text(nom[nextH], 246, True)}\n            </Group>\n            </Compare>')

    # 6) Вторая половина часа с 4 строками всего (35, 56..59 -> y = 116 + 3*50 = 266)
    n6 = f"hn4_h{h12}"
    hour_expressions.append(f'                <Expression name="{n6}">([HOUR_1_12] == {h12}) &amp;&amp; (([MINUTE] == 35) || (([MINUTE] &gt;= 56) &amp;&amp; ([MINUTE] &lt;= 59)))</Expression>')
    hour_compares.append(f'            <Compare expression="{n6}">\n            <Group x="0" y="0" width="450" height="450">\n{make_part_text(nom[nextH], 266, True)}\n            </Group>\n            </Compare>')

watchface_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450">
    <Metadata key="CLOCK_TYPE" value="DIGITAL" />
    <Metadata key="PREVIEW_TIME" value="10:08:32" />
    <Scene backgroundColor="#ff000000">
        <Condition>
            <Expressions>
{chr(10).join(expressions)}
            </Expressions>
{chr(10).join(compares)}
        </Condition>
        <Condition>
            <Expressions>
{chr(10).join(hour_expressions)}
            </Expressions>
{chr(10).join(hour_compares)}
        </Condition>
    </Scene>
</WatchFace>
"""

with open("app/src/main/res/raw/watchface.xml", "w", encoding="utf-8") as f:
    f.write(watchface_xml)
