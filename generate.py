import os
import zlib
import struct
import math

# 1. build.gradle.kts
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
        versionCode = 1
        versionName = "1.0"
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

    <application
        android:allowBackup="true"
        android:icon="@drawable/preview"
        android:label="Русские часы"
        android:hasCode="true">

        <service
            android:name=".WordWatchFaceService"
            android:exported="true"
            android:label="Русские часы"
            android:permission="android.permission.BIND_WALLPAPER">

            <intent-filter>
                <action android:name="android.service.wallpaper.WallpaperService" />
                <category android:name="com.google.android.wearable.watchface.category.WATCH_FACE" />
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
        </service>

    </application>
</manifest>
""")

# 5. res/xml/watch_face.xml
with open("app/src/main/res/xml/watch_face.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<wallpaper xmlns:android="http://schemas.android.com/apk/res/android" />
""")

# 6. preview.png
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
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
with open("app/src/main/res/drawable/preview.png", "wb") as f:
    f.write(png)

# 7. WordWatchFaceService.kt
with open("app/src/main/java/com/example/wordclock/WordWatchFaceService.kt", "w", encoding="utf-8") as f:
    f.write("""package com.example.wordclock

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.Typeface
import android.view.SurfaceHolder
import androidx.wear.watchface.CanvasType
import androidx.wear.watchface.ComplicationSlotsManager
import androidx.wear.watchface.Renderer
import androidx.wear.watchface.WatchFace
import androidx.wear.watchface.WatchFaceService
import androidx.wear.watchface.WatchFaceType
import androidx.wear.watchface.WatchState
import androidx.wear.watchface.style.CurrentUserStyleRepository
import java.time.ZonedDateTime

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
    private val textPaint = Paint().apply {
        isAntiAlias = true
        color = Color.WHITE
        textSize = 36f
        try {
            typeface = Typeface.createFromAsset(context.assets, "minecraft.ttf")
        } catch (e: Exception) {
            typeface = Typeface.MONOSPACE
        }
    }

    override fun render(
        canvas: Canvas,
        bounds: Rect,
        zonedDateTime: ZonedDateTime
    ) {
        canvas.drawColor(Color.BLACK)
        val hour = zonedDateTime.hour
        val minute = zonedDateTime.minute
        val lines = getRussianTime(hour, minute)

        val n = lines.size
        val startY = if (n == 2) 180f else if (n == 3) 145f else 120f
        val step = if (n == 2) 56f else if (n == 3) 54f else 52f

        lines.forEachIndexed { i, line ->
            val y = startY + i * step
            canvas.drawText(line, 75f, y, textPaint)
        }
    }

    override fun renderHighlightLayer(
        canvas: Canvas,
        bounds: Rect,
        zonedDateTime: ZonedDateTime
    ) {
    }

    private fun getRussianTime(hour: Int, minute: Int): List<String> {
        val h12 = if (hour % 12 == 0) 12 else hour % 12
        val nextH = if ((hour + 1) % 12 == 0) 12 else (hour + 1) % 12
        val nom = listOf("", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать")
        val gen = listOf("", "первого", "второго", "третьего", "четвертого", "пятого", "шестого", "седьмого", "восьмого", "девятого", "десятого", "одиннадцатого", "двенадцатого")
        val tod = if (hour in 4..11) "утра" else if (hour in 12..16) "дня" else if (hour in 17..22) "вечера" else "ночи"

        return when {
            minute == 0 -> {
                when (h12) {
                    1 -> listOf("час", tod)
                    in 2..4 -> listOf(nom[h12], "часа", tod)
                    else -> listOf(nom[h12], "часов", tod)
                }
            }
            minute == 15 -> listOf("четверть", gen[nextH])
            minute == 30 -> listOf("половина", gen[nextH])
            minute == 45 -> listOf("без", "четверти", nom[nextH])
            minute == 35 -> listOf("без", "двадцати", "пяти", nom[nextH])
            minute in 31..39 -> {
                val mWords = mapOf(
                    31 to listOf("тридцать", "одна"),
                    32 to listOf("тридцать", "две"),
                    33 to listOf("тридцать", "три"),
                    34 to listOf("тридцать", "четыре"),
                    36 to listOf("тридцать", "шесть"),
                    37 to listOf("тридцать", "семь"),
                    38 to listOf("тридцать", "восемь"),
                    39 to listOf("тридцать", "девять")
                )[minute] ?: listOf()
                listOf(nom[h12]) + mWords
            }
            minute < 30 -> {
                val mMap = mapOf(
                    1 to listOf("одна", "минута"), 2 to listOf("две", "минуты"), 3 to listOf("три", "минуты"),
                    4 to listOf("четыре", "минуты"), 5 to listOf("пять", "минут"), 6 to listOf("шесть", "минут"),
                    7 to listOf("семь", "минут"), 8 to listOf("восемь", "минут"), 9 to listOf("девять", "минут"),
                    10 to listOf("десять", "минут"), 11 to listOf("одиннадцать", "минут"), 12 to listOf("двенадцать", "минут"),
                    13 to listOf("тринадцать", "минут"), 14 to listOf("четырнадцать", "минут"), 16 to listOf("шестнадцать", "минут"),
                    17 to listOf("семнадцать", "минут"), 18 to listOf("восемнадцать", "минут"), 19 to listOf("девятнадцать", "минут"),
                    20 to listOf("двадцать", "минут"), 21 to listOf("двадцать", "одна", "минута"), 22 to listOf("двадцать", "две", "минуты"),
                    23 to listOf("двадцать", "три", "минуты"), 24 to listOf("двадцать", "четыре", "минуты"), 25 to listOf("двадцать", "пять", "минут"),
                    26 to listOf("двадцать", "шесть", "минут"), 27 to listOf("двадцать", "семь", "минут"), 28 to listOf("двадцать", "восемь", "минут"),
                    29 to listOf("двадцать", "девять", "минут")
                )[minute] ?: listOf()
                mMap + listOf(gen[nextH])
            }
            else -> {
                val left = 60 - minute
                val leftMap = mapOf(
                    1 to listOf("без", "одной", "минуты"), 2 to listOf("без", "двух", "минут"), 3 to listOf("без", "трех", "минут"),
                    4 to listOf("без", "четырех", "минут"), 5 to listOf("без", "пяти"), 6 to listOf("без", "шести"),
                    7 to listOf("без", "семи"), 8 to listOf("без", "восьми"), 9 to listOf("без", "девяти"),
                    10 to listOf("без", "десяти"), 11 to listOf("без", "одиннадцати"), 12 to listOf("двенадцати"),
                    13 to listOf("без", "тринадцати"), 14 to listOf("без", "четырнадцати"), 16 to listOf("без", "шестнадцати"),
                    17 to listOf("без", "семнадцати"), 18 to listOf("без", "восем", "надцати"), 19 to listOf("девятнадцати"),
                    20 to listOf("без", "двадцати")
                )[left] ?: listOf()
                leftMap + listOf(nom[nextH])
            }
        }
    }
}
""")
