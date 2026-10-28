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
        // Загрузка пиксельного шрифта из папки assets (с fallback на Monospace при отсутствии)
        private val pixelFont: Typeface by lazy {
            try {
                Typeface.createFromAsset(this@WordWatchFaceService.assets, "minecraft.ttf")
            } catch (e: Exception) {
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

        override suspend fun createSharedAssets(): NoSharedAssets {
            return NoSharedAssets()
        }

        override fun render(
            canvas: Canvas,
            bounds: Rect,
            zonedDateTime: ZonedDateTime,
            sharedAssets: NoSharedAssets
        ) {
            val isAmbient = renderParameters.drawMode == DrawMode.AMBIENT

            // Всегда глубокий черный фон (экономит батарею OLED и не слепит)
            canvas.drawColor(Color.BLACK)

            // Для аутентичного пиксель-арта отключаем сглаживание
            paintRegular.typeface = pixelFont
            paintBold.typeface = pixelFont
            paintRegular.isAntiAlias = false
            paintBold.isAntiAlias = false

            if (isAmbient) {
                // В режиме AOD (Always-On): полый контурный шрифт с белой рамкой
                paintRegular.style = Paint.Style.STROKE
                paintRegular.strokeWidth = bounds.width() * 0.005f // тонкая рамка ~2-3px

                paintBold.style = Paint.Style.STROKE
                paintBold.strokeWidth = bounds.width() * 0.012f // более жирная рамка для часа
            } else {
                // В активном режиме: сплошная белая заливка
                paintRegular.style = Paint.Style.FILL
                paintBold.style = Paint.Style.FILL
            }

            val lines = getRussianTime(zonedDateTime.hour, zonedDateTime.minute)
            val fontSize = bounds.width() * 0.09f
            val lineSpacing = fontSize * 1.35f

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
