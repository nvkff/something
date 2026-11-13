import os
import zlib
import struct
import math

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
    namespace = "com.example.wordclock"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.wordclock"
        minSdk = 28
        targetSdk = 30
        versionCode = 2
        versionName = "2.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
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

# 4. AndroidManifest.xml
os.makedirs("app/src/main/res/xml", exist_ok=True)
os.makedirs("app/src/main/res/drawable", exist_ok=True)
os.makedirs("app/src/main/assets", exist_ok=True)
os.makedirs("app/src/main/java/com/example/wordclock", exist_ok=True)

with open("app/src/main/AndroidManifest.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature android:name="android.hardware.type.watch" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="com.google.android.permission.PROVIDE_BACKGROUND" />

    <application
        android:allowBackup="true"
        android:icon="@drawable/preview"
        android:label="Русские часы"
        android:hasCode="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:label="Русские часы"
            android:theme="@android:style/Theme.DeviceDefault.NoActionBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".WordWatchFaceService"
            android:directBootAware="true"
            android:exported="true"
            android:icon="@drawable/preview"
            android:label="Словами"
            android:permission="android.permission.BIND_WALLPAPER">
            <intent-filter>
                <action android:name="android.service.wallpaper.WallpaperService" />
                <category android:name="com.google.android.wearable.watchface.category.WATCH_FACE" />
                <category android:name="android.intent.category.DEFAULT" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.LOCKED_BOOT_COMPLETED" />
            </intent-filter>

            <meta-data
                android:name="android.service.wallpaper"
                android:resource="@xml/watch_face" />
            <meta-data
                android:name="com.google.android.wearable.watchface.preview"
                android:resource="@drawable/preview" />
            <meta-data
                android:name="com.google.android.wearable.watchface.preview_circular"
                android:resource="@drawable/preview" />
            <meta-data
                android:name="com.google.android.wearable.watchface.wearableConfigurationAction"
                android:value="androidx.wear.watchface.editor.action.WATCH_FACE_EDITOR" />
            <meta-data
                android:name="com.google.android.wearable.watchface.companionBuiltinConfigurationEnabled"
                android:value="true" />
        </service>

    </application>
</manifest>
""")

# 5. res/xml/watch_face.xml
with open("app/src/main/res/xml/watch_face.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<wallpaper xmlns:android="http://schemas.android.com/apk/res/android"
    android:thumbnail="@drawable/preview" />
""")

# 6. Генерация растрового preview.png (400x400)
w, h = 400, 400
raw = bytearray()
for y in range(h):
    raw.append(0)
    for x in range(w):
        d = math.hypot(x - 200, y - 200)
        c = 255 if (180 <= d <= 192) else 0
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

# 7. WordWatchFaceService.kt + MainActivity.kt (полная логика всех 60 минут + AOD)
with open("app/src/main/java/com/example/wordclock/WordWatchFaceService.kt", "w", encoding="utf-8") as f:
    f.write("""package com.example.wordclock

import android.app.Activity
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.SurfaceHolder
import android.view.View
import android.view.WindowManager
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
                Pair(lines, 0) // жирным выделяется первая строка (сам час)
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
                Pair(lines, 0) // жирным выделяется первая строка (сам час)
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

class WordWatchFaceService : WatchFaceService() {
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

class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var clockView: View

    private val tickRunnable = object : Runnable {
        override fun run() {
            clockView.invalidate()
            handler.postDelayed(this, 1000L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        clockView = object : View(this) {
            private val pixelFont: Typeface by lazy {
                try {
                    Typeface.createFromAsset(assets, "minecraft.ttf")
                } catch (e: Exception) {
                    Typeface.MONOSPACE
                }
            }
            private val pReg = Paint().apply {
                color = Color.WHITE
                textAlign = Paint.Align.LEFT
                isAntiAlias = false
            }
            private val pBold = Paint().apply {
                color = Color.WHITE
                textAlign = Paint.Align.LEFT
                isAntiAlias = false
                isFakeBoldText = true
            }

            override fun onDraw(canvas: Canvas) {
                super.onDraw(canvas)
                canvas.drawColor(Color.BLACK)
                pReg.typeface = pixelFont
                pBold.typeface = pixelFont

                val now = ZonedDateTime.now()
                val (lines, boldIdx) = RussianTimeFormatter.format(now.hour, now.minute)
                val fontSize = width * 0.088f
                val lineSpacing = fontSize * 1.32f
                pReg.textSize = fontSize
                pBold.textSize = fontSize

                val startX = width * 0.18f
                var startY = (height / 2f) - (lines.size * lineSpacing / 2f) + fontSize * 0.8f

                for (i in lines.indices) {
                    canvas.drawText(lines[i], startX, startY, if (i == boldIdx) pBold else pReg)
                    startY += lineSpacing
                }
            }
        }
        setContentView(clockView)
    }

    override fun onResume() {
        super.onResume()
        handler.post(tickRunnable)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(tickRunnable)
    }
}
""")
