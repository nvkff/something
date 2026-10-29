package com.example.wordclock

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

class WordWatchFaceService : WatchFaceService() {

    override fun createComplicationSlotsManager(
        currentUserStyleRepository: CurrentUserStyleRepository
    ): ComplicationSlotsManager {
        return ComplicationSlotsManager(emptyList(), currentUserStyleRepository)
    }

    override suspend fun createWatchFace(
        surfaceHolder: SurfaceHolder,
        watchState: WatchState,
        complicationSlotsManager: ComplicationSlotsManager,
        currentUserStyleRepository: CurrentUserStyleRepository
    ): WatchFace {
        val renderer = WordCanvasRenderer(
            surfaceHolder,
            currentUserStyleRepository,
            watchState,
            16L
        )
        return WatchFace(WatchFaceType.DIGITAL, renderer)
    }

    private class NoSharedAssets : Renderer.SharedAssets {
        override fun onDestroy() {}
    }

    private inner class WordCanvasRenderer(
        surfaceHolder: SurfaceHolder,
        currentUserStyleRepository: CurrentUserStyleRepository,
        watchState: WatchState,
        interactiveDrawModeUpdateDelayMillis: Long
    ) : Renderer.CanvasRenderer2<NoSharedAssets>(
        surfaceHolder,
        currentUserStyleRepository,
        watchState,
        CanvasType.HARDWARE,
        interactiveDrawModeUpdateDelayMillis,
        clearWithBackgroundTintBeforeRenderingHighlightLayer = true
    ) {
        private val pixelFont: Typeface by lazy {
            try {
                Typeface.createFromAsset(this@WordWatchFaceService.assets, "minecraft.ttf")
            } catch (_: Exception) {
                Typeface.MONOSPACE
            }
        }

        private val paintRegular = Paint().apply {
            color = Color.WHITE
            textAlign = Paint.Align.LEFT
        }

        private val paintBold = Paint().apply {
            color = Color.WHITE
            textAlign = Paint.Align.LEFT
        }

        override suspend fun createSharedAssets(): NoSharedAssets = NoSharedAssets()

        override fun render(
            canvas: Canvas,
            bounds: Rect,
            zonedDateTime: ZonedDateTime,
            sharedAssets: NoSharedAssets
        ) {
            val isAmbient = renderParameters.drawMode == DrawMode.AMBIENT

            canvas.drawColor(Color.BLACK)

            paintRegular.typeface = pixelFont
            paintBold.typeface = pixelFont
            paintRegular.isAntiAlias = false
            paintBold.isAntiAlias = false

            if (isAmbient) {
                paintRegular.style = Paint.Style.STROKE
                paintRegular.strokeWidth = bounds.width() * 0.006f
                paintBold.style = Paint.Style.STROKE
                paintBold.strokeWidth = bounds.width() * 0.012f
            } else {
                paintRegular.style = Paint.Style.FILL
                paintBold.style = Paint.Style.FILL
            }

            val lines = getRussianTime(zonedDateTime.hour, zonedDateTime.minute)
            val fontSize = bounds.width() * 0.088f
            val lineSpacing = fontSize * 1.32f

            paintRegular.textSize = fontSize
            paintBold.textSize = fontSize

            val startX = bounds.left + bounds.width() * 0.18f
            var startY = bounds.centerY() - (lines.size * lineSpacing / 2f) + fontSize

            for (i in lines.indices) {
                val p = if (i == lines.lastIndex) paintBold else paintRegular
                canvas.drawText(lines[i], startX, startY, p)
                startY += lineSpacing
            }
        }

        override fun renderHighlightLayer(
            canvas: Canvas,
            bounds: Rect,
            zonedDateTime: ZonedDateTime,
            sharedAssets: NoSharedAssets
        ) {}

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
                        1 -> listOf("час", "ночи")
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
                        31 -> listOf("тридцать", "один")
                        32 -> listOf("тридцать", "два")
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
                        else -> listOf("без", "$left")
                    }
                    leftWords + listOf(nom[nextH])
                }
            }
        }
    }
}
