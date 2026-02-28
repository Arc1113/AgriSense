/*
 * AgriSense ESP32-CAM Scanner Firmware — Pan-Tilt Servo Edition (Async Version)
 * =============================================================================
 * * IMPROVEMENTS:
 * - Uses esp_http_server.h for non-blocking video streaming
 * - Allows motor control WHILE video is streaming
 * - Physics/Robotics ready (Low latency)
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_timer.h"
#include "img_converters.h"
#include "fb_gfx.h"
#include "soc/soc.h" // Disable brownout problems
#include "soc/rtc_cntl_reg.h"
#include "esp_http_server.h"

// ============================================================================
// Configuration — EDIT THESE
// ============================================================================

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Servo pins (pan-tilt bracket)
#define SERVO_PAN_PIN   14  // Horizontal rotation
#define SERVO_TILT_PIN  15  // Vertical tilt

// Servo PWM configuration
#define SERVO_PWM_FREQ    50   // 50Hz standard for servos
#define SERVO_PWM_BITS    16   // 16-bit resolution

// Servo pulse width range (microseconds)
#define SERVO_MIN_PULSE   500   // 0 degrees
#define SERVO_MAX_PULSE   2500  // 180 degrees

// Servo angle limits
#define PAN_MIN       0
#define PAN_MAX       180
#define PAN_CENTER    90
#define TILT_MIN      30    
#define TILT_MAX      120   
#define TILT_CENTER   75

// ============================================================================
// Pin Definitions (AI-Thinker)
// ============================================================================
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
#define FLASH_LED_PIN      4

// ============================================================================
// Global State
// ============================================================================

httpd_handle_t camera_httpd = NULL;

// Current servo positions
int panAngle = PAN_CENTER;
int tiltAngle = TILT_CENTER;

// ============================================================================
// Servo Control Logic
// ============================================================================

void setServoAngle(uint8_t pin, int angle) {
  angle = constrain(angle, 0, 180);
  int pulseWidth = map(angle, 0, 180, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
  int duty = (pulseWidth * 65535) / 20000;
  ledcWrite(pin, duty);
}

void setServoPosition(int pan, int tilt) {
  panAngle = constrain(pan, PAN_MIN, PAN_MAX);
  tiltAngle = constrain(tilt, TILT_MIN, TILT_MAX);
  
  setServoAngle(SERVO_PAN_PIN, panAngle);
  setServoAngle(SERVO_TILT_PIN, tiltAngle);
}

void initServos() {
  // Check your ESP32 board version. 
  // If this fails to compile, replace with ledcSetup/ledcAttachPin (older API)
  ledcAttach(SERVO_PAN_PIN, SERVO_PWM_FREQ, SERVO_PWM_BITS);
  ledcAttach(SERVO_TILT_PIN, SERVO_PWM_FREQ, SERVO_PWM_BITS);
  
  setServoPosition(PAN_CENTER, TILT_CENTER);
}

// ============================================================================
// Camera Initialization
// ============================================================================

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  if(psramFound()){
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return false;
  }
  return true;
}

// ============================================================================
// HTTP Server Helpers
// ============================================================================

// Helper to extract integer parameters from URL (e.g. ?step=10)
int getQueryParam(httpd_req_t *req, const char* key, int defaultValue) {
  char* buf;
  size_t buf_len;
  char param[32];
  int value = defaultValue;

  buf_len = httpd_req_get_url_query_len(req) + 1;
  if (buf_len > 1) {
    buf = (char*)malloc(buf_len);
    if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK) {
      if (httpd_query_key_value(buf, key, param, sizeof(param)) == ESP_OK) {
        value = atoi(param);
      }
    }
    free(buf);
  }
  return value;
}

void sendJsonStatus(httpd_req_t *req) {
  char json[128];
  sprintf(json, "{\"pan_angle\":%d,\"tilt_angle\":%d}", panAngle, tiltAngle);
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_send(req, json, strlen(json));
}

// ============================================================================
// HTTP Handlers
// ============================================================================

// GET /stream
esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char * part_buf[64];

  httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=frame");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while(true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
    } else {
      _jpg_buf_len = fb->len;
      _jpg_buf = fb->buf;
    }

    if(res == ESP_OK){
      size_t hlen = snprintf((char *)part_buf, 64, "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, "\r\n--frame\r\n", 12);
    }

    if(fb){
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf){
      free(_jpg_buf);
      _jpg_buf = NULL;
    }

    if(res != ESP_OK){
      break;
    }
  }
  return res;
}

// GET / (Root HTML)
esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  // Slightly updated JS to match new backend
  const char* html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>AgriSense ESP32-CAM</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: sans-serif; text-align: center; background: #1a1a2e; color: #eee; margin: 0; padding: 20px; }
    .feed { max-width: 640px; margin: 10px auto; border: 2px solid #4ade80; border-radius: 8px; overflow: hidden; }
    .feed img { width: 100%; display: block; }
    .controls { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-top: 20px; }
    .row { display: flex; gap: 10px; }
    button { width: 60px; height: 60px; font-size: 24px; border: none; border-radius: 12px; background: #16a34a; color: white; cursor: pointer; touch-action: manipulation; }
    button:active { transform: scale(0.95); background: #15803d; }
    .center-btn { background: #0ea5e9; }
    #status { margin-top: 15px; color: #94a3b8; font-family: monospace; }
  </style>
</head>
<body>
  <h1>AgriSense Robot</h1>
  <div class="feed"><img src="/stream" alt="Stream"></div>
  <div class="controls">
    <button onclick="move('up')">&#9650;</button>
    <div class="row">
      <button onclick="move('left')">&#9664;</button>
      <button class="center-btn" onclick="move('center')">&#9678;</button>
      <button onclick="move('right')">&#9654;</button>
    </div>
    <button onclick="move('down')">&#9660;</button>
  </div>
  <div id="status">Pan: -- | Tilt: --</div>

  <script>
    function move(dir) {
      // Send request without waiting for page reload
      fetch('/motor/' + dir + '?step=5', {method: 'GET'})
        .then(r => r.json())
        .then(d => {
           document.getElementById('status').innerText = `Pan: ${d.pan_angle} | Tilt: ${d.tilt_angle}`;
        });
    }
  </script>
</body>
</html>
)rawliteral";
  
  return httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
}

// Motor Handlers
esp_err_t cmd_left_handler(httpd_req_t *req) {
  int step = getQueryParam(req, "step", 5);
  setServoPosition(panAngle - step, tiltAngle);
  sendJsonStatus(req);
  return ESP_OK;
}

esp_err_t cmd_right_handler(httpd_req_t *req) {
  int step = getQueryParam(req, "step", 5);
  setServoPosition(panAngle + step, tiltAngle);
  sendJsonStatus(req);
  return ESP_OK;
}

esp_err_t cmd_up_handler(httpd_req_t *req) {
  int step = getQueryParam(req, "step", 5);
  setServoPosition(panAngle, tiltAngle + step);
  sendJsonStatus(req);
  return ESP_OK;
}

esp_err_t cmd_down_handler(httpd_req_t *req) {
  int step = getQueryParam(req, "step", 5);
  setServoPosition(panAngle, tiltAngle - step);
  sendJsonStatus(req);
  return ESP_OK;
}

esp_err_t cmd_center_handler(httpd_req_t *req) {
  setServoPosition(PAN_CENTER, TILT_CENTER);
  sendJsonStatus(req);
  return ESP_OK;
}

// ============================================================================
// Server Setup
// ============================================================================

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  // Endpoint definitions
  httpd_uri_t index_uri = { .uri = "/", .method = HTTP_GET, .handler = index_handler, .user_ctx = NULL };
  httpd_uri_t stream_uri = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };
  httpd_uri_t left_uri = { .uri = "/motor/left", .method = HTTP_GET, .handler = cmd_left_handler, .user_ctx = NULL };
  httpd_uri_t right_uri = { .uri = "/motor/right", .method = HTTP_GET, .handler = cmd_right_handler, .user_ctx = NULL };
  httpd_uri_t up_uri = { .uri = "/motor/up", .method = HTTP_GET, .handler = cmd_up_handler, .user_ctx = NULL };
  httpd_uri_t down_uri = { .uri = "/motor/down", .method = HTTP_GET, .handler = cmd_down_handler, .user_ctx = NULL };
  httpd_uri_t center_uri = { .uri = "/motor/center", .method = HTTP_GET, .handler = cmd_center_handler, .user_ctx = NULL };

  Serial.printf("Starting web server on port: '%d'\n", config.server_port);
  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &stream_uri);
    httpd_register_uri_handler(camera_httpd, &left_uri);
    httpd_register_uri_handler(camera_httpd, &right_uri);
    httpd_register_uri_handler(camera_httpd, &up_uri);
    httpd_register_uri_handler(camera_httpd, &down_uri);
    httpd_register_uri_handler(camera_httpd, &center_uri);
  }
}

// ============================================================================
// Main Loops
// ============================================================================

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  initServos();
  initCamera();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println(WiFi.localIP());

  startCameraServer();
}

void loop() {
  // Nothing to do here! 
  // esp_http_server handles everything in background tasks.
  delay(10000); 
}