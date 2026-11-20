import os
import zlib
import struct
import math
import shutil

# ─── НАСТРОЙКИ ───
PKG = "com.opw.fourthirty"
APP_LABEL = "4:30"
# Вставь сюда URL своего воркера и пароль, когда задеплоишь его. 
# Пока можно оставить пустым, синхронизация будет работать локально.
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
}}
''')

# ─── 2. Папки ───
for p in ("app/src/main/java", "app/src/main/res"):
    if os.path.exists(p):
        shutil.rmtree(p)
os.makedirs(f"app/src/main/java/{PKG.replace('.', '/')}", exist_ok=True)
os.makedirs("app/src/main/res/drawable-nodpi", exist_ok=True)
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
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
    <uses-permission android:name="android.permission.INTERNET" />
    
    <application
        android:allowBackup="false"
        android:icon="@drawable-nodpi/ic_launcher"
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
        </activity>
        
        <service
            android:name=".TrackingService"
            android:exported="false"
            android:foregroundServiceType="dataSync" />
    </application>
</manifest>
''')

# ─── 3. Генерация иконки (4:30) ───
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
    # Рисуем "4:30" пиксельным шрифтом 5x7 на круглом фоне 192x192
    cx, cy = 96, 96
    d = math.hypot(x - cx, y - cy)
    if d > 90: return (0, 0, 0, 0) # Прозрачный фон за пределами круга
    
    # Простая матрица для "4:30" (упрощённая, но читаемая)
    # 4
    p4 = [
        "10001", "10001", "10001", "11111", "00001", "00001", "00001"
    ]
    # :
    p_col = [
        "00", "00", "01", "00", "01", "00", "00"
    ]
    # 3
    p3 = [
        "1110", "0001", "0001", "0110", "0001", "0001", "1110"
    ]
    # 0
    p0 = [
        "0110", "1001", "1001", "1001", "1001", "1001", "0110"
    ]
    
    # Масштабируем и центрируем
    scale = 6
    total_w = (5 + 2 + 4 + 4) * scale
    start_x = cx - total_w // 2
    start_y = cy - (7 * scale) // 2
    
    def get_bit(char, r, c):
        if char == '4' and r < 7 and c < 5: return p4[r][c] == '1'
        if char == ':' and r < 7 and c < 2: return p_col[r][c] == '1'
        if char == '3' and r < 7 and c < 4: return p3[r][c] == '1'
        if char == '0' and r < 7 and c < 4: return p0[r][c] == '1'
        return False

    chars = ['4', ':', '3', '0']
    c_offsets = [0, 5, 7, 11]
    
    for i, char in enumerate(chars):
        for r in range(7):
            for c in range(len(p4[0]) if char=='4' else (2 if char==':' else 4)):
                if get_bit(char, r, c):
                    px = start_x + (c_offsets[i] + c) * scale
                    py = start_y + r * scale
                    if px <= x < px + scale and py <= y < py + scale:
                        return (168, 156, 208, 255) # Фиолетовый акцент
                        
    return (38, 38, 38, 255) # Тёмный фон внутри круга

save_png("app/src/main/res/drawable-nodpi/ic_launcher.png", 192, 192, icon_pixel)

# ─── 4. TrackingService.kt (Фоновая запись) ───
service_code = f'''package {PKG}

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.IBinder
import android.util.Base64
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.math.abs
import kotlin.math.roundToInt
import kotlin.math.sqrt

class TrackingService : Service(), SensorEventListener {{
    private lateinit var sm: SensorManager
    private var isRecording = false
    private var startTs = 0L
    private var lastHrSavedMs = 0L
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
        isRecording = true
        startTs = System.currentTimeMillis()
        lastHrSavedMs = 0L
        hrSum = 0; hrN = 0; hrMin = Int.MAX_VALUE; hrMax = 0
        hrSamples.setLength(0)
        motionSumSq = 0.0; motionN = 0; motionMax = 0.0
        lightSum = 0.0; lightN = 0
        stepStart = lastStep
        
        sensorAggs.clear()
        registeredSensors.clear()
        val wanted = setOf(
            Sensor.TYPE_HEART_RATE, Sensor.TYPE_ACCELEROMETER, 
            Sensor.TYPE_LIGHT, Sensor.TYPE_STEP_COUNTER,
            Sensor.TYPE_GYROSCOPE, Sensor.TYPE_GRAVITY
        )
        val seen = mutableSetOf<Int>()
        for (s in sm.getSensorList(Sensor.TYPE_ALL)) {{
            if (s.type !in wanted || s.type in seen) continue
            val delay = if (s.type == Sensor.TYPE_ACCELEROMETER || s.type == Sensor.TYPE_GYROSCOPE) 
                SensorManager.SENSOR_DELAY_GAME else SensorManager.SENSOR_DELAY_NORMAL
            if (sm.registerListener(this, s, delay)) {{
                sensorAggs[s.name] = SensorAgg(s.name)
                registeredSensors.add(s)
                seen.add(s.type)
            }}
        }}
        
        val notification = buildNotification(0)
        startForeground(1, notification)
    }}

    private fun stopTracking() {{
        if (!isRecording) return
        isRecording = false
        sm.unregisterListener(this)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
        
        val endTs = System.currentTimeMillis()
        val durMs = endTs - startTs
        if (durMs < 3000L) return // Игнорируем слишком короткие
        
        val stepDelta = if (stepStart >= 0 && lastStep >= 0) (lastStep - stepStart).coerceAtLeast(0) else 0
        val truncated = durMs >= 2L * 60L * 60L * 1000L // 2 часа
        
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
            put("extraSensors", extrasObj.toString())
        }}
        
        saveSession(session)
    }}

    private fun saveSession(session: JSONObject) {{
        val prefs = getSharedPreferences("fourthirty", Context.MODE_PRIVATE)
        val raw = prefs.getString("sessions", "[]") ?: "[]"
        val arr = JSONArray(raw)
        arr.put(session)
        prefs.edit().putString("sessions", arr.toString()).apply()
        
        // Экспорт в файл
        try {{
            val dir = getExternalFilesDir(null)
            if (dir != null) java.io.File(dir, "430.json").writeText(arr.toString())
        }} catch (_: Exception) {{}}
        
        // Отправка на Worker
        uploadToWorker(arr.toString())
    }}

    private fun uploadToWorker(json: String) {{
        if ("{WORKER_URL}".isEmpty()) return
        Thread {{
            try {{
                val conn = URL("{WORKER_URL}/upload").openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.doOutput = true
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                conn.setRequestProperty("Content-Type", "application/json")
                if ("{AUTH_PASS}".isNotEmpty()) {{
                    val creds = Base64.encodeToString("{AUTH_PASS}".toByteArray(), Base64.NO_WRAP)
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
                    if (now - lastHrSavedMs >= 5000L) {{ // Каждые 5 сек
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
        
        // Обновляем уведомление с таймером
        val elapsed = ((now - startTs) / 1000L).toInt()
        val notification = buildNotification(elapsed)
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(1, notification)
        
        // Авто-стоп через 2 часа
        if (elapsed * 1000L >= 2L * 60L * 60L * 1000L) {{
            stopTracking()
        }}
    }}

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {{}}

    private fun buildNotification(elapsedSec: Int): Notification {{
        val h = elapsedSec / 3600
        val m = (elapsedSec % 3600) / 60
        val s = elapsedSec % 60
        val timeStr = String.format(java.util.Locale.US, "%02d:%02d:%02d", h, m, s)
        
        val stopIntent = Intent(this, TrackingService::class.java).apply {{ action = ACTION_STOP }}
        val pendingStop = android.app.PendingIntent.getService(this, 0, stopIntent, 
            android.app.PendingIntent.FLAG_IMMUTABLE or android.app.PendingIntent.FLAG_UPDATE_CURRENT)

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
            val name = "4:30 Tracking"
            val descriptionText = "Фоновая запись датчиков"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {{
                description = descriptionText
                setShowBadge(false)
            }}
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
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

# ─── 5. MainActivity.kt (UI) ───
# (Сокращённая, но полнофункциональная версия с Canvas, как обсуждали)
main_activity_code = f'''package {PKG}

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.view.MotionEvent
import android.view.View
import androidx.activity.ComponentActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.abs

class MainActivity : ComponentActivity() {{
    private lateinit var mainView: MainView
    private var sessions = mutableListOf<JSONObject>()

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        requestPermissions()
        loadSessions()
        mainView = MainView(this)
        setContentView(mainView)
    }}

    override fun onResume() {{
        super.onResume()
        loadSessions()
        mainView.invalidate()
    }}

    private fun requestPermissions() {{
        val perms = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {{
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {{
                perms.add(android.Manifest.permission.POST_NOTIFICATIONS)
            }}
        }}
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.BODY_SENSORS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {{
            perms.add(android.Manifest.permission.BODY_SENSORS)
        }}
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACTIVITY_RECOGNITION) != android.content.pm.PackageManager.PERMISSION_GRANTED) {{
            perms.add(android.Manifest.permission.ACTIVITY_RECOGNITION)
        }}
        if (perms.isNotEmpty()) {{
            ActivityCompat.requestPermissions(this, perms.toTypedArray(), 100)
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
        val intent = Intent(this, TrackingService::class.java)
        val isRunning = isServiceRunning()
        if (isRunning) {{
            intent.action = TrackingService.ACTION_STOP
            startService(intent)
        }} else {{
            intent.action = TrackingService.ACTION_START
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent)
            else startService(intent)
        }}
        // Небольшая задержка для обновления UI
        mainView.postDelayed({{ mainView.invalidate() }}, 300)
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
        private var isRunning = false

        override fun onDraw(c: Canvas) {{
            super.onDraw(c)
            c.drawColor(Color.BLACK)
            isRunning = isServiceRunning()
            
            val cx = width / 2f
            val cy = height / 2f - 40f
            val r = width * 0.25f
            
            // Круг
            val bp = Paint().apply {{ color = 0xFF2A2A2A.toInt(); isAntiAlias = true }}
            val rp = Paint().apply {{ color = if (isRunning) 0xFFFF5577.toInt() else 0xFFA89CD0.toInt(); style = Paint.Style.STROKE; strokeWidth = 5f; isAntiAlias = true }}
            c.drawCircle(cx, cy, r, bp)
            c.drawCircle(cx, cy, r, rp)
            
            if (isRunning) {{
                tp.typeface = Typeface.MONOSPACE
                tp.textSize = 36f
                c.drawText("СТОП", cx, cy + 12f, tp)
            }} else {{
                tp.typeface = Typeface.DEFAULT_BOLD
                tp.textSize = 42f
                c.drawText("СТАРТ", cx, cy + 14f, tp)
            }}
            
            // Последние 2 сессии
            if (sessions.size >= 1) {{
                val fmt = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault())
                val s1 = sessions[sessions.size - 1]
                val dur1 = fmtDur(s1.optInt("durationSec", 0))
                tp.typeface = Typeface.DEFAULT
                tp.textSize = 18f
                tp.color = 0xFF888888.toInt()
                c.drawText("${{fmt.format(Date(s1.getLong("startTs")))}} · $dur1", cx, cy + r + 60f, tp)
            }}
            if (sessions.size >= 2) {{
                val fmt = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault())
                val s2 = sessions[sessions.size - 2]
                val dur2 = fmtDur(s2.optInt("durationSec", 0))
                tp.typeface = Typeface.DEFAULT
                tp.textSize = 18f
                tp.color = 0xFF666666.toInt()
                c.drawText("${{fmt.format(Date(s2.getLong("startTs")))}} · $dur2", cx, cy + r + 90f, tp)
            }}
        }}

        override fun onTouchEvent(e: MotionEvent): Boolean {{
            if (e.action == MotionEvent.ACTION_UP) {{
                val cx = width / 2f; val cy = height / 2f - 40f; val r = width * 0.25f
                val dist = kotlin.math.hypot(e.x - cx, e.y - cy)
                if (dist <= r * 1.2) {{
                    toggleTracking()
                }}
            }}
            return true
        }}
        
        private fun fmtDur(sec: Int): String {{
            if (sec < 60) return "${{sec}}с"
            val m = sec / 60
            if (m < 60) return "${{m}}м"
            return "${{m / 60}}ч${{m % 60}}м"
        }}
    }}
}}
'''

with open(f"app/src/main/java/{PKG.replace('.', '/')}/MainActivity.kt", "w", encoding="utf-8") as f:
    f.write(main_activity_code)

print("✅ Проект '4:30' успешно сгенерирован!")
print("📁 Структура:")
print("  - app/src/main/java/com/opw/fourthirty/MainActivity.kt")
print("  - app/src/main/java/com/opw/fourthirty/TrackingService.kt")
print("  - app/src/main/AndroidManifest.xml")
print("  - app/build.gradle.kts")
print("\n🚀 Чтобы собрать APK:")
print("  1. Запусти: gradle assembleRelease")
print("  2. Или закоммить в GitHub и используй Actions, как с циферблатами.")
print("  3. Установи на часы: adb install -r app/build/outputs/apk/release/app-release.apk")
