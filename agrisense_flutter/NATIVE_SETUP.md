<!-- Android Manifest: Place this content into the actual AndroidManifest.xml
     after running `flutter create .` in the agrisense_flutter directory.
     
     Add these permissions inside the <manifest> tag:
-->

<!--
Required permissions for AgriSense Flutter:

<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />

Inside <application> tag, add:
    android:label="AgriSense"
    android:icon="@mipmap/ic_launcher"
    android:usesCleartextTraffic="true"
-->

<!-- 
iOS: Add these to ios/Runner/Info.plist:

<key>NSCameraUsageDescription</key>
<string>AgriSense needs camera access to scan plant leaves for disease detection</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>AgriSense needs photo library access to analyze saved plant images</string>
<key>NSMicrophoneUsageDescription</key>
<string>Not used but required by camera plugin</string>
-->
