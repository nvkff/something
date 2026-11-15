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

# 8. Генерация preview.png (450x450)
w, h = 450, 450
raw = bytearray()
for y in range(h):
    raw.append(0)
    for x in range(w):
        d = math.hypot(x - 225, y - 225)
        c = 255 if (215 <= d <= 222) else 0
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

# 9. Точные расчеты для 12 надписей "ща" ближе к краю экрана
dial_marks = []
radius = 184 # Отодвинуто ближе к краю (с запасом 21px до безеля)
for i in range(12):
    angle_deg = i * 30
    angle_rad = math.radians(angle_deg)
    cx = 225 + radius * math.sin(angle_rad)
    cy = 225 - radius * math.cos(angle_rad)
    
    # Контейнер 70x44, центрируем вокруг расчетной точки (cx, cy)
    x = int(cx - 35)
    y = int(cy - 22)
    
    dial_marks.append(f"""            <PartText x="{x}" y="{y}" width="70" height="44">
                <Text align="CENTER">
                    <Font family="minecraft" size="32" color="#ffffffff" weight="NORMAL">ща</Font>
                </Text>
            </PartText>""")

# 10. Генерация watchface.xml через официальный тег <AnalogClock>
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

        <!-- 12 одинаковых надписей "ща" по кругу -->
        <Group x="0" y="0" width="450" height="450">
{chr(10).join(dial_marks)}
        </Group>

        <!-- СТИЛЬ 1: Пиксельные стрелки (8-bit) -->
        <Condition>
            <Expressions>
                <Expression name="is_pixel">[CONFIGURATION.hands_style] == 'pixel'</Expression>
            </Expressions>
            <Compare expression="is_pixel">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand x="219" y="115" width="12" height="110" pivotX="0.5" pivotY="1.0">
                        <Line startX="6" startY="0" endX="6" endY="110" color="#ffffffff" strokeWidth="12" strokeCap="SQUARE" />
                    </HourHand>
                    <MinuteHand x="221" y="65" width="8" height="160" pivotX="0.5" pivotY="1.0">
                        <Line startX="4" startY="0" endX="4" endY="160" color="#ffffffff" strokeWidth="8" strokeCap="SQUARE" />
                    </MinuteHand>
                    <SecondHand x="223" y="55" width="4" height="170" pivotX="0.5" pivotY="1.0">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                        <Line startX="2" startY="0" endX="2" endY="170" color="#ffff3b30" strokeWidth="4" strokeCap="SQUARE" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- СТИЛЬ 2: Стрелки-мечи (Дайвер) -->
        <Condition>
            <Expressions>
                <Expression name="is_sword">[CONFIGURATION.hands_style] == 'sword'</Expression>
            </Expressions>
            <Compare expression="is_sword">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand x="217" y="110" width="16" height="115" pivotX="0.5" pivotY="1.0">
                        <Line startX="8" startY="0" endX="8" endY="115" color="#ffffffff" strokeWidth="16" strokeCap="ROUND" />
                    </HourHand>
                    <MinuteHand x="220" y="55" width="10" height="170" pivotX="0.5" pivotY="1.0">
                        <Line startX="5" startY="0" endX="5" endY="170" color="#ffffffff" strokeWidth="10" strokeCap="ROUND" />
                    </MinuteHand>
                    <SecondHand x="223" y="45" width="4" height="180" pivotX="0.5" pivotY="1.0">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                        <Line startX="2" startY="0" endX="2" endY="180" color="#ffffcc00" strokeWidth="4" strokeCap="ROUND" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- СТИЛЬ 3: Классический минимализм -->
        <Condition>
            <Expressions>
                <Expression name="is_classic">[CONFIGURATION.hands_style] == 'classic'</Expression>
            </Expressions>
            <Compare expression="is_classic">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand x="220" y="125" width="10" height="100" pivotX="0.5" pivotY="1.0">
                        <Line startX="5" startY="0" endX="5" endY="100" color="#ffffffff" strokeWidth="10" strokeCap="ROUND" />
                    </HourHand>
                    <MinuteHand x="222" y="70" width="6" height="155" pivotX="0.5" pivotY="1.0">
                        <Line startX="3" startY="0" endX="3" endY="155" color="#ffffffff" strokeWidth="6" strokeCap="ROUND" />
                    </MinuteHand>
                    <SecondHand x="224" y="60" width="2" height="165" pivotX="0.5" pivotY="1.0">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                        <Line startX="1" startY="0" endX="1" endY="165" color="#ffff3b30" strokeWidth="2" strokeCap="ROUND" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- СТИЛЬ 4: Скелетоны -->
        <Condition>
            <Expressions>
                <Expression name="is_skeleton">[CONFIGURATION.hands_style] == 'skeleton'</Expression>
            </Expressions>
            <Compare expression="is_skeleton">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand x="218" y="115" width="14" height="110" pivotX="0.5" pivotY="1.0">
                        <RoundRectangle x="0" y="0" width="14" height="110" cornerRadiusX="4" cornerRadiusY="4" color="#00000000" strokeWidth="3" strokeColor="#ffffffff" />
                    </HourHand>
                    <MinuteHand x="220" y="60" width="10" height="165" pivotX="0.5" pivotY="1.0">
                        <RoundRectangle x="0" y="0" width="10" height="165" cornerRadiusX="3" cornerRadiusY="3" color="#00000000" strokeWidth="3" strokeColor="#ffffffff" />
                    </MinuteHand>
                    <SecondHand x="224" y="50" width="2" height="175" pivotX="0.5" pivotY="1.0">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                        <Line startX="1" startY="0" endX="1" endY="175" color="#ff00e5ff" strokeWidth="3" strokeCap="ROUND" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- СТИЛЬ 5: Тонкие иглы -->
        <Condition>
            <Expressions>
                <Expression name="is_needle">[CONFIGURATION.hands_style] == 'needle'</Expression>
            </Expressions>
            <Compare expression="is_needle">
                <AnalogClock x="0" y="0" width="450" height="450">
                    <HourHand x="223" y="120" width="4" height="105" pivotX="0.5" pivotY="1.0">
                        <Line startX="2" startY="0" endX="2" endY="105" color="#ffffffff" strokeWidth="4" strokeCap="ROUND" />
                    </HourHand>
                    <MinuteHand x="223" y="60" width="4" height="165" pivotX="0.5" pivotY="1.0">
                        <Line startX="2" startY="0" endX="2" endY="165" color="#ffffffff" strokeWidth="3" strokeCap="ROUND" />
                    </MinuteHand>
                    <SecondHand x="224" y="50" width="2" height="175" pivotX="0.5" pivotY="1.0">
                        <Variant mode="AMBIENT" target="alpha" value="0" />
                        <Line startX="1" startY="0" endX="1" endY="175" color="#ffff3b30" strokeWidth="2" strokeCap="ROUND" />
                    </SecondHand>
                </AnalogClock>
            </Compare>
        </Condition>

        <!-- Центральная точка (ось стрелок) -->
        <PartDraw x="217" y="217" width="16" height="16">
            <RoundRectangle x="0" y="0" width="16" height="16" cornerRadiusX="8" cornerRadiusY="8" color="#ffffffff" />
            <RoundRectangle x="4" y="4" width="8" height="8" cornerRadiusX="4" cornerRadiusY="4" color="#ff000000" />
        </PartDraw>

    </Scene>
</WatchFace>
"""

with open("app/src/main/res/raw/watchface.xml", "w", encoding="utf-8") as f:
    f.write(watchface_xml)
