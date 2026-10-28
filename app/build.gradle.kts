plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.wordclock"
    compileSdk = 34

    defaultConfig {
        applicationId "com.example.wordclock"
        minSdk 30
        targetSdk 34   // <--- МЕНЯЕМ 34 НА 33
        versionCode 1
        versionName "1.0"
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
    implementation("androidx.wear.watchface:watchface:1.2.1")
    implementation("androidx.wear.watchface:watchface-editor:1.2.1")
}
