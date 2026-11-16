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
rootProject.name = "MinecraftCompass"
include(":app")
""")

# 3. gradle.properties (обязателен для AndroidX / androidx.wear:wear)
with open("gradle.properties", "w", encoding="utf-8") as f:
    f.write("""org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.nonTransitiveRClass=true
""")

# 4. app/build.gradle.kts (подключаем androidx.wear:wear для Ambient / AOD)
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

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.wear:wear:1.3.0")
    implementation("androidx.activity:activity-ktx:1.9.0")
}
""")

# 5. Очистка старых папок и подготовка новых
if os.path.exists("app/src/main/java"):
    shutil.rmtree("app/src/main/java")
if os.path.exists("app/src/main/res"):
    shutil.rmtree("app/src/main/res")

os.makedirs("app/src/main/res/drawable-nodpi", exist_ok=True)
os.makedirs("app/src/main/res/values", exist_ok=True)
os.makedirs("app/src/main/java/com/minecraft/compassapp", exist_ok=True)

# 6. res/values/strings.xml
with open("app/src/main/res/values/strings.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Компас</string>
</resources>
""")

# 7. AndroidManifest.xml (WAKE_LOCK + wearable library для поддержки AOD)
with open("app/src/main/AndroidManifest.xml", "w", encoding="utf-8") as f:
    f.write("""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature android:name="android.hardware.type.watch" />
    <uses-feature android:name="android.hardware.sensor.compass" android:required="false" />

    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

    <application
        android:allowBackup="true"
        android:icon="@drawable/ic_launcher"
        android:label="@string/app_name">

        <uses-library
            android:name="com.google.android.wearable"
            android:required="false" />

        <meta-data
            android:name="com.google.android.wearable.standalone"
            android:value="true" />

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleInstance"
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

# 8. Скачивание 32 оригинальных текстур compass_00..compass_31 из Mojang client.jar
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

        if icon_pixels is None or abs(angle) < 12 or abs(angle - 360) < 12:
            icon_pixels = upscale_nearest(spixels, sw, sh, 192, 192)

write_png_rgba("app/src/main/res/drawable-nodpi/ic_launcher.png", 192, 192, icon_pixels)

# 9. MainActivity.kt (AOD через AmbientLifecycleObserver + Магнетит GPS + Ручной ввод по двойному тапу)
angles_str = ", ".join(f"{a}f" for a in frame_angles)
res_list_str = ",\n        ".join(f"R.drawable.compass_{k:02d}" for k in range(32))

kotlin_code = f"""package com.minecraft.compassapp

import android.Manifest
import android.app.AlertDialog
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.PorterDuff
import android.graphics.PorterDuffXfermode
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.text.InputType
import android.view.GestureDetector
import android.view.Gravity
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.wear.ambient.AmbientLifecycleObserver
import java.util.Locale
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.roundToInt

class MainActivity : ComponentActivity(), SensorEventListener, LocationListener {{

    private lateinit var sensorManager: SensorManager
    private lateinit var locationManager: LocationManager
    private lateinit var ambientObserver: AmbientLifecycleObserver

    private var rotationSensor: Sensor? = null
    private var accelSensor: Sensor? = null
    private var magnetSensor: Sensor? = null

    private val gravity = FloatArray(3)
    private val geomagnetic = FloatArray(3)
    private var hasGravity = false
    private var hasMagnet = false

    private var hasFirstAzimuth = false
    private var rawAzimuth = 0f
    private var smoothAzimuth = 0f
    private var sensorAccuracy = SensorManager.SENSOR_STATUS_ACCURACY_HIGH
    private var isAmbient = false
    private var lastAmbientDrawMs = 0L

    // Механика Магнетита (GPS + ручной ввод + сохранение)
    private var isLodestoneActive = false
    private var pendingGpsLock = false
    private var currentLocation: Location? = null
    private var lodestoneLocation: Location? = null
    private var fallbackLodestoneBearing = 0f

    private var showOverlay = true
    private lateinit var compassView: CompassView

    private val frameAngles = floatArrayOf({angles_str})
    private val frameResIds = intArrayOf(
        {res_list_str}
    )

    private val ambientCallback = object : AmbientLifecycleObserver.AmbientLifecycleCallback {{
        override fun onEnterAmbient(ambientDetails: AmbientLifecycleObserver.AmbientDetails) {{
            isAmbient = true
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            compassView.invalidate()
        }}

        override fun onUpdateAmbient() {{
            compassView.invalidate()
        }}

        override fun onExitAmbient() {{
            isAmbient = false
            compassView.invalidate()
        }}
    }}

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)

        ambientObserver = AmbientLifecycleObserver(this, mainExecutor, ambientCallback)
        lifecycle.addObserver(ambientObserver)

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager

        rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
        if (rotationSensor == null) {{
            accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            magnetSensor = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)
        }}

        loadSavedLodestone()

        compassView = CompassView(this)
        setContentView(compassView)
    }}

    override fun onStart() {{
        super.onStart()
        rotationSensor?.let {{
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME)
        }} ?: run {{
            accelSensor?.let {{ sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }}
            magnetSensor?.let {{ sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }}
        }}
        startLocationIfPermitted()
    }}

    override fun onStop() {{
        super.onStop()
        sensorManager.unregisterListener(this)
        locationManager.removeUpdates(this)
    }}

    private fun loadSavedLodestone() {{
        val prefs = getSharedPreferences("mc_compass_prefs", Context.MODE_PRIVATE)
        if (prefs.getBoolean("lodestone_active", false)) {{
            val lat = prefs.getFloat("lodestone_lat", Float.NaN)
            val lon = prefs.getFloat("lodestone_lon", Float.NaN)
            if (!lat.isNaN() && !lon.isNaN()) {{
                lodestoneLocation = Location("saved").apply {{
                    latitude = lat.toDouble()
                    longitude = lon.toDouble()
                }}
                isLodestoneActive = true
                pendingGpsLock = false
            }}
        }}
    }}

    private fun saveLodestoneState(active: Boolean, loc: Location?) {{
        val editor = getSharedPreferences("mc_compass_prefs", Context.MODE_PRIVATE).edit()
        editor.putBoolean("lodestone_active", active && loc != null)
        if (active && loc != null) {{
            editor.putFloat("lodestone_lat", loc.latitude.toFloat())
            editor.putFloat("lodestone_lon", loc.longitude.toFloat())
        }}
        editor.apply()
    }}

    private fun hasLocationPermission(): Boolean {{
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }}

    private fun startLocationIfPermitted() {{
        if (!hasLocationPermission()) return
        try {{
            val gpsLast = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            val netLast = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            val bestLast = pickBetterLocation(gpsLast, netLast)
            if (bestLast != null) {{
                currentLocation = bestLast
            }}
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {{
                locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1500L, 1f, this)
            }}
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {{
                locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 2500L, 2f, this)
            }}
        }} catch (_: SecurityException) {{}}
    }}

    private fun pickBetterLocation(a: Location?, b: Location?): Location? {{
        if (a == null) return b
        if (b == null) return a
        return if (a.time >= b.time) a else b
    }}

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {{
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 100 && hasLocationPermission()) {{
            startLocationIfPermitted()
            if (pendingGpsLock && isLodestoneActive) {{
                val loc = currentLocation
                if (loc != null) {{
                    lodestoneLocation = Location(loc)
                    pendingGpsLock = false
                    saveLodestoneState(true, lodestoneLocation)
                }}
            }}
            compassView.invalidate()
        }}
    }}

    override fun onLocationChanged(location: Location) {{
        currentLocation = location
        if (isLodestoneActive && pendingGpsLock) {{
            lodestoneLocation = Location(location)
            pendingGpsLock = false
            saveLodestoneState(true, lodestoneLocation)
        }}
        if (!isAmbient) {{
            compassView.postInvalidateOnAnimation()
        }}
    }}

    override fun onSensorChanged(event: SensorEvent) {{
        sensorAccuracy = event.accuracy
        if (event.sensor.type == Sensor.TYPE_ROTATION_VECTOR) {{
            val rMat = FloatArray(9)
            SensorManager.getRotationMatrixFromVector(rMat, event.values)
            applyRotationMatrix(rMat)
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
            applyRotationMatrix(rMat)
        }}
    }}

    private fun applyRotationMatrix(rMat: FloatArray) {{
        val northX = rMat[3]
        val northY = rMat[4]
        if (northX * northX + northY * northY < 0.002f) return

        val northScreenAngle = Math.toDegrees(atan2(northX.toDouble(), northY.toDouble())).toFloat()
        val azimuth = (-northScreenAngle + 360f) % 360f

        rawAzimuth = azimuth
        if (!hasFirstAzimuth) {{
            smoothAzimuth = azimuth
            hasFirstAzimuth = true
        }}

        if (!isAmbient) {{
            compassView.postInvalidateOnAnimation()
        }} else {{
            val now = System.currentTimeMillis()
            if (now - lastAmbientDrawMs > 900L) {{
                lastAmbientDrawMs = now
                smoothAzimuth = rawAzimuth
                compassView.invalidate()
            }}
        }}
    }}

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {{
        sensorAccuracy = accuracy
    }}

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

    private fun showManualCoordsDialog() {{
        val dp = resources.displayMetrics.density
        val padH = (26 * dp).toInt()
        val padV = (18 * dp).toInt()

        val container = LinearLayout(this).apply {{
            orientation = LinearLayout.VERTICAL
            setPadding(padH, padV, padH, padV)
            setBackgroundColor(0xFF121212.toInt())
        }}

        val title = TextView(this).apply {{
            text = "Координаты цели"
            setTextColor(0xFFE89CFF.toInt())
            textSize = 15f
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, (10 * dp).toInt())
        }}
        container.addView(title)

        val prefill = lodestoneLocation ?: currentLocation
        val numInputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL or InputType.TYPE_NUMBER_FLAG_SIGNED

        val latInput = EditText(this).apply {{
            hint = "Широта (напр. 55.7558)"
            inputType = numInputType
            setTextColor(Color.WHITE)
            setHintTextColor(0xFF888888.toInt())
            textSize = 14f
            if (prefill != null) {{
                setText(String.format(Locale.US, "%.5f", prefill.latitude))
            }}
        }}
        container.addView(latInput)

        val lonInput = EditText(this).apply {{
            hint = "Долгота (напр. 37.6173)"
            inputType = numInputType
            setTextColor(Color.WHITE)
            setHintTextColor(0xFF888888.toInt())
            textSize = 14f
            if (prefill != null) {{
                setText(String.format(Locale.US, "%.5f", prefill.longitude))
            }}
        }}
        container.addView(lonInput)

        val btnRow = LinearLayout(this).apply {{
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, (12 * dp).toInt(), 0, (10 * dp).toInt())
        }}

        val btnReset = Button(this).apply {{
            text = "Сброс"
            textSize = 12f
        }}
        val btnSave = Button(this).apply {{
            text = "Ок"
            textSize = 12f
        }}
        btnRow.addView(btnReset)
        btnRow.addView(btnSave)
        container.addView(btnRow)

        val scroll = ScrollView(this).apply {{
            addView(container)
        }}

        val dialog = AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_NoActionBar)
            .setView(scroll)
            .create()

        btnReset.setOnClickListener {{
            isLodestoneActive = false
            pendingGpsLock = false
            lodestoneLocation = null
            saveLodestoneState(false, null)
            compassView.invalidate()
            dialog.dismiss()
        }}

        btnSave.setOnClickListener {{
            val latStr = latInput.text.toString().trim().replace(',', '.')
            val lonStr = lonInput.text.toString().trim().replace(',', '.')
            val lat = latStr.toDoubleOrNull()
            val lon = lonStr.toDoubleOrNull()
            if (lat == null || lon == null || lat < -90.0 || lat > 90.0 || lon < -180.0 || lon > 180.0) {{
                Toast.makeText(this, "Неверные координаты", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }}
            val target = Location("manual").apply {{
                latitude = lat
                longitude = lon
            }}
            lodestoneLocation = target
            isLodestoneActive = true
            pendingGpsLock = false
            saveLodestoneState(true, target)
            if (!hasLocationPermission()) {{
                requestPermissions(
                    arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION),
                    100
                )
            }} else {{
                startLocationIfPermitted()
            }}
            compassView.resetAnim()
            compassView.invalidate()
            dialog.dismiss()
        }}

        dialog.show()
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

        private val glintShader = LinearGradient(
            0f, 0f, 180f, 110f,
            intArrayOf(
                0x145500AA,
                0x458E24FF,
                0xAAEA80FC,
                0x458E24FF,
                0x145500AA
            ),
            floatArrayOf(0f, 0.30f, 0.50f, 0.70f, 1f),
            Shader.TileMode.REPEAT
        )
        private val glintMatrix = Matrix()
        private val xferAtop = PorterDuffXfermode(PorterDuff.Mode.SRC_ATOP)
        private val glintPaint = Paint().apply {{
            shader = glintShader
            xfermode = xferAtop
        }}

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
            color = 0xFF1A1A1A.toInt()
            textAlign = Paint.Align.CENTER
            isAntiAlias = false
        }}

        private val dstRect = Rect()
        private val dstRectF = RectF()
        private var startAnimMs = System.currentTimeMillis()

        fun resetAnim() {{
            startAnimMs = System.currentTimeMillis()
        }}

        private val gestureDetector = GestureDetector(context, object : GestureDetector.SimpleOnGestureListener() {{
            override fun onDown(e: MotionEvent): Boolean = true

            override fun onSingleTapConfirmed(e: MotionEvent): Boolean {{
                showOverlay = !showOverlay
                invalidate()
                return true
            }}

            override fun onDoubleTap(e: MotionEvent): Boolean {{
                showManualCoordsDialog()
                return true
            }}

            override fun onLongPress(e: MotionEvent) {{
                performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
                if (!isLodestoneActive) {{
                    isLodestoneActive = true
                    fallbackLodestoneBearing = smoothAzimuth
                    startAnimMs = System.currentTimeMillis()

                    if (!hasLocationPermission()) {{
                        pendingGpsLock = true
                        requestPermissions(
                            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION),
                            100
                        )
                    }} else {{
                        startLocationIfPermitted()
                        val loc = currentLocation
                        if (loc != null && (System.currentTimeMillis() - loc.time) < 120000L) {{
                            lodestoneLocation = Location(loc)
                            pendingGpsLock = false
                            saveLodestoneState(true, lodestoneLocation)
                        }} else {{
                            lodestoneLocation = null
                            pendingGpsLock = true
                        }}
                    }}
                }} else {{
                    isLodestoneActive = false
                    pendingGpsLock = false
                    lodestoneLocation = null
                    saveLodestoneState(false, null)
                }}
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

            if (!isAmbient) {{
                val diff = shortestAngleDiff(smoothAzimuth, rawAzimuth)
                if (abs(diff) > 0.25f) {{
                    smoothAzimuth = (smoothAzimuth + diff * 0.22f + 360f) % 360f
                    postInvalidateOnAnimation()
                }} else {{
                    smoothAzimuth = rawAzimuth
                }}
            }} else {{
                smoothAzimuth = rawAzimuth
            }}

            var targetBearing = 0f
            var distanceMeters: Float? = null
            if (isLodestoneActive) {{
                val targetLoc = lodestoneLocation
                val curLoc = currentLocation
                if (targetLoc != null && curLoc != null) {{
                    var bearing = curLoc.bearingTo(targetLoc)
                    if (bearing < 0f) bearing += 360f
                    targetBearing = bearing
                    distanceMeters = curLoc.distanceTo(targetLoc)
                }} else {{
                    targetBearing = fallbackLodestoneBearing
                }}
            }}

            val needleAngle = (targetBearing - smoothAzimuth + 720f) % 360f

            var bestIdx = 0
            var bestDiff = 999f
            for (i in 0 until 32) {{
                val d = abs(shortestAngleDiff(needleAngle, frameAngles[i]))
                if (d < bestDiff) {{
                    bestDiff = d
                    bestIdx = i
                }}
            }}

            val size = (minOf(width, height) * 0.88f).toInt()
            val left = (width - size) / 2
            val top = (height - size) / 2
            dstRect.set(left, top, left + size, top + size)
            dstRectF.set(dstRect)

            imgPaint.alpha = if (isAmbient) 110 else 255

            if (isLodestoneActive && !isAmbient) {{
                val saveId = canvas.saveLayer(dstRectF, null)
                canvas.drawBitmap(bitmaps[bestIdx], null, dstRect, imgPaint)
                val t = ((System.currentTimeMillis() - startAnimMs) % 2400L) / 2400f
                val shift = t * 210f
                glintMatrix.setTranslate(shift, shift * 0.6f)
                glintShader.setLocalMatrix(glintMatrix)
                canvas.drawRect(dstRectF, glintPaint)
                canvas.restoreToCount(saveId)
                postInvalidateOnAnimation()
            }} else {{
                canvas.drawBitmap(bitmaps[bestIdx], null, dstRect, imgPaint)
            }}

            if (showOverlay) {{
                textPaint.typeface = pixelFont
                shadowPaint.typeface = pixelFont
                val fontSize = width * 0.064f
                textPaint.textSize = fontSize
                shadowPaint.textSize = fontSize
                val textAlpha = if (isAmbient) 130 else 255

                val label = if (isLodestoneActive) {{
                    textPaint.color = 0xFFE89CFF.toInt()
                    val dist = distanceMeters
                    if (dist != null) {{
                        val distStr = if (dist >= 1000f) String.format(Locale.US, "%.1f км", dist / 1000f) else "${{dist.roundToInt()}} м"
                        "МАГНЕТИТ · $distStr"
                    }} else if (pendingGpsLock) {{
                        "МАГНЕТИТ · ПОИСК GPS"
                    }} else if (lodestoneLocation != null) {{
                        "МАГНЕТИТ · ПОИСК GPS"
                    }} else {{
                        "МАГНЕТИТ"
                    }}
                }} else {{
                    if (sensorAccuracy <= SensorManager.SENSOR_STATUS_ACCURACY_LOW && !isAmbient) {{
                        textPaint.color = 0xFFFFD54F.toInt()
                        "ПОКРУТИ (8)"
                    }} else {{
                        textPaint.color = Color.WHITE
                        val degInt = smoothAzimuth.roundToInt() % 360
                        "${{cardinalRu(smoothAzimuth)}} ${{degInt}}°"
                    }}
                }}

                textPaint.alpha = textAlpha
                shadowPaint.alpha = textAlpha

                val ty = height * 0.88f
                if (!isAmbient) {{
                    canvas.drawText(label, width / 2f + 2f, ty + 2f, shadowPaint)
                }}
                canvas.drawText(label, width / 2f, ty, textPaint)
            }}
        }}
    }}
}}
"""

with open("app/src/main/java/com/minecraft/compassapp/MainActivity.kt", "w", encoding="utf-8") as f:
    f.write(kotlin_code)
