package com.agrisense.agrisense_flutter

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.Debug
import android.os.Process
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.RandomAccessFile

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.agrisense/device_metrics"

    // Track peak RSS for reset/read cycle
    private var peakRssKb: Long = 0

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "getDeviceInfo" -> result.success(getDeviceInfo())
                    "getBatteryLevel" -> result.success(getBatteryLevel())
                    "getPeakRamMB" -> result.success(getPeakRamMB())
                    "resetPeakRam" -> {
                        peakRssKb = getCurrentRssKb()
                        result.success(null)
                    }
                    "getCpuUsage" -> result.success(getCpuUsage())
                    else -> result.notImplemented()
                }
            }
    }

    private fun getDeviceInfo(): Map<String, Any?> {
        val am = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val memInfo = ActivityManager.MemoryInfo()
        am.getMemoryInfo(memInfo)

        return mapOf(
            "manufacturer" to Build.MANUFACTURER,
            "model" to Build.MODEL,
            "brand" to Build.BRAND,
            "device" to Build.DEVICE,
            "android_version" to Build.VERSION.RELEASE,
            "sdk_int" to Build.VERSION.SDK_INT,
            "hardware" to Build.HARDWARE,
            "board" to Build.BOARD,
            "supported_abis" to Build.SUPPORTED_ABIS.toList(),
            "total_ram_mb" to (memInfo.totalMem / (1024 * 1024)),
            "available_ram_mb" to (memInfo.availMem / (1024 * 1024)),
            "processors" to Runtime.getRuntime().availableProcessors()
        )
    }

    private fun getBatteryLevel(): Double? {
        return try {
            val batteryStatus: Intent? = IntentFilter(Intent.ACTION_BATTERY_CHANGED).let {
                applicationContext.registerReceiver(null, it)
            }
            val level = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
            val scale = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
            if (level >= 0 && scale > 0) {
                (level.toDouble() / scale.toDouble()) * 100.0
            } else null
        } catch (_: Exception) {
            null
        }
    }

    private fun getPeakRamMB(): Double {
        val currentRss = getCurrentRssKb()
        if (currentRss > peakRssKb) {
            peakRssKb = currentRss
        }
        return peakRssKb / 1024.0
    }

    private fun getCurrentRssKb(): Long {
        return try {
            // Read /proc/self/status for VmRSS (most accurate)
            val status = RandomAccessFile("/proc/self/status", "r")
            var line: String?
            var rss: Long = 0
            while (status.readLine().also { line = it } != null) {
                if (line!!.startsWith("VmRSS:")) {
                    rss = line!!.replace(Regex("[^0-9]"), "").toLongOrNull() ?: 0
                    break
                }
            }
            status.close()
            if (rss > 0) rss else {
                // Fallback to Debug.getNativeHeapAllocatedSize
                (Debug.getNativeHeapAllocatedSize() + Runtime.getRuntime().totalMemory()) / 1024
            }
        } catch (_: Exception) {
            (Debug.getNativeHeapAllocatedSize() + Runtime.getRuntime().totalMemory()) / 1024
        }
    }

    private fun getCpuUsage(): Double? {
        return try {
            val pid = Process.myPid()
            val stat = RandomAccessFile("/proc/$pid/stat", "r")
            val line = stat.readLine()
            stat.close()

            val parts = line.split(" ")
            if (parts.size > 16) {
                val utime = parts[13].toLong()  // user mode jiffies
                val stime = parts[14].toLong()  // kernel mode jiffies
                val totalTime = utime + stime

                // Read system uptime
                val uptimeFile = RandomAccessFile("/proc/uptime", "r")
                val uptimeLine = uptimeFile.readLine()
                uptimeFile.close()
                val uptime = uptimeLine.split(" ")[0].toDouble()

                val starttime = parts[21].toLong()
                val hertz = 100L  // standard jiffies/second

                val elapsed = uptime - (starttime.toDouble() / hertz)
                if (elapsed > 0) {
                    ((totalTime.toDouble() / hertz) / elapsed) * 100.0
                } else null
            } else null
        } catch (_: Exception) {
            null
        }
    }
}