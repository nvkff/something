import os
import sys
import math
import json
import zlib
import struct
import zipfile
import urllib.request
import shutil

# 0. Встроенный чистый PNG-декодер и энкодер (без Pillow и pip)
def read_png_rgba(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    idat = bytearray()
    plte = None
    trns = None
    w = h = depth = ctype = 0
    while pos < len(data):
        length = struct.unpack("!I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            w, h, depth, ctype, _, _, _ = struct.unpack("!IIBBBBB", chunk_data)
        elif tag == b"PLTE":
            plte = chunk_data
        elif tag == b"tRNS":
            trns = chunk_data
        elif tag == b"IDAT":
            idat.extend(chunk_data)
        elif tag == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    bpp_map = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    row_bytes = (w * bpp_map[ctype] * depth + 7) // 8
    filt_bpp = max(1, (bpp_map[ctype] * depth + 7) // 8)

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        return b if pb <= pc else c

    rows = []
    idx = 0
    prev = bytearray(row_bytes)
    for _ in range(h):
        ftype = raw[idx]
        idx += 1
        scan = bytearray(raw[idx:idx + row_bytes])
        idx += row_bytes
        for i in range(row_bytes):
            a = scan[i - filt_bpp] if i >= filt_bpp else 0
            b = prev[i]
            c = prev[i - filt_bpp] if i >= filt_bpp else 0
            if ftype == 1:
                scan[i] = (scan[i] + a) & 0xff
            elif ftype == 2:
                scan[i] = (scan[i] + b) & 0xff
            elif ftype == 3:
                scan[i] = (scan[i] + ((a + b) >> 1)) & 0xff
            elif ftype == 4:
                scan[i] = (scan[i] + paeth(a, b, c)) & 0xff
        prev = scan
        rows.append(scan)

    pixels = []
    for y in range(h):
        row = rows[y]
        prow = []
        if ctype == 6 and depth == 8:
            for x in range(w):
                prow.append((row[x * 4], row[x * 4 + 1], row[x * 4 + 2], row[x * 4 + 3]))
        elif ctype == 2 and depth == 8:
            for x in range(w):
                prow.append((row[x * 3], row[x * 3 + 1], row[x * 3 + 2], 255))
        elif ctype == 4 and depth == 8:
            for x in range(w):
                g = row[x * 2]
                prow.append((g, g, g, row[x * 2 + 1]))
        elif ctype == 3:
            if depth == 8:
                vals = list(row)
            else:
                vals = []
                mask = (1 << depth) - 1
                for byte in row:
                    for shift in range(8 - depth, -1, -depth):
                        vals.append((byte >> shift) & mask)
            for x in range(w):
                pi = vals[x]
                r, g, b = plte[pi * 3], plte[pi * 3 + 1], plte[pi * 3 + 2]
                a = trns[pi] if (trns is not None and pi < len(trns)) else 255
                prow.append((r, g, b, a))
        elif ctype == 0:
            if depth == 8:
                vals = list(row)
            else:
                vals = []
                mask = (1 << depth) - 1
                for byte in row:
                    for shift in range(8 - depth, -1, -depth):
                        vals.append((byte >> shift) & mask)
            maxv = (1 << depth) - 1
            for x in range(w):
                g = vals[x] * 255 // maxv
                prow.append((g, g, g, 255))
        pixels.append(prow)
    return w, h, pixels

def write_png_rgba(filename, w, h, pixels):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for r, g, b, a in pixels[y]:
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

def upscale_nearest(pixels, src_w, src_h, dst_w, dst_h):
    out = []
    for y in range(dst_h):
        sy = (y * src_h) // dst_h
        srow = pixels[sy]
        out.append([srow[(x * src_w) // dst_w] for x in range(dst_w)])
    return out

# 1. Корневой build.gradle.kts (подключаем Kotlin для работы с датчиками)
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
rootProject.name = "MinecraftCompass"
include(":app")
""")

# 3. app/build.gradle.kts (Отдельное приложение под Wear OS)
os.makedirs("app", exist_ok=True)
with open("app/build.gradle.kts", "w", encoding="utf-8") as f:
    f.write("""plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.minecraft.compassapp"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.minecraft.compassapp"
        minSdk = 30
        targetSdk = 34
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
            enableV3Signing = false
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
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
""")

# 4. Очистка старых папок и подготовка новых
if os.path.exists("app/src/main/java"):
    shutil.rmtree("app/src/main/java")
if os.path.exists("app/src/main/res"):
    shutil.rmtree("app/src/main/res")

os.makedirs("app/src/main/res/drawable-nodpi", exist_ok=True)
os.makedirs("app/src/main/res/values", exist_ok=True)
os.makedirs("app/src/main/java/com/minecraft/compassapp", exist_ok=True)

# 5. res/values/strings.xml
with open("app/src/main/res/values/strings.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Компас</string>
</resources>
""")

# 6. AndroidManifest.xml (Standalone Wear OS приложение)
with open("app/src/main/AndroidManifest.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature android:name="android.hardware.type.watch" />
    <uses-feature android:name="android.hardware.sensor.compass" android:required="false" />

    <application
        android:allowBackup="true"
        android:icon="@drawable/ic_launcher"
        android:label="@string/app_name">

        <meta-data
            android:name="com.google.android.wearable.standalone"
            android:value="true" />

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:label="@string/app_name"
            android:theme="@android:style/Theme.DeviceDefault.NoActionBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

    </application>
</manifest>
""")

# 7. Скачивание 32 оригинальных текстур compass_00..compass_31 из Mojang client.jar
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

frame_angles = []
icon_pixels = None

with zipfile.ZipFile(jar_path, "r") as zf:
    names = zf.namelist()
    for k in range(32):
        target_suffix = f"textures/item/compass_{k:02d}.png"
        entry = next(n for n in names if n.endswith(target_suffix))
        raw_png = zf.read(entry)
        sw, sh, spixels = read_png_rgba(raw_png)

        # Автоматически вычисляем точный угол красной стрелки (0° = Вверх, 90° = Вправо, 180° = Вниз)
        sum_x = 0.0
        sum_y = 0.0
        cx_center = (sw - 1) / 2.0
        cy_center = (sh - 1) / 2.0
        for y in range(sh):
            for x in range(sw):
                r, g, b, a = spixels[y][x]
                if a > 128 and r > 140 and r > g * 1.7 and r > b * 1.7:
                    dx = x - cx_center
                    dy = y - cy_center
                    dist = math.hypot(dx, dy)
                    sum_x += dx * dist
                    sum_y += dy * dist
        angle = (math.degrees(math.atan2(sum_x, -sum_y)) + 360.0) % 360.0
        frame_angles.append(round(angle, 2))

        scaled = upscale_nearest(spixels, sw, sh, 448, 448)
        write_png_rgba(f"app/src/main/res/drawable-nodpi/compass_{k:02d}.png", 448, 448, scaled)

        # Иконка приложения — кадр, смотрящий максимально вверх (Север)
        if icon_pixels is None or abs(angle) < 12 or abs(angle - 360) < 12:
            icon_pixels = upscale_nearest(spixels, sw, sh, 192, 192)

write_png_rgba("app/src/main/res/drawable-nodpi/ic_launcher.png", 192, 192, icon_pixels)

# 8. Генерация MainActivity.kt (магнитометр + плавная анимация + режим Магнетит)
angles_str = ", ".join(f"{a}f" for a in frame_angles)
res_list_str = ",\n        ".join(f"R.drawable.compass_{k:02d}" for k in range(32))

kotlin_code = f"""package com.minecraft.compassapp

import android.app.Activity
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LightingColorFilter
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.Typeface
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import android.view.GestureDetector
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import kotlin.math.abs
import kotlin.math.roundToInt

class MainActivity : Activity(), SensorEventListener {{

    private lateinit var sensorManager: SensorManager
    private var rotationSensor: Sensor? = null
    private var accelSensor: Sensor? = null
    private var magnetSensor: Sensor? = null

    private val gravity = FloatArray(3)
    private val geomagnetic = FloatArray(3)
    private var hasGravity = false
    private var hasMagnet = false

    private var rawAzimuth = 0f
    private var smoothAzimuth = 0f
    private var lodestoneBearing: Float? = null
    private var showOverlay = true

    private lateinit var compassView: CompassView

    private val frameAngles = floatArrayOf({angles_str})
    private val frameResIds = intArrayOf(
        {res_list_str}
    )

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
        if (rotationSensor == null) {{
            accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            magnetSensor = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)
        }}

        compassView = CompassView(this)
        setContentView(compassView)
    }}

    override fun onResume() {{
        super.onResume()
        rotationSensor?.let {{
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME)
        }} ?: run {{
            accelSensor?.let {{ sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }}
            magnetSensor?.let {{ sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }}
        }}
    }}

    override fun onPause() {{
        super.onPause()
        sensorManager.unregisterListener(this)
    }}

    override fun onSensorChanged(event: SensorEvent) {{
        if (event.sensor.type == Sensor.TYPE_ROTATION_VECTOR) {{
            val rMat = FloatArray(9)
            val orientation = FloatArray(3)
            SensorManager.getRotationMatrixFromVector(rMat, event.values)
            SensorManager.getOrientation(rMat, orientation)
            var deg = Math.toDegrees(orientation[0].toDouble()).toFloat()
            if (deg < 0f) deg += 360f
            rawAzimuth = deg
            compassView.postInvalidateOnAnimation()
        }} else if (event.sensor.type == Sensor.TYPE_ACCELEROMETER) {{
            System.arraycopy(event.values, 0, gravity, 0, 3)
            hasGravity = true
            updateFallback()
        }} else if (event.sensor.type == Sensor.TYPE_MAGNETIC_FIELD) {{
            System.arraycopy(event.values, 0, geomagnetic, 0, 3)
            hasMagnet = true
            updateFallback()
        }}
    }}

    private fun updateFallback() {{
        if (!hasGravity || !hasMagnet) return
        val rMat = FloatArray(9)
        val iMat = FloatArray(9)
        if (SensorManager.getRotationMatrix(rMat, iMat, gravity, geomagnetic)) {{
            val orientation = FloatArray(3)
            SensorManager.getOrientation(rMat, orientation)
            var deg = Math.toDegrees(orientation[0].toDouble()).toFloat()
            if (deg < 0f) deg += 360f
            rawAzimuth = deg
            compassView.postInvalidateOnAnimation()
        }}
    }}

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {{}}

    private fun shortestAngleDiff(from: Float, to: Float): Float {{
        var diff = (to - from) % 360f
        if (diff > 180f) diff -= 360f
        if (diff < -180f) diff += 360f
        return diff
    }}

    private fun cardinalRu(deg: Float): String {{
        val dirs = arrayOf("С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ")
        val idx = (((deg + 22.5f) % 360f) / 45f).toInt() and 7
        return dirs[idx]
    }}

    private inner class CompassView(context: Context) : View(context) {{
        private val opts = BitmapFactory.Options().apply {{ inScaled = false }}
        private val bitmaps: Array<Bitmap> = Array(32) {{ idx ->
            BitmapFactory.decodeResource(resources, frameResIds[idx], opts)
        }}

        private val imgPaint = Paint().apply {{
            isFilterBitmap = false
            isAntiAlias = false
        }}

        private val lodestoneFilter = LightingColorFilter(0xFFE0B0FF.toInt(), 0x00240044)

        private val pixelFont: Typeface by lazy {{
            try {{
                Typeface.createFromAsset(assets, "minecraft.ttf")
            }} catch (_: Exception) {{
                Typeface.MONOSPACE
            }}
        }}

        private val textPaint = Paint().apply {{
            color = Color.WHITE
            textAlign = Paint.Align.CENTER
            isAntiAlias = false
        }}

        private val shadowPaint = Paint().apply {{
            color = 0xFF222222.toInt()
            textAlign = Paint.Align.CENTER
            isAntiAlias = false
        }}

        private val dstRect = Rect()

        private val gestureDetector = GestureDetector(context, object : GestureDetector.SimpleOnGestureListener() {{
            override fun onDown(e: MotionEvent): Boolean = true

            override fun onSingleTapConfirmed(e: MotionEvent): Boolean {{
                showOverlay = !showOverlay
                invalidate()
                return true
            }}

            override fun onLongPress(e: MotionEvent) {{
                performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
                lodestoneBearing = if (lodestoneBearing == null) smoothAzimuth else null
                invalidate()
            }}
        }})

        override fun onTouchEvent(event: MotionEvent): Boolean {{
            gestureDetector.onTouchEvent(event)
            return true
        }}

        override fun onDraw(canvas: Canvas) {{
            super.onDraw(canvas)
            canvas.drawColor(Color.BLACK)

            // Плавная интерполяция угла
            val diff = shortestAngleDiff(smoothAzimuth, rawAzimuth)
            if (abs(diff) > 0.25f) {{
                smoothAzimuth = (smoothAzimuth + diff * 0.22f + 360f) % 360f
                postInvalidateOnAnimation()
            }} else {{
                smoothAzimuth = rawAzimuth
            }}

            // Целевой угол стрелки на экране (0° = Вверх)
            val targetOffset = lodestoneBearing ?: 0f
            val needleAngle = (targetOffset - smoothAzimuth + 720f) % 360f

            // Ищем ближайший из 32 оригинальных спрайтов Mojang
            var bestIdx = 0
            var bestDiff = 999f
            for (i in 0 until 32) {{
                val d = abs(shortestAngleDiff(needleAngle, frameAngles[i]))
                if (d < bestDiff) {{
                    bestDiff = d
                    bestIdx = i
                }}
            }}

            // Рисуем квадрат по центру экрана
            val size = (minOf(width, height) * 0.92f).toInt()
            val left = (width - size) / 2
            val top = (height - size) / 2
            dstRect.set(left, top, left + size, top + size)

            imgPaint.colorFilter = if (lodestoneBearing != null) lodestoneFilter else null
            canvas.drawBitmap(bitmaps[bestIdx], null, dstRect, imgPaint)

            if (showOverlay) {{
                textPaint.typeface = pixelFont
                shadowPaint.typeface = pixelFont
                val fontSize = width * 0.068f
                textPaint.textSize = fontSize
                shadowPaint.textSize = fontSize

                val locked = lodestoneBearing
                val label = if (locked != null) {{
                    textPaint.color = 0xFFD99BFF.toInt()
                    "МАГНЕТИТ ${{locked.roundToInt()}}°"
                }} else {{
                    textPaint.color = Color.WHITE
                    val degInt = smoothAzimuth.roundToInt() % 360
                    "${{cardinalRu(smoothAzimuth)}} ${{degInt}}°"
                }}

                val ty = height * 0.86f
                canvas.drawText(label, width / 2f + 2f, ty + 2f, shadowPaint)
                canvas.drawText(label, width / 2f, ty, textPaint)
            }}
        }}
    }}
}}
"""

with open("app/src/main/java/com/minecraft/compassapp/MainActivity.kt", "w", encoding="utf-8") as f:
    f.write(kotlin_code)
