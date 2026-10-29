package com.example.wordclock

import android.app.Activity
import android.app.WallpaperManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Toast
import java.time.ZonedDateTime

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
        clockView = WordPreviewView(this)
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

    private fun tryActivateWatchFace() {
        val component = ComponentName(this, WordWatchFaceService::class.java)

        val intents = listOf(
            Intent("com.google.android.wearable.watchface.action.SET_WATCH_FACE").apply {
                putExtra("com.google.android.wearable.watchface.extra.WATCH_FACE_COMPONENT", component)
            },
            Intent(WallpaperManager.ACTION_CHANGE_LIVE_WALLPAPER).apply {
                putExtra(WallpaperManager.EXTRA_LIVE_WALLPAPER_COMPONENT, component)
            },
            Intent(WallpaperManager.ACTION_LIVE_WALLPAPER_CHOOSER)
        )

        for (intent in intents) {
            try {
                startActivity(intent)
                Toast.makeText(this, "Открыт селектор: ${intent.action?.substringAfterLast('.')}", Toast.LENGTH_SHORT).show()
                return
            } catch (_: Exception) {}
        }

        Toast.makeText(this, "Зажмите экран -> '+' -> Словами", Toast.LENGTH_LONG).show()
    }

    private inner class WordPreviewView(context: Context) : View(context) {
        private val pixelFont: Typeface by lazy {
            try {
                Typeface.createFromAsset(assets, "minecraft.ttf")
            } catch (_: Exception) {
                Typeface.MONOSPACE
            }
        }

        private val paint = Paint().apply {
            color = Color.WHITE
            textAlign = Paint.Align.LEFT
            isAntiAlias = false
        }

        private val hintPaint = Paint().apply {
            color = Color.GRAY
            textAlign = Paint.Align.CENTER
            isAntiAlias = true
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            canvas.drawColor(Color.BLACK)

            paint.typeface = pixelFont
            val now = ZonedDateTime.now()
            val lines = getRussianTime(now.hour, now.minute)

            val fontSize = width * 0.088f
            val lineSpacing = fontSize * 1.35f
            paint.textSize = fontSize

            val startX = width * 0.20f
            var startY = (height / 2f) - (lines.size * lineSpacing / 2f) + fontSize

            for (line in lines) {
                canvas.drawText(line, startX, startY, paint)
                startY += lineSpacing
            }

            hintPaint.textSize = width * 0.038f
            canvas.drawText("[ Нажми для установки ]", width / 2f, height * 0.88f, hintPaint)
        }

        override fun onTouchEvent(event: MotionEvent): Boolean {
            if (event.action == MotionEvent.ACTION_UP) {
                tryActivateWatchFace()
                return true
            }
            return true
        }
    }

    private fun getRussianTime(hour: Int, min: Int): List<String> {
        val h12 = (if (min > 30) hour + 1 else hour) % 12
        val nextH = if (h12 == 0) 12 else h12
        val nom = arrayOf("", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать")
        val gen = arrayOf("", "первого", "второго", "третьего", "четвертого", "пятого", "шестого", "седьмого", "восьмого", "девятого", "десятого", "одиннадцатого", "двенадцатого")

        return when {
            min == 0 -> {
                val tod = when (hour) {
                    in 4..11 -> "утра"
                    in 12..16 -> "дня"
                    in 17..22 -> "вечера"
                    else -> "ночи"
                }
                val curH = if (hour % 12 == 0) 12 else hour % 12
                listOf(nom[curH], "часов", tod)
            }
            min == 15 -> listOf("четверть", gen[nextH])
            min == 30 -> listOf("половина", gen[nextH])
            min == 45 -> listOf("без", "четверти", nom[nextH])
            min < 30 -> {
                val mWord = when (min) {
                    1 -> listOf("одна", "минута")
                    2 -> listOf("две", "минуты")
                    5 -> listOf("пять", "минут")
                    10 -> listOf("десять", "минут")
                    20 -> listOf("двадцать", "минут")
                    else -> listOf("$min", "минут")
                }
                mWord + listOf(gen[nextH])
            }
            else -> {
                val left = 60 - min
                val leftWords = when (left) {
                    5 -> listOf("без", "пяти")
                    10 -> listOf("без", "десяти")
                    15 -> listOf("без", "четверти")
                    20 -> listOf("без", "двадцати")
                    else -> listOf("без", "$left")
                }
                leftWords + listOf(nom[nextH])
            }
        }
    }
}
