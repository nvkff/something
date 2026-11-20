import os
import zlib
import struct
import math
import shutil

# ─── НАСТРОЙКИ ───
PKG = "com.opw.fourthirty"
APP_LABEL = "4:30"
WORKER_URL = ""  
AUTH_PASS = ""  

# ─── 1. Gradle-обвязка ───
with open("build.gradle.kts", "w", encoding="utf-8") as f:
    f.write('''plugins {
    id("com.android.application") version "8.4.1" apply false
    id("org.jetbrains.kotlin.android") version "1.9.23" apply false
}
''')

with open("settings.gradle.kts", "w", encoding="utf-8") as f:
    f.write('''pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "FourThirty"
include(":app")
''')

with open("gradle.properties", "w", encoding="utf-8") as f:
    f.write('''org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.nonTransitiveRClass=true
''')

os.makedirs("app", exist_ok=True)
with open("app/build.gradle.kts", "w", encoding="utf-8") as f:
    f.write(f'''plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}}
android {{
    namespace = "{PKG}"
    compileSdk = 34
    defaultConfig {{
        applicationId = "{PKG}"
        minSdk = 30
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }}
    signingConfigs {{
        create("release") {{
            storeFile = rootProject.file("release.keystore")
            storePassword = "123456"
            keyAlias = "watchkey"
            keyPassword = "123456"
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = false
        }}
    }}
    buildTypes {{
        release {{
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }}
    }}
    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}
    kotlinOptions {{ jvmTarget = "17" }}
}}
dependencies {{
    implementation("androidx.wear:wear:1.3.0")
    implementation("androidx.activity:activity-ktx:1.9.0")
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.health.connect:connect-client:1.1.0-alpha07")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
}}
''')

# ─── 2. Папки и Manifest ───
for p in ("app/src/main/java", "app/src/main/res"):
    if os.path.exists(p): shutil.rmtree(p)
os.makedirs(f"app/src/main/java/{PKG.replace('.', '/')}", exist_ok=True)
os.makedirs("app/src/main/res/drawable", exist_ok=True)
os.makedirs("app/src/main/res/values", exist_ok=True)

with open("app/src/main/res/values/strings.xml", "w", encoding="utf-8") as f:
    f.write(f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{APP_LABEL}</string>
</resources>
''')

with open("app/src/main/AndroidManifest.xml", "w", encoding="utf-8") as f:
    f.write(f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-feature android:name="android.hardware.type.watch" />
    <uses-permission android:name="android.permission.BODY_SENSORS" />
    <uses-permission android:name="android.permission.ACTIVITY_RECOGNITION" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_HEALTH" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.health.READ_SLEEP" />
    
    <application
        android:allowBackup="false"
        android:icon="@drawable/ic_launcher"
        android:label="@string/app_name">
        <uses-library android:name="com.google.android.wearable" android:required="false" />
        <meta-data android:name="com.google.android.wearable.standalone" android:value="true" />
        
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
            <intent-filter>
                <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
            </intent-filter>
        </activity>
        
        <service
            android:name=".TrackingService"
            android:exported="false"
            android:foregroundServiceType="health" />
    </application>
</manifest>
''')

# ─── 3. Генерация иконки ───
def save_png(filename, w, h, pixel_func):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            r, g, b, a = pixel_func(x, y, w, h)
            raw.extend((r, g, b, a))
    def chunk(t, d):
        return struct.pack("!I", len(d)) + t + d + struct.pack("!I", zlib.crc32(t + d) & 0xffffffff)
    with open(filename, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))

def icon_pixel(x, y, w, h):
    cx, cy = 96, 96
    d = math.hypot(x - cx, y - cy)
    if d > 90: return (0, 0, 0, 0)
    if d > 82: return (232, 156, 208, 255)
    if d > 80: return (38, 38, 38, 255)
    if 88 <= x <= 104 and 88 <= y <= 104: return (255, 255, 255, 255)
    return (38, 38, 38, 255)

save_png("app/src/main/res/drawable/ic_launcher.png", 192, 192, icon_pixel)

# ─── 4. TrackingService.kt ───
service_code = f'''package {PKG}

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import kotlin.math.abs
import kotlin.math.roundToInt
import kotlin.math.sqrt

class TrackingService : Service(), SensorEventListener {{
    private lateinit var sm: SensorManager
    private var wakeLock: PowerManager.WakeLock? = null
    
    private var isRecording = false
    private var startTs = 0L
    private var lastHrSavedMs = 0L
    private var lastNotificationMs = 0L
    private var hrSum = 0L; var hrN = 0; var hrMin = Int.MAX_VALUE; var hrMax = 0
    private val hrSamples = StringBuilder()
    private var motionSumSq = 0.0; var motionN = 0; var motionMax = 0.0
    private var lightSum = 0.0; var lightN = 0
    private var stepStart = -1; var lastStep = -1
    
    private val sensorAggs = linkedMapOf<String, SensorAgg>()
    private val registeredSensors = mutableListOf<Sensor>()

    companion object {{
        const val CHANNEL_ID = "430_tracking_channel"
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
        var currentStartTs = 0L
    }}

    override fun onCreate() {{
        super.onCreate()
        sm = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        createNotificationChannel()
    }}

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {{
        when (intent?.action) {{
            ACTION_START -> startTracking()
            ACTION_STOP -> stopTracking()
        }}
        return START_STICKY
    }}

    private fun startTracking() {{
        if (isRecording) return
        
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "FourThirty::BackgroundTracking")
        wakeLock?.acquire(2L * 60L * 60L * 1000L) 
        
        isRecording = true
        startTs = System.currentTimeMillis()
        currentStartTs = startTs
        lastNotificationMs = startTs
        lastHrSavedMs = 0L
        hrSum = 0; hrN = 0; hrMin = Int.MAX_VALUE; hrMax = 0
        hrSamples.setLength(0)
        motionSumSq = 0.0; motionN = 0; motionMax = 0.0
        lightSum = 0.0; lightN = 0
        stepStart = lastStep
        
        sensorAggs.clear()
        registeredSensors.clear()
        
        // Подключаем вообще все доступные датчики (Skin Temp, SpO2, и т.д.)
        val seen = mutableSetOf<Int>()
        for (s in sm.getSensorList(Sensor.TYPE_ALL)) {{
            if (s.type in seen) continue
            // Фильтруем только датчики-триггеры, которые не пишут непрерывно
            if (s.type == Sensor.TYPE_SIGNIFICANT_MOTION || s.type == Sensor.TYPE_STEP_DETECTOR) continue
            
            val delay = if (s.type == Sensor.TYPE_ACCELEROMETER || s.type == Sensor.TYPE_GYROSCOPE) 
                SensorManager.SENSOR_DELAY_GAME else SensorManager.SENSOR_DELAY_NORMAL
            
            if (sm.registerListener(this, s, delay)) {{
                sensorAggs[s.name] = SensorAgg(s.name)
                registeredSensors.add(s)
                seen.add(s.type)
            }}
        }}
        
        startForeground(1, buildNotification(0))
    }}

    private fun getSleepData(): String {{
        var sleepContext = ""
        try {{
            if (androidx.health.connect.client.HealthConnectClient.getSdkStatus(this) == androidx.health.connect.client.HealthConnectClient.SDK_AVAILABLE) {{
                val hc = androidx.health.connect.client.HealthConnectClient.getOrCreate(this)
                kotlinx.coroutines.runBlocking {{
                    val now = java.time.Instant.now()
                    val req = androidx.health.connect.client.request.ReadRecordsRequest(
                        recordType = androidx.health.connect.client.records.SleepSessionRecord::class,
                        timeRangeFilter = androidx.health.connect.client.time.TimeRangeFilter.between(now.minus(java.time.Duration.ofDays(2)), now)
                    )
                    val res = hc.readRecords(req)
                    val rec = res.records.maxByOrNull {{ it.endTime }}
                    if (rec != null) {{
                        val h = (rec.endTime.toEpochMilli() - rec.startTime.toEpochMilli()) / 3600000.0
                        sleepContext = String.format(java.util.Locale.US, "%.1fh", h)
                    }}
                }}
            }}
        }} catch(e: Exception) {{}}
        return sleepContext
    }}

    private fun stopTracking() {{
        if (!isRecording) return
        isRecording = false
        currentStartTs = 0L
        sm.unregisterListener(this)
        
        try {{ wakeLock?.takeIf {{ it.isHeld }}?.release() }} catch (_: Exception) {{}}
        wakeLock = null
        
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
        
        val endTs = System.currentTimeMillis()
        val durMs = endTs - startTs
        if (durMs < 3000L) return
        
        val sleepContext = getSleepData()
        
        val stepDelta = if (stepStart >= 0 && lastStep >= 0) (lastStep - stepStart).coerceAtLeast(0) else 0
        val truncated = durMs >= 2L * 60L * 60L * 1000L
        
        val extrasObj = JSONObject()
        for ((_, agg) in sensorAggs) {{
            if (agg.count > 0) extrasObj.put(agg.name, agg.toJson())
        }}
        
        val session = JSONObject().apply {{
            put("startTs", startTs)
            put("endTs", if (truncated) startTs + 2L * 60L * 60L * 1000L else endTs)
            put("hrMin", if (hrMin == Int.MAX_VALUE) 0 else hrMin)
            put("hrMax", hrMax)
            put("hrAvg", if (hrN > 0) (hrSum / hrN).toInt() else 0)
            put("hrSamples", hrSamples.toString().trimEnd(','))
            put("motionAvg", if (motionN > 0) sqrt(motionSumSq / motionN) else 0.0)
            put("motionMax", motionMax)
            put("lightAvg", if (lightN > 0) lightSum / lightN else 0.0)
            put("stepDelta", stepDelta)
            put("truncated", truncated)
            put("note", "")
            put("sleepContext", sleepContext)
            put("extraSensors", extrasObj.toString())
        }}
        
        saveSession(session)
    }}

    private fun saveSession(session: JSONObject) {{
        val prefs = getSharedPreferences("fourthirty", Context.MODE_PRIVATE)
        val raw = prefs.getString("sessions", "[]") ?: "[]"
        val arr = JSONArray(raw)
        arr.put(session)
        val jsonStr = arr.toString()
        prefs.edit().putString("sessions", jsonStr).apply()
        
        try {{
            val dir = getExternalFilesDir(null)
            if (dir != null) File(dir, "430.json").writeText(jsonStr)
        }} catch (_: Exception) {{}}
        
        uploadToWorker(jsonStr)
    }}

    private fun uploadToWorker(json: String) {{
        val url = "{WORKER_URL}"
        val pass = "{AUTH_PASS}"
        if (url.isEmpty() || url == "WORKER_URL_PLACEHOLDER") return
        
        Thread {{
            try {{
                val conn = URL("$url/upload").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.doOutput = true
                conn.connectTimeout = 7000
                conn.readTimeout = 7000
                conn.setRequestProperty("Content-Type", "application/json")
                if (pass.isNotEmpty()) {{
                    val creds = Base64.encodeToString(pass.toByteArray(), Base64.NO_WRAP)
                    conn.setRequestProperty("X-Auth", creds)
                }}
                conn.outputStream.use {{ it.write(json.toByteArray()) }}
                conn.responseCode
                conn.disconnect()
            }} catch (_: Exception) {{}}
        }}.start()
    }}

    override fun onSensorChanged(event: SensorEvent) {{
        if (!isRecording) return
        val now = System.currentTimeMillis()
        sensorAggs[event.sensor.name]?.add(event.values)
        
        when (event.sensor.type) {{
            Sensor.TYPE_HEART_RATE -> {{
                val bpm = event.values[0].roundToInt()
                if (bpm in 30..230) {{
                    hrSum += bpm; hrN++
                    if (bpm < hrMin) hrMin = bpm
                    if (bpm > hrMax) hrMax = bpm
                    if (now - lastHrSavedMs >= 5000L) {{
                        hrSamples.append(((now - startTs) / 1000L).toInt()).append(':').append(bpm).append(',')
                        lastHrSavedMs = now
                    }}
                }}
            }}
            Sensor.TYPE_ACCELEROMETER -> {{
                val mag = sqrt(event.values.fold(0.0) {{ acc, v -> acc + v.toDouble() * v }})
                val delta = abs(mag - 9.80665)
                motionSumSq += delta * delta; motionN++
                if (delta > motionMax) motionMax = delta
            }}
            Sensor.TYPE_LIGHT -> {{ lightSum += event.values[0]; lightN++ }}
            Sensor.TYPE_STEP_COUNTER -> {{ lastStep = event.values[0].toInt() }}
        }}
        
        if (now - lastNotificationMs >= 1000L) {{
            lastNotificationMs = now
            val elapsed = ((now - startTs) / 1000L).toInt()
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.notify(1, buildNotification(elapsed))
            
            if (elapsed * 1000L >= 2L * 60L * 60L * 1000L) stopTracking()
        }}
    }}

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {{}}

    private fun buildNotification(elapsedSec: Int): Notification {{
        val h = elapsedSec / 3600
        val m = (elapsedSec % 3600) / 60
        val s = elapsedSec % 60
        val timeStr = String.format(java.util.Locale.US, "%02d:%02d:%02d", h, m, s)
        
        val stopIntent = Intent(this, TrackingService::class.java).apply {{ action = ACTION_STOP }}
        val pendingStop = PendingIntent.getService(this, 0, stopIntent, 
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("4:30")
            .setContentText(timeStr)
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Стоп", pendingStop)
            .setOngoing(true)
            .build()
    }}

    private fun createNotificationChannel() {{
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
            val channel = NotificationChannel(CHANNEL_ID, "4:30 Tracking", NotificationManager.IMPORTANCE_LOW).apply {{
                description = "Фоновая запись"
                setShowBadge(false)
            }}
            (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).createNotificationChannel(channel)
        }}
    }}

    override fun onBind(intent: Intent?): IBinder? = null

    class SensorAgg(val name: String) {{
        var dim = 0
        val sum = mutableListOf<Double>()
        val min = mutableListOf<Double>()
        val max = mutableListOf<Double>()
        var count = 0L
        fun add(values: FloatArray) {{
            if (values.isEmpty()) return
            if (dim == 0) {{
                dim = values.size
                for (i in 0 until dim) {{ sum.add(0.0); min.add(Double.MAX_VALUE); max.add(-Double.MAX_VALUE) }}
            }}
            for (i in 0 until minOf(dim, values.size)) {{
                val v = values[i].toDouble()
                sum[i] += v
                if (v < min[i]) min[i] = v
                if (v > max[i]) max[i] = v
            }}
            count++
        }}
        fun toJson(): JSONObject = JSONObject().apply {{
            put("name", name); put("count", count)
            if (count > 0) {{
                put("avg", JSONArray().also {{ a -> for (i in 0 until dim) a.put(sum[i] / count) }})
                put("min", JSONArray().also {{ a -> for (i in 0 until dim) a.put(min[i]) }})
                put("max", JSONArray().also {{ a -> for (i in 0 until dim) a.put(max[i]) }})
            }}
        }}
    }}
}}
'''

with open(f"app/src/main/java/{PKG.replace('.', '/')}/TrackingService.kt", "w", encoding="utf-8") as f:
    f.write(service_code)

# ─── 5. MainActivity.kt ───
main_activity_code = f'''package {PKG}

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.view.GestureDetector
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.wear.ambient.AmbientLifecycleObserver
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.hypot

class MainActivity : ComponentActivity() {{
    private lateinit var mainView: MainView
    private var sessions = mutableListOf<JSONObject>()
    
    private lateinit var ambientObserver: AmbientLifecycleObserver
    private var isAmbient = false

    private val ambientCallback = object : AmbientLifecycleObserver.AmbientLifecycleCallback {{
        override fun onEnterAmbient(ambientDetails: AmbientLifecycleObserver.AmbientDetails) {{
            isAmbient = true
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            if (::mainView.isInitialized) mainView.invalidate()
        }}
        override fun onUpdateAmbient() {{
            if (::mainView.isInitialized) mainView.invalidate()
        }}
        override fun onExitAmbient() {{
            isAmbient = false
            if (::mainView.isInitialized) mainView.invalidate()
        }}
    }}

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        ambientObserver = AmbientLifecycleObserver(this, ContextCompat.getMainExecutor(this), ambientCallback)
        lifecycle.addObserver(ambientObserver)
        requestPermissionsAndInit()
    }}

    private fun requestPermissionsAndInit() {{
        val perms = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {{
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
                perms.add(android.Manifest.permission.POST_NOTIFICATIONS)
        }}
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.BODY_SENSORS) != PackageManager.PERMISSION_GRANTED)
            perms.add(android.Manifest.permission.BODY_SENSORS)
        
        if (perms.isNotEmpty()) {{
            ActivityCompat.requestPermissions(this, perms.toTypedArray(), 100)
        }} else {{
            setupUI()
        }}
    }}
    
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {{
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        setupUI()
    }}

    private fun setupUI() {{
        if (!::mainView.isInitialized) {{
            loadSessions()
            mainView = MainView(this)
            setContentView(mainView)
        }}
    }}

    override fun onResume() {{
        super.onResume()
        if (::mainView.isInitialized) {{
            loadSessions()
            mainView.invalidate()
        }}
    }}

    private fun loadSessions() {{
        sessions.clear()
        val raw = getSharedPreferences("fourthirty", Context.MODE_PRIVATE).getString("sessions", "[]") ?: "[]"
        try {{
            val arr = JSONArray(raw)
            for (i in 0 until arr.length()) sessions.add(arr.getJSONObject(i))
        }} catch (_: Exception) {{}}
        sessions.sortBy {{ it.getLong("startTs") }}
    }}

    private fun toggleTracking() {{
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.BODY_SENSORS) != PackageManager.PERMISSION_GRANTED) {{
            requestPermissionsAndInit()
            return
        }}
        
        val intent = Intent(this, TrackingService::class.java)
        if (isServiceRunning()) {{
            intent.action = TrackingService.ACTION_STOP
            startService(intent)
        }} else {{
            intent.action = TrackingService.ACTION_START
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent)
            else startService(intent)
        }}
        mainView.postDelayed({{ mainView.invalidate() }}, 400)
    }}

    private fun isServiceRunning(): Boolean {{
        val manager = getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
        for (service in manager.getRunningServices(Int.MAX_VALUE)) {{
            if (TrackingService::class.java.name == service.service.className) return true
        }}
        return false
    }}

    inner class MainView(ctx: Context) : View(ctx) {{
        private val tp = Paint().apply {{ color = Color.WHITE; textAlign = Paint.Align.CENTER; isAntiAlias = false }}
        private val sp = Paint().apply {{ color = 0xFF1A1A1A.toInt(); textAlign = Paint.Align.CENTER; isAntiAlias = false }}
        private val arrow = Paint().apply {{ color = 0xFF666666.toInt(); isAntiAlias = true; style = Paint.Style.FILL }}
        private var screen = 0
        private val screens = arrayOf("Главная", "Цифры", "История", "Ещё")
        private var toastTxt = ""; private var toastUntil = 0L

        private val gestureDetector = GestureDetector(context, object : GestureDetector.SimpleOnGestureListener() {{
            override fun onDown(e: MotionEvent): Boolean = true

            override fun onSingleTapConfirmed(e: MotionEvent): Boolean {{
                handleTap(e.x, e.y)
                return true
            }}

            override fun onLongPress(e: MotionEvent) {{
                performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
                if (screen == 3) clearAll()
            }}
        }})

        override fun onTouchEvent(event: MotionEvent): Boolean {{
            gestureDetector.onTouchEvent(event)
            return true
        }}

        fun showToast(t: String) {{
            toastTxt = t; toastUntil = System.currentTimeMillis() + 1500
            postDelayed({{ invalidate() }}, 1600)
        }}

        private fun handleTap(x: Float, y: Float) {{
            val w = width.toFloat()
            if (x < w * 0.30f) {{
                if (screen > 0) {{ screen--; invalidate(); performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK) }}
            }} else if (x > w * 0.70f) {{
                if (screen < screens.size - 1) {{ screen++; invalidate(); performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK) }}
            }} else {{
                if (screen == 0) {{
                    val cx = w / 2f
                    val cy = height / 2f - 20f
                    val r = w * 0.27f
                    if (hypot(x - cx, y - cy) <= r * 1.3f) {{
                        performHapticFeedback(HapticFeedbackConstants.CONFIRM)
                        toggleTracking()
                    }}
                }} else if (screen == 3) {{
                    if (y > height / 2f + 30f && y < height / 2f + 80f) {{
                        try {{
                            val intent = Intent("androidx.health.ACTION_REQUEST_PERMISSIONS")
                            intent.putExtra("androidx.health.health_permissions", arrayOf("android.permission.health.READ_SLEEP"))
                            context.startActivity(intent)
                        }} catch (e: Exception) {{ showToast("Health Connect недоступен") }}
                    }} else {{
                        cancelLast()
                    }}
                }}
            }}
        }}

        private fun drawTxt(c: Canvas, s: String, x: Float, y: Float, sz: Float, col: Int = Color.WHITE) {{
            tp.typeface = Typeface.DEFAULT; sp.typeface = Typeface.DEFAULT
            tp.textSize = sz; sp.textSize = sz; tp.color = col
            val alphaVal = if (isAmbient) 130 else 255
            tp.alpha = alphaVal; sp.alpha = alphaVal
            if (!isAmbient) c.drawText(s, x + 2f, y + 2f, sp)
            c.drawText(s, x, y, tp)
        }}

        private fun drawNav(c: Canvas) {{
            val cx = width / 2f; val cy = 52f
            val x0 = cx - (screens.size - 1) * 16f / 2f
            val dp = Paint().apply {{ isAntiAlias = true }}
            for (i in screens.indices) {{
                dp.color = if (i == screen) 0xFFA89CD0.toInt() else 0xFF444444.toInt()
                c.drawCircle(x0 + i * 16f, cy, 4f, dp)
            }}
            if (screen > 0) {{
                val p = Path(); p.moveTo(58f, cy - 9f); p.lineTo(44f, cy); p.lineTo(58f, cy + 9f); p.close()
                c.drawPath(p, arrow)
            }}
            if (screen < screens.size - 1) {{
                val p = Path(); p.moveTo(width - 58f, cy - 9f); p.lineTo(width - 44f, cy); p.lineTo(width - 58f, cy + 9f); p.close()
                c.drawPath(p, arrow)
            }}
        }}

        private fun drawMain(c: Canvas) {{
            val cx = width / 2f; val cy = height / 2f - 20f; val r = width * 0.27f
            val running = isServiceRunning()
            
            val bp = Paint().apply {{ color = if (running) 0xFF3A2A4E.toInt() else 0xFF2A2A2A.toInt(); isAntiAlias = true }}
            val rp = Paint().apply {{ color = if (running) 0xFFFF5577.toInt() else 0xFFA89CD0.toInt(); style = Paint.Style.STROKE; strokeWidth = 5f; isAntiAlias = true }}
            
            if (isAmbient) {{
                bp.color = Color.BLACK
                rp.color = 0xFF666666.toInt()
            }}
            
            c.drawCircle(cx, cy, r, bp); c.drawCircle(cx, cy, r, rp)
            
            if (running) {{
                val startTs = TrackingService.currentStartTs
                if (startTs > 0L) {{
                    val elapsed = (System.currentTimeMillis() - startTs) / 1000L
                    val m = elapsed / 60
                    val s = elapsed % 60
                    val timeStr = String.format(Locale.US, "%02d:%02d", m, s)
                    drawTxt(c, timeStr, cx, cy + 8f, 38f, Color.WHITE)
                    drawTxt(c, "СТОП", cx, cy + r + 45f, 20f, 0xFFFF5577.toInt())
                }} else {{
                    drawTxt(c, "СТОП", cx, cy + 12f, 32f, 0xFFFF5577.toInt())
                }}
            }} else {{
                val pp = Paint().apply {{ color = Color.WHITE; strokeWidth = 9f; strokeCap = Paint.Cap.ROUND; isAntiAlias = true }}
                if (isAmbient) pp.color = 0xFF888888.toInt()
                val p = r * 0.35f
                val path = Path()
                path.moveTo(cx - p*0.6f, cy - p)
                path.lineTo(cx - p*0.6f, cy + p)
                path.lineTo(cx + p, cy)
                path.close()
                c.drawPath(path, pp)
                drawTxt(c, "Нажми для старта", cx, cy + r + 50f, 20f, 0xFF888888.toInt())
            }}
            
            if (sessions.size >= 1 && !isAmbient) {{
                val fmt = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault())
                val s1 = sessions[sessions.size - 1]
                val dur1 = fmtDur(s1.optInt("durationSec", 0).toLong())
                drawTxt(c, "${{fmt.format(Date(s1.getLong("startTs")))}} · $dur1", cx, cy + r + 90f, 18f, 0xFF666666.toInt())
            }}
            
            if (running && !isAmbient) postInvalidateDelayed(1000)
        }}

        private fun drawStats(c: Canvas) {{
            if (sessions.isEmpty()) {{ drawTxt(c, "Нет данных", width / 2f, 220f, 30f, 0xFF888888.toInt()); return }}
            val total = sessions.size
            val totalSec = sessions.sumOf {{ it.optInt("durationSec", 0).toLong() }}
            val avgDur = totalSec / total
            
            val lines = listOf(
                "Всего: $total",
                "Сумма: ${{fmtDur(totalSec)}}",
                "Средняя: ${{fmtDur(avgDur)}}",
                "Пульс ср: ${{sessions.filter{{it.optInt("hrAvg",0)>0}}.map{{it.optInt("hrAvg")}}.average().toInt()}} bpm"
            )
            var y = 120f
            for ((i, s) in lines.withIndex()) {{
                drawTxt(c, s, width / 2f, y, 26f, if (i == 0) 0xFFA89CD0.toInt() else Color.WHITE)
                y += 40f
            }}
        }}

        private fun drawHistory(c: Canvas) {{
            drawTxt(c, "Последние", width / 2f, 100f, 26f, 0xFFA89CD0.toInt())
            if (sessions.isEmpty()) {{ drawTxt(c, "Пусто", width / 2f, 220f, 26f, 0xFF888888.toInt()); return }}
            val fmt = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault())
            var y = 150f
            for (s in sessions.takeLast(6).reversed()) {{
                val dur = fmtDur(s.optInt("durationSec", 0).toLong())
                val hr = if (s.optInt("hrAvg", 0) > 0) "${{s.optInt("hrAvg")}} bpm" else "—"
                drawTxt(c, "${{fmt.format(Date(s.getLong("startTs")))}} · $dur · $hr", width / 2f, y, 20f)
                y += 34f
            }}
        }}

        private fun drawSettings(c: Canvas) {{
            drawTxt(c, "Настройки", width / 2f, 100f, 26f, 0xFFA89CD0.toInt())
            drawTxt(c, "Записей: ${{sessions.size}}", width / 2f, 160f, 22f)
            drawTxt(c, "Тап по центру = отменить", width / 2f, 210f, 20f, 0xFFFF8888.toInt())
            drawTxt(c, "Долгий тап = очистить", width / 2f, 240f, 20f, 0xFFFF8888.toInt())
            
            drawTxt(c, "Доступ ко сну (Health Connect)", width / 2f, 280f, 18f, 0xFF888888.toInt())
            
            val syncStatus = if ("{WORKER_URL}".isNotEmpty() && "{WORKER_URL}" != "WORKER_URL_PLACEHOLDER") "Синк: ВКЛ" else "Синк: ЛОК"
            drawTxt(c, syncStatus, width / 2f, 320f, 18f, 0xFF888888.toInt())
        }}

        override fun onDraw(c: Canvas) {{
            super.onDraw(c)
            c.drawColor(Color.BLACK)
            when (screen) {{
                0 -> drawMain(c)
                1 -> drawStats(c)
                2 -> drawHistory(c)
                3 -> drawSettings(c)
            }}
            if (!isAmbient) {{
                drawNav(c)
                drawTxt(c, screens[screen], width / 2f, height - 36f, 20f, 0xFF888888.toInt())
            }}
            
            if (System.currentTimeMillis() < toastUntil) {{
                drawTxt(c, toastTxt, width / 2f, height - 90f, 22f, 0xFFA89CD0.toInt())
            }}
        }}
        
        private fun cancelLast() {{
            if (sessions.isNotEmpty()) {{
                performHapticFeedback(HapticFeedbackConstants.REJECT)
                sessions.removeAt(sessions.size - 1)
                val arr = JSONArray()
                for (s in sessions) arr.put(s)
                getSharedPreferences("fourthirty", Context.MODE_PRIVATE).edit().putString("sessions", arr.toString()).apply()
                showToast("Последняя удалена")
                invalidate()
            }}
        }}

        private fun clearAll() {{
            sessions.clear()
            getSharedPreferences("fourthirty", Context.MODE_PRIVATE).edit().putString("sessions", "[]").apply()
            showToast("История очищена")
            invalidate()
        }}
        
        private fun fmtDur(sec: Long): String {{
            if (sec < 60) return "${{sec}}с"
            val m = sec / 60
            if (m < 60) return "${{m}}м"
            val h = m / 60; val rm = m % 60
            return if (rm == 0L) "${{h}}ч" else "${{h}}ч${{rm}}м"
        }}
    }}
}}
'''

with open(f"app/src/main/java/{PKG.replace('.', '/')}/MainActivity.kt", "w", encoding="utf-8") as f:
    f.write(main_activity_code)

print("Готово. Запускай сборку.")
