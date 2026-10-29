plugins {
    id("com.android.application")
}

android {
    namespace = "com.example.wordclock"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.wordclock"
        minSdk = 33
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}
