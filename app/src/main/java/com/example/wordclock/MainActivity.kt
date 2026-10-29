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

        private val hintPaint = Paint().apply {
            color = Color.GRAY
            textAlign = Paint.Align.CENTER
            isAntiAlias = true
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            canvas.drawColor(Color.BLACK)

            paintRegular.typeface = pixelFont
            paintBold.typeface = pixelFont

            val now = ZonedDateTime.now()
            val lines = getRussianTime(now.hour, now.minute)

            val fontSize = width * 0.088f
            val lineSpacing = fontSize * 1.32f

            paintRegular.textSize = fontSize
            paintBold.textSize = fontSize

            val startX = width * 0.18f
            var startY = (height / 2f) - (lines.size * lineSpacing / 2f) + fontSize

            for (i in lines.indices) {
                val p = if (i == lines.lastIndex) paintBold else paintRegular
                canvas.drawText(lines[i], startX, startY, p)
                startY += lineSpacing
            }

            hintPaint.textSize = width * 0.038f
            canvas.drawText("[ Нажми для установки ]", width / 2f, height * 0.90f, hintPaint)
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
        val h12 = if (hour % 12 == 0) 12 else hour % 12
        val nextH = if ((hour + 1) % 12 == 0) 12 else (hour + 1) % 12

        val nom = arrayOf(
            "", "один", "два", "три", "четыре", "пять",
            "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать"
        )
        val gen = arrayOf(
            "", "первого", "второго", "третьего", "четвертого", "пятого",
            "шестого", "седьмого", "восьмого", "девятого", "десятого", "одиннадцатого", "двенадцатого"
        )

        val tod = when (hour) {
            in 4..11 -> "утра"
            in 12..16 -> "дня"
            in 17..22 -> "вечера"
            else -> "ночи"
        }

        return when {
            min == 0 -> {
                when (h12) {
                    1 -> listOf("час", tod)
                    in 2..4 -> listOf(nom[h12], "часа", tod)
                    else -> listOf(nom[h12], "часов", tod)
                }
            }
            min == 15 -> listOf("четверть", gen[nextH])
            min == 30 -> listOf("половина", gen[nextH])
            min == 45 -> listOf("без", "четверти", nom[nextH])
            min == 35 -> listOf("без", "двадцати", "пяти", nom[nextH])
            min in 31..39 -> {
                val mWords = when (min) {
                    31 -> listOf("тридцать", "одна")
                    32 -> listOf("тридцать", "две")
                    33 -> listOf("тридцать", "три")
                    34 -> listOf("тридцать", "четыре")
                    36 -> listOf("тридцать", "шесть")
                    37 -> listOf("тридцать", "семь")
                    38 -> listOf("тридцать", "восемь")
                    else -> listOf("тридцать", "девять")
                }
                listOf(nom[h12]) + mWords
            }
            min < 30 -> {
                val mWords = when (min) {
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
                    18 -> listOf("восемнадцать", "минут")
                    19 -> listOf("девятнадцать", "минут")
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
                mWords + listOf(gen[nextH])
            }
            else -> {
                val left = 60 - min
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
                    11 -> listOf("без", "одиннадцати")
                    12 -> listOf("без", "двенадцати")
                    13 -> listOf("без", "тринадцати")
                    14 -> listOf("без", "четырнадцати")
                    16 -> listOf("без", "шестнадцати")
                    17 -> listOf("без", "семнадцати")
                    18 -> listOf("без", "восем", "надцати")
                    19 -> listOf("без", "девятнадцати")
                    20 -> listOf("без", "двадцати")
                    else -> listOf("без", "двадцати")
                }
                leftWords + listOf(nom[nextH])
            }
        }
    }
}
