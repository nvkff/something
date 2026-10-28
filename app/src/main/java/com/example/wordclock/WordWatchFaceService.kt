package com.example.wordclock

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.Typeface
import android.view.SurfaceHolder
import androidx.wear.watchface.CanvasRenderer
import androidx.wear.watchface.DrawMode
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
        currentUserStyleRepository: CurrentUserStyleRepository
    ): WatchFace {
        val renderer = WordCanvasRenderer(
            surfaceHolder,
            currentUserStyleRepository,
            watchState,
            CanvasType.HARDWARE
        )
        return WatchFace(WatchFaceType.DIGITAL, renderer)
    }

    private inner class WordCanvasRenderer(
        surfaceHolder: SurfaceHolder,
        currentUserStyleRepository: CurrentUserStyleRepository,
        watchState: WatchState,
        canvasType: Int
    ) : CanvasRenderer(
        surfaceHolder,
        currentUserStyleRepository,
        watchState,
        canvasType,
        16L,
        clearWithBackgroundTintBeforeRenderingHighlightLayer = true
    ) {
        private val paintRegular = Paint().apply {
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            textAlign = Paint.Align.LEFT
        }

        private val paintBold = Paint().apply {
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
            textAlign = Paint.Align.LEFT
        }

        override fun render(canvas: Canvas, bounds: Rect, zonedDateTime: ZonedDateTime) {
            val isAmbient = renderParameters.drawMode == DrawMode.AMBIENT

            // Светлый E-Ink фон при включенном экране, черный в AOD
            canvas.drawColor(if (isAmbient) Color.BLACK else Color.WHITE)

            val textColor = if (isAmbient) Color.WHITE else Color.BLACK
            paintRegular.color = textColor
            paintBold.color = textColor
            paintRegular.isAntiAlias = !isAmbient
            paintBold.isAntiAlias = !isAmbient

            val lines = getRussianTime(zonedDateTime.hour, zonedDateTime.minute)
            val fontSize = bounds.width() * 0.085f
            val lineSpacing = fontSize * 1.25f

            paintRegular.textSize = fontSize
            paintBold.textSize = fontSize

            val startX = bounds.left + bounds.width() * 0.22f
            var startY = bounds.centerY() - (lines.size * lineSpacing / 2f) + fontSize

            for (i in lines.indices) {
                // Последняя строка (сам час) выделяется жирным, как на фото
                val p = if (i == lines.lastIndex) paintBold else paintRegular
                canvas.drawText(lines[i], startX, startY, p)
                startY += lineSpacing
            }
        }

        override fun renderHighlightLayer(canvas: Canvas, bounds: Rect, zonedDateTime: ZonedDateTime) {}

        private fun getRussianTime(hour: Int, min: Int): List<String> {
            val h12 = (if (min > 30) hour + 1 else hour) % 12
            val nextH = if (h12 == 0) 12 else h12

            val nom = arrayOf(
                "", "один", "два", "три", "четыре", "пять",
                "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать"
            )
            val gen = arrayOf(
                "", "первого", "второго", "третьего", "четвертого", "пятого",
                "шестого", "седьмого", "восьмого", "девятого", "десятого", "одиннадцатого", "двенадцатого"
            )

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
}
