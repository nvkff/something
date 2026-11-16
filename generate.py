import os
import sys
import json
import zipfile
import urllib.request
import subprocess
import shutil

# 0. Устанавливаем Pillow (с учётом Ubuntu 24.04 PEP 668 --break-system-packages)
try:
    from PIL import Image
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", "pillow"])
    except Exception:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pillow"])
    from PIL import Image

NEAREST = getattr(Image, "Resampling", Image).NEAREST

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

# 8. Скачивание оригинальных 64 текстур clock_00..clock_63 с официального сервера Mojang
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

with zipfile.ZipFile(jar_path, "r") as zf:
    for k in range(64):
        entry = f"assets/minecraft/textures/item/clock_{k:02d}.png"
        with zf.open(entry) as src:
            img = Image.open(src).convert("RGBA")
            # Масштабируем 16x16 -> 448x448 строго без сглаживания (NEAREST)
            scaled = img.resize((448, 448), NEAREST)
            scaled.save(f"app/src/main/res/drawable/clock_{k:02d}.png")

# Создаем preview.png (450x450, черный фон + clock_00 по центру)
prev_bg = Image.new("RGBA", (450, 450), (0, 0, 0, 255))
c0 = Image.open("app/src/main/res/drawable/clock_00.png")
prev_bg.paste(c0, (1, 1), c0)
prev_bg.save("app/src/main/res/drawable/preview.png")

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
