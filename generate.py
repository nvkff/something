import os
import zlib
import struct
import math
import shutil

# 1. Корневой build.gradle.kts
with open("build.gradle.kts", "w", encoding="utf-8") as f:
    f.write("""plugins {
    id("com.android.application") version "8.4.1" apply false
    id("org.jetbrains.kotlin.android") version "1.9.23" apply false
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
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "wb.illuminator.wordclock"
    compileSdk = 34

    defaultConfig {
        applicationId = "wb.illuminator.wordclock"
        minSdk = 28
        targetSdk = 30
        versionCode = 1
        versionName = "1.0.0"
    }

    signingConfigs {
        create("release") {
            storeFile = rootProject.file("release.keystore")
            storePassword = "123456"
            keyAlias = "watchkey"
            keyPassword = "123456"
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isDebuggable = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.wear.watchface:watchface:1.1.1")
    implementation("androidx.wear.watchface:watchface-editor:1.1.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
}
""")

# 4. Папки ресурсов и копирование шрифта и в assets, и в res/font
os.makedirs("app/src/main/res/xml", exist_ok=True)
os.makedirs("app/src/main/res/font", exist_ok=True)
os.makedirs("app/src/main/res/drawable-nodpi", exist_ok=True)
os.makedirs("app/src/main/assets", exist_ok=True)
os.makedirs("app/src/main/java/com/samsung/android/wearable/watchfacestudio/editor", exist_ok=True)
os.makedirs("app/src/main/java/com/samsung/watchface/debug", exist_ok=True)

if os.path.exists("app/src/main/assets/minecraft.ttf"):
    shutil.copy("app/src/main/assets/minecraft.ttf", "app/src/main/res/font/minecraft.ttf")

# 5. Полная побайтовая копия AndroidManifest.xml от рабочего wb.illuminator.two (включая DebugBroadcastReceiver)
with open("app/src/main/AndroidManifest.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature android:name="android.hardware.type.watch" />

    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.VIBRATE" />
    <uses-permission android:name="com.google.android.wearable.permission.BIND_WATCH_FACE_CONTROL" />
    <uses-permission android:name="com.google.android.wearable.permission.RECEIVE_COMPLICATION_DATA" />

    <queries>
        <package android:name="com.samsung.android.watch.watchface.companionhelper" />
        <intent>
            <action android:name="android.support.wearable.complications.ACTION_COMPLICATION_UPDATE_REQUEST" />
        </intent>
        <intent>
            <action android:name="android.intent.action.MAIN" />
            <category android:name="android.intent.category.LAUNCHER" />
        </intent>
        <intent>
            <action android:name="androidx.wear.tiles.action.BIND_UPDATE_REQUESTER" />
        </intent>
    </queries>

    <application
        android:allowBackup="true"
        android:extractNativeLibs="true"
        android:icon="@drawable/preview_circular"
        android:label="Словами"
        android:supportsRtl="true"
        android:hasCode="true">

        <uses-library
            android:name="com.google.android.wearable"
            android:required="false" />

        <meta-data
            android:name="com.google.android.wearable.standalone"
            android:value="true" />

        <activity
            android:name="com.samsung.android.wearable.watchfacestudio.editor.EditorActivity"
            android:exported="true"
            android:excludeFromRecents="true"
            android:label="Config Activity"
            android:theme="@android:style/Theme.DeviceDefault.NoActionBar">
            <intent-filter>
                <action android:name="androidx.wear.watchface.editor.action.WATCH_FACE_EDITOR" />
                <category android:name="com.google.android.wearable.watchface.category.WEARABLE_CONFIGURATION" />
                <category android:name="android.intent.category.DEFAULT" />
            </intent-filter>
        </activity>

        <receiver
            android:name="com.samsung.watchface.debug.DebugBroadcastReceiver"
            android:exported="true">
            <intent-filter>
                <action android:name="com.samsung.watchface.DEBUG_WATCH_FACE" />
            </intent-filter>
        </receiver>

        <service
            android:name="com.samsung.android.wearable.watchfacestudio.WatchFaceStudioRuntime"
            android:directBootAware="true"
            android:enabled="true"
            android:exported="true"
            android:label="Словами"
            android:permission="android.permission.BIND_WALLPAPER">
            <intent-filter>
                <action android:name="android.intent.action.LOCKED_BOOT_COMPLETED" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.service.wallpaper.WallpaperService" />
                <category android:name="com.google.android.wearable.watchface.category.WATCH_FACE" />
            </intent-filter>

            <meta-data
                android:name="android.service.wallpaper"
                android:resource="@xml/watch_face" />
            <meta-data
                android:name="android.service.wallpaper.square_mode"
                android:value="false" />
            <meta-data
                android:name="com.google.android.wearable.watchface.preview"
                android:resource="@drawable/preview_circular" />
            <meta-data
                android:name="com.google.android.wearable.watchface.preview_circular"
                android:resource="@drawable/preview_circular" />
            <meta-data
                android:name="com.google.android.wearable.watchface.wearableConfigurationAction"
                android:value="androidx.wear.watchface.editor.action.WATCH_FACE_EDITOR" />
            <meta-data
                android:name="com.google.android.wearable.watchface.companionBuiltinConfigurationEnabled"
                android:value="true" />
            <meta-data
                android:name="androidx.wear.watchface.MULTIPLE_INSTANCES_ALLOWED"
                android:value="false" />
            <meta-data
                android:name="androidx.wear.watchface.api_version"
                android:value="5" />
            <meta-data
                android:name="androidx.wear.watchface.xml_version"
                android:value="2" />
            <meta-data
                android:name="com.samsung.android.watch.watchface.config.vi.launching"
                android:value="com.samsung.android.watch.watchface.config.vi.launching.REQUIRE_PREVIEW" />
            <meta-data
                android:name="com.samsung.watchfacestudio.category"
                android:value=" /> " />
            <meta-data
                android:name="com.samsung.watchfacestudio.version"
                android:value="1.3.13" />
            <meta-data
                android:name="com.samsung.watchfacestudio.xml.version"
                android:value="11" />
        </service>

    </application>
</manifest>
""")

# 6. res/xml/watch_face.xml и полноценный res/xml/watchface.xml (по схеме 1.1.1 из дампа wb.illuminator.two)
with open("app/src/main/res/xml/watch_face.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<wallpaper xmlns:android="http://schemas.android.com/apk/res/android" />
""")

with open("app/src/main/res/xml/watchface.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<Watchface width="450" height="450" schemeVersion="1.1.1">
    <Metadata key="CLOCK_TYPE" value="DIGITAL" />
    <Metadata key="PREVIEW_TIME" value="10:08:32" />
    <Scene backgroundColor="#ff000000" ambientBackgroundColor="#ff000000">
        <Group name="RootGroup" x="0" y="0" width="450" height="450" alpha="255" alphaAmbient="255">
            <PartText name="TimeText" x="75" y="180" width="320" height="100" alpha="255" alphaAmbient="255">
                <Text align="START" ellipsis="false">
                    <Font family="minecraft" size="38" color="#ffffffff" weight="NORMAL">
                        <Template>%s<Parameter expression="[HOUR_0_23]" /></Template>
                    </Font>
                </Text>
            </PartText>
        </Group>
    </Scene>
</Watchface>
""")

# 7. Генерация растрового preview_circular.png (450x450) в drawable-nodpi
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
with open("app/src/main/res/drawable-nodpi/preview_circular.png", "wb") as f:
    f.write(png)

# 8. WatchFaceStudioRuntime.kt
with open("app/src/main/java/com/samsung/android/wearable/watchfacestudio/WatchFaceStudioRuntime.kt", "w", encoding="utf-8") as f:
    f.write("""package com.samsung.android.wearable.watchfacestudio

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.Typeface
import android.view.SurfaceHolder
import androidx.wear.watchface.CanvasType
import androidx.wear.watchface.ComplicationSlotsManager
import androidx.wear.watchface.DrawMode
import androidx.wear.watchface.Renderer
import androidx.wear.watchface.WatchFace
import androidx.wear.watchface.WatchFaceService
import androidx.wear.watchface.WatchFaceType
import androidx.wear.watchface.WatchState
import androidx.wear.watchface.style.CurrentUserStyleRepository
import java.time.ZonedDateTime

object RussianTimeFormatter {
    private val nom = listOf(
        "", "один", "два", "три", "четыре", "пять",
        "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать"
    )
    private val gen = listOf(
        "", "первого", "второго", "третьего", "четвертого", "пятого",
        "шестого", "седьмого", "восьмого", "девятого", "десятого", "одиннадцатого", "двенадцатого"
    )

    fun format(hour: Int, minute: Int): Pair<List<String>, Int> {
        val h12 = if (hour % 12 == 0) 12 else hour % 12
        val nextH = if ((hour + 1) % 12 == 0) 12 else (hour + 1) % 12
        val tod = when (hour) {
            in 4..11 -> "утра"
            in 12..16 -> "дня"
            in 17..22 -> "вечера"
            else -> "ночи"
        }

        return when {
            minute == 0 -> {
                val lines = when (h12) {
                    1 -> listOf("час", tod)
                    in 2..4 -> listOf(nom[h12], "часа", tod)
                    else -> listOf(nom[h12], "часов", tod)
                }
                Pair(lines, 0)
            }
            minute == 15 -> Pair(listOf("четверть", gen[nextH]), 1)
            minute == 30 -> Pair(listOf("половина", gen[nextH]), 1)
            minute == 45 -> Pair(listOf("без", "четверти", nom[nextH]), 2)
            minute == 35 -> Pair(listOf("без", "двадцати", "пяти", nom[nextH]), 3)
            minute in 31..39 -> {
                val mWords = when (minute) {
                    31 -> listOf("тридцать", "одна")
                    32 -> listOf("тридцать", "две")
                    33 -> listOf("тридцать", "три")
                    34 -> listOf("тридцать", "четыре")
                    36 -> listOf("тридцать", "шесть")
                    37 -> listOf("тридцать", "семь")
                    38 -> listOf("тридцать", "восемь")
                    else -> listOf("тридцать", "девять")
                }
                val lines = listOf(nom[h12]) + mWords
                Pair(lines, 0)
            }
            minute < 30 -> {
                val mWords = when (minute) {
                    1 -> listOf("одна", "минута")
                    2 -> listOf("две", "минуты")
                    3 -> listOf("три", "минуты")
                    4 -> listOf("четыре", "минуты")
                    5 -> listOf("пять", "минут")
                    6 -> listOf("шесть", "минут")
                    7 -> listOf("семь", "минут")
                    8 -> listOf("восемь", "минут")
                    9 -> listOf("девять", "минут")
                    10 -> listOf("десять", "минут")
                    11 -> listOf("одиннадцать", "минут")
                    12 -> listOf("двенадцать", "минут")
                    13 -> listOf("тринадцать", "минут")
                    14 -> listOf("четырнадцать", "минут")
                    16 -> listOf("шестнадцать", "минут")
                    17 -> listOf("семнадцать", "минут")
                    18 -> listOf("восем", "надцать", "минут")
                    19 -> listOf("девят", "надцать", "минут")
                    20 -> listOf("двадцать", "минут")
                    21 -> listOf("двадцать", "одна", "минута")
                    22 -> listOf("двадцать", "две", "минуты")
                    23 -> listOf("двадцать", "три", "минуты")
                    24 -> listOf("двадцать", "четыре", "минуты")
                    25 -> listOf("двадцать", "пять", "минут")
                    26 -> listOf("двадцать", "шесть", "минут")
                    27 -> listOf("двадцать", "семь", "минут")
                    28 -> listOf("двадцать", "восемь", "минут")
                    else -> listOf("двадцать", "девять", "минут")
                }
                val lines = mWords + listOf(gen[nextH])
                Pair(lines, lines.lastIndex)
            }
            else -> {
                val left = 60 - minute
                val leftWords = when (left) {
                    1 -> listOf("без", "одной", "минуты")
                    2 -> listOf("без", "двух", "минут")
                    3 -> listOf("без", "трех", "минут")
                    4 -> listOf("без", "четырех", "минут")
                    5 -> listOf("без", "пяти")
                    6 -> listOf("без", "шести")
                    7 -> listOf("без", "семи")
                    8 -> listOf("без", "восьми")
                    9 -> listOf("без", "девяти")
                    10 -> listOf("без", "десяти")
                    11 -> listOf("без", "один", "надцати")
                    12 -> listOf("без", "две", "надцати")
                    13 -> listOf("без", "три", "надцати")
                    14 -> listOf("без", "четыр", "надцати")
                    16 -> listOf("без", "шест", "надцати")
                    17 -> listOf("без", "сем", "надцати")
                    18 -> listOf("без", "восем", "надцати")
                    19 -> listOf("без", "девят", "надцати")
                    else -> listOf("без", "двадцати")
                }
                val lines = leftWords + listOf(nom[nextH])
                Pair(lines, lines.lastIndex)
            }
        }
    }
}

class WatchFaceStudioRuntime : WatchFaceService() {
    override suspend fun createWatchFace(
        surfaceHolder: SurfaceHolder,
        watchState: WatchState,
        complicationSlotsManager: ComplicationSlotsManager,
        currentUserStyleRepository: CurrentUserStyleRepository
    ): WatchFace {
        val renderer = WordCanvasRenderer(
            context = applicationContext,
            surfaceHolder = surfaceHolder,
            currentUserStyleRepository = currentUserStyleRepository,
            watchState = watchState
        )
        return WatchFace(
            watchFaceType = WatchFaceType.DIGITAL,
            renderer = renderer
        )
    }
}

class WordCanvasRenderer(
    private val context: Context,
    surfaceHolder: SurfaceHolder,
    currentUserStyleRepository: CurrentUserStyleRepository,
    watchState: WatchState
) : Renderer.CanvasRenderer(
    surfaceHolder = surfaceHolder,
    currentUserStyleRepository = currentUserStyleRepository,
    watchState = watchState,
    canvasType = CanvasType.HARDWARE,
    interactiveDrawModeUpdateDelayMillis = 1000L
) {
    private val pixelFont: Typeface by lazy {
        try {
            Typeface.createFromAsset(context.assets, "minecraft.ttf")
        } catch (e: Exception) {
            Typeface.MONOSPACE
        }
    }

    private val paintRegular = Paint().apply {
        color = Color.WHITE
        textAlign = Paint.Align.LEFT
        isAntiAlias = false
    }

    private val paintBold = Paint().apply {
        color = Color.WHITE
        textAlign = Paint.Align.LEFT
        isAntiAlias = false
        isFakeBoldText = true
    }

    override fun render(
        canvas: Canvas,
        bounds: Rect,
        zonedDateTime: ZonedDateTime
    ) {
        val isAmbient = renderParameters.drawMode == DrawMode.AMBIENT
        canvas.drawColor(Color.BLACK)

        paintRegular.typeface = pixelFont
        paintBold.typeface = pixelFont

        if (isAmbient) {
            paintRegular.style = Paint.Style.STROKE
            paintRegular.strokeWidth = bounds.width() * 0.005f
            paintRegular.isFakeBoldText = false

            paintBold.style = Paint.Style.STROKE
            paintBold.strokeWidth = bounds.width() * 0.011f
            paintBold.isFakeBoldText = false
        } else {
            paintRegular.style = Paint.Style.FILL
            paintRegular.isFakeBoldText = false

            paintBold.style = Paint.Style.FILL
            paintBold.isFakeBoldText = true
        }

        val (lines, boldIndex) = RussianTimeFormatter.format(zonedDateTime.hour, zonedDateTime.minute)
        val fontSize = bounds.width() * 0.088f
        val lineSpacing = fontSize * 1.32f

        paintRegular.textSize = fontSize
        paintBold.textSize = fontSize

        val startX = bounds.left + bounds.width() * 0.18f
        var startY = bounds.centerY() - (lines.size * lineSpacing / 2f) + fontSize * 0.8f

        for (i in lines.indices) {
            val p = if (i == boldIndex) paintBold else paintRegular
            canvas.drawText(lines[i], startX, startY, p)
            startY += lineSpacing
        }
    }

    override fun renderHighlightLayer(
        canvas: Canvas,
        bounds: Rect,
        zonedDateTime: ZonedDateTime
    ) {}
}
""")

# 9. EditorActivity.kt и DebugBroadcastReceiver.kt (чтобы все компоненты из манифеста wb.illuminator.two существовали)
with open("app/src/main/java/com/samsung/android/wearable/watchfacestudio/editor/EditorActivity.kt", "w", encoding="utf-8") as f:
    f.write("""package com.samsung.android.wearable.watchfacestudio.editor

import android.app.Activity
import android.os.Bundle

class EditorActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        finish()
    }
}
""")

with open("app/src/main/java/com/samsung/watchface/debug/DebugBroadcastReceiver.kt", "w", encoding="utf-8") as f:
    f.write("""package com.samsung.watchface.debug

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class DebugBroadcastReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {}
}
""")
