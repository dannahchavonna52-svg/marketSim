# MarketSim Fund App Android Shell

This is a native Android WebView shell for the local MarketSim Fund App.

## What It Does

- Opens your MarketSim web app inside an Android app.
- Lets you set the server URL on first launch.
- Allows plain HTTP local-network access such as `http://192.168.1.8:8000`.
- Stores the server URL on the phone.

## Before Building

This machine currently needs Android build tools:

- Android Studio, or
- JDK 17 + Android SDK + Gradle

## Build With Android Studio

1. Open `D:\桌面\基金\marketsim-web\android-app` in Android Studio.
2. Let Android Studio sync Gradle.
3. Choose `Build > Build Bundle(s) / APK(s) > Build APK(s)`.
4. The debug APK will be generated under:

```text
android-app\app\build\outputs\apk\debug\app-debug.apk
```

## Build From Command Line

After JDK, Android SDK, and Gradle are installed:

```bat
cd D:\桌面\基金\marketsim-web\android-app
build-apk.bat
```

## Phone Usage

1. Run `D:\桌面\基金\marketsim-web\start.bat` on the computer.
2. Make sure phone and computer are on the same Wi-Fi.
3. Install the APK on the phone.
4. On first launch, enter your computer server URL, for example:

```text
http://192.168.1.8:8000
```

The app will then load the web app and remember this address.
