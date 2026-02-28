/*
 * AgriSense ESP32-CAM Robot Controller
 * Handles:
 *   - Linear rail (rack & pinion / belt drive) via DC motor or stepper
 *   - Pan-tilt servo bracket
 *   - Camera streaming
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include "esp_camera.h"

// ===== WiFi Config =====
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

// ===== Pin Definitions =====
// Linear rail motor (L298N or similar driver)
#define RAIL_IN1     12
#define RAIL_IN2     13
#define RAIL_EN      14  // PWM enable pin

// Pan-tilt servos
#define PAN_SERVO_PIN   2
#define TILT_SERVO_PIN  15

// ===== Objects =====
WebServer server(80);
Servo panServo;
Servo tiltServo;

int currentPan = 90;
int currentTilt = 90;

// ===== Camera pin config (AI-Thinker ESP32-CAM) =====
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count     = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
  }
}

// ===== Rail Motor Control =====
void railMove(String dir, int speed) {
  analogWrite(RAIL_EN, speed);
  if (dir == "left") {
    digitalWrite(RAIL_IN1, HIGH);
    digitalWrite(RAIL_IN2, LOW);
  } else if (dir == "right") {
    digitalWrite(RAIL_IN1, LOW);
    digitalWrite(RAIL_IN2, HIGH);
  } else {
    // stop
    digitalWrite(RAIL_IN1, LOW);
    digitalWrite(RAIL_IN2, LOW);
    analogWrite(RAIL_EN, 0);
  }
}

// ===== Route Handlers =====
void handlePing() {
  server.send(200, "text/plain", "pong");
}

void handleLinear() {
  String dir = server.arg("dir");
  int speed = server.hasArg("speed") ? server.arg("speed").toInt() : 150;
  if (dir.length() == 0) dir = "stop";
  speed = constrain(speed, 0, 255);

  railMove(dir, speed);

  server.send(200, "text/plain", "OK: rail " + dir + " speed=" + String(speed));
}

void handlePanTilt() {
  if (server.hasArg("pan")) {
    currentPan = constrain(server.arg("pan").toInt(), 0, 180);
    panServo.write(currentPan);
  }
  if (server.hasArg("tilt")) {
    currentTilt = constrain(server.arg("tilt").toInt(), 0, 180);
    tiltServo.write(currentTilt);
  }
  server.send(200, "text/plain", "OK: pan=" + String(currentPan) + " tilt=" + String(currentTilt));
}

void handleHome() {
  currentPan = 90;
  currentTilt = 90;
  panServo.write(90);
  tiltServo.write(90);
  railMove("stop", 0);
  server.send(200, "text/plain", "OK: homed");
}

void handleCapture() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void setup() {
  Serial.begin(115200);

  // Motor pins
  pinMode(RAIL_IN1, OUTPUT);
  pinMode(RAIL_IN2, OUTPUT);
  pinMode(RAIL_EN, OUTPUT);
  digitalWrite(RAIL_IN1, LOW);
  digitalWrite(RAIL_IN2, LOW);

  // Servos
  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);
  panServo.write(90);
  tiltServo.write(90);

  // Camera
  setupCamera();

  // WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // Routes
  server.on("/ping",    handlePing);
  server.on("/linear",  handleLinear);
  server.on("/pantilt", handlePanTilt);
  server.on("/home",    handleHome);
  server.on("/capture", handleCapture);

  server.begin();
  Serial.println("Server started");
}

void loop() {
  server.handleClient();
}
