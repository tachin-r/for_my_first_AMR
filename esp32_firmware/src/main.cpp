/**
 * AMR ESP32 Motor Controller Firmware
 * =====================================
 * Hardware:
 *   Motor A (Left):   ENA=GPIO14(PWM), IN1=GPIO26, IN2=GPIO27
 *   Motor B (Right):  ENB=GPIO21(PWM), IN3=GPIO22, IN4=GPIO23
 *   Encoder A (Left): PhA=GPIO32(INT), PhB=GPIO33
 *   Encoder B (Right):PhA=GPIO19(INT), PhB=GPIO18
 *
 * Serial Protocol (115200 baud):
 *   Pi5 → ESP32:  {"l":0.10,"r":0.10}\n      (target velocity m/s, left & right)
 *   ESP32 → Pi5:  {"lt":N,"rt":N,"lv":0.10,"rv":0.10,"dt":50}\n
 *                 lt/rt = cumulative encoder ticks
 *                 lv/rv = current velocity (m/s)
 *                 dt    = control loop interval (ms)
 *
 * Robot Specs:
 *   Wheel diameter : 65mm
 *   Wheelbase      : 200mm
 *   Encoder PPR    : 506 pulses/wheel-rev (Phase A rising edge)
 *   x2 counting    : CHANGE interrupt → 1012 counts/wheel-rev
 */

#include <Arduino.h>
#include <ArduinoJson.h>

// ================================================================
//  PIN DEFINITIONS
// ================================================================
// Motor A — Left
#define MOTOR_A_ENA  14
#define MOTOR_A_IN1  26
#define MOTOR_A_IN2  27

// Motor B — Right
#define MOTOR_B_ENB  21
#define MOTOR_B_IN3  22
#define MOTOR_B_IN4  23

// Encoder A — Left  (interrupt on Phase A, direction from Phase B)
#define ENC_A_PHA    32
#define ENC_A_PHB    33

// Encoder B — Right
#define ENC_B_PHA    19
#define ENC_B_PHB    18

// ================================================================
//  PWM — ใช้ analogWrite() เหมือน test_L298N ที่พิสูจน์แล้วว่าทำงานได้
//  ทำงานได้ทั้ง arduino-esp32 2.x และ 3.x
//  duty 0-255 (8-bit default)
// ================================================================

// ================================================================
//  ROBOT PHYSICAL SPECS
// ================================================================
static const float WHEEL_DIAMETER_M   = 0.065f;              // 65 mm
static const float WHEEL_CIRCUMFERENCE = (float)M_PI * WHEEL_DIAMETER_M; // ~0.2042 m
static const int   ENCODER_PPR        = 506;                 // Phase A rising edge per wheel-rev
static const int   ENCODER_CPR        = ENCODER_PPR * 2;    // x2 (CHANGE interrupt) = 1012 counts
static const float DIST_PER_COUNT     = WHEEL_CIRCUMFERENCE / (float)ENCODER_CPR; // ~0.2018 mm/count
static const float WHEELBASE_M        = 0.200f;              // 200 mm

// ================================================================
//  PID PARAMETERS  (ปรับได้ผ่าน Serial: {"pid_kp":400,"pid_ki":50,"pid_kd":2})
// ================================================================
float PID_KP = 400.0f;  // ปรับขึ้นจาก 80 → 400 (motor ~357 PWM per m/s)
float PID_KI =  50.0f;  // ปรับขึ้นจาก 15 → 50
float PID_KD =   2.0f;

#define PID_LOOP_MS     50     // 20 Hz control loop
#define MAX_PWM         230    // เผื่อ headroom (max 255)
#define MIN_START_PWM   45     // ลดจาก 65→45 เพื่อให้หมุนช้าได้ (ω=1.0 rad/s)
#define CMD_TIMEOUT_MS  500    // หยุดถ้าไม่ได้รับคำสั่งนาน 500ms

// === ทิศทางหุ่น ===
// true  = caster wheel อยู่ด้านหน้า (ข้างหน้าคือด้านที่ไม่มีมอเตอร์)
// false = drive wheels อยู่ด้านหน้า
#define CASTER_IS_FRONT true

// ================================================================
//  GLOBAL STATE
// ================================================================
// Encoder (volatile — เขียนใน ISR)
volatile long enc_A_count = 0;
volatile long enc_B_count = 0;

// PID state
float target_vel_A = 0.0f;   // m/s
float target_vel_B = 0.0f;
float pid_integ_A  = 0.0f;
float pid_integ_B  = 0.0f;
float pid_prev_A   = 0.0f;
float pid_prev_B   = 0.0f;

// Velocity measurement
long  prev_enc_A   = 0;
long  prev_enc_B   = 0;
float current_vel_A = 0.0f;
float current_vel_B = 0.0f;

// Timing
unsigned long last_pid_ms  = 0;
unsigned long last_cmd_ms  = 0;

// ================================================================
//  ENCODER ISR
// ================================================================
/*
 * ตรรกะทิศทาง (quadrature x2):
 *   เมื่อ PhA เปลี่ยน และ PhA == PhB → หมุนทวนเข็ม (-)
 *   เมื่อ PhA เปลี่ยน และ PhA != PhB → หมุนตามเข็ม (+)
 *
 * หมายเหตุ: ถ้าล้อหมุนกลับทิศกับที่คาด ให้สลับสัญลักษณ์ +/- ในแต่ละ ISR
 */
void IRAM_ATTR isr_enc_A() {
#if CASTER_IS_FRONT
  // เมื่อ caster ด้านหน้า: วิ่งหน้า → enc เพิ่ม (+)
  if (digitalRead(ENC_A_PHA) == digitalRead(ENC_A_PHB)) {
    enc_A_count++;
  } else {
    enc_A_count--;
  }
#else
  if (digitalRead(ENC_A_PHA) == digitalRead(ENC_A_PHB)) {
    enc_A_count--;
  } else {
    enc_A_count++;
  }
#endif
}

void IRAM_ATTR isr_enc_B() {
  // Motor B อยู่ฝั่งตรงข้าม
#if CASTER_IS_FRONT
  if (digitalRead(ENC_B_PHA) == digitalRead(ENC_B_PHB)) {
    enc_B_count--;
  } else {
    enc_B_count++;
  }
#else
  if (digitalRead(ENC_B_PHA) == digitalRead(ENC_B_PHB)) {
    enc_B_count++;
  } else {
    enc_B_count--;
  }
#endif
}

// ================================================================
//  MOTOR CONTROL
// ================================================================
// ================================================================
//  MOTOR CONTROL — ใช้ analogWrite() (เหมือน test_L298N)
// ================================================================
void setMotorA(int pwm) {  // pwm: -255 to +255
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0) {
    digitalWrite(MOTOR_A_IN1, HIGH);
    digitalWrite(MOTOR_A_IN2, LOW);
    analogWrite(MOTOR_A_ENA, pwm);
  } else if (pwm < 0) {
    digitalWrite(MOTOR_A_IN1, LOW);
    digitalWrite(MOTOR_A_IN2, HIGH);
    analogWrite(MOTOR_A_ENA, -pwm);
  } else {
    digitalWrite(MOTOR_A_IN1, LOW);
    digitalWrite(MOTOR_A_IN2, LOW);
    analogWrite(MOTOR_A_ENA, 0);
  }
}

void setMotorB(int pwm) {
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0) {
    digitalWrite(MOTOR_B_IN3, HIGH);
    digitalWrite(MOTOR_B_IN4, LOW);
    analogWrite(MOTOR_B_ENB, pwm);
  } else if (pwm < 0) {
    digitalWrite(MOTOR_B_IN3, LOW);
    digitalWrite(MOTOR_B_IN4, HIGH);
    analogWrite(MOTOR_B_ENB, -pwm);
  } else {
    digitalWrite(MOTOR_B_IN3, LOW);
    digitalWrite(MOTOR_B_IN4, LOW);
    analogWrite(MOTOR_B_ENB, 0);
  }
}

void stopAll() {
  setMotorA(0);
  setMotorB(0);
  target_vel_A = 0.0f;
  target_vel_B = 0.0f;
  pid_integ_A  = pid_integ_B  = 0.0f;
  pid_prev_A   = pid_prev_B   = 0.0f;
}

// ================================================================
//  PID VELOCITY CONTROLLER
// ================================================================
int computePID(float target, float measured,
               float &integral, float &prev_err, float dt) {
  if (fabsf(target) < 0.001f) {
    // Reset integral เมื่อ setpoint = 0
    integral = 0.0f;
    prev_err = 0.0f;
    return 0;
  }

  float err       = target - measured;
  integral       += err * dt;

  // Anti-windup
  float integ_limit = 200.0f / (PID_KI + 1e-6f);
  integral = constrain(integral, -integ_limit, integ_limit);

  float derivative = (err - prev_err) / dt;
  prev_err         = err;

  float output = PID_KP * err + PID_KI * integral + PID_KD * derivative;

  int sign = (output >= 0.0f) ? 1 : -1;
  int mag  = constrain((int)fabsf(output), 0, MAX_PWM);

  // Dead-zone kickstart: ถ้า PWM น้อยเกินไปมอเตอร์ไม่ขยับ
  // บังคับให้อย่างน้อย MIN_START_PWM เพื่อ overcome static friction ทันที
  if (mag > 0 && mag < MIN_START_PWM) {
    mag = MIN_START_PWM;
  }

  return sign * mag;
}

// ================================================================
//  SETUP
// ================================================================
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50);  // timeout สำหรับ readStringUntil

  // --- Motor Output Pins ---
  pinMode(MOTOR_A_IN1, OUTPUT); digitalWrite(MOTOR_A_IN1, LOW);
  pinMode(MOTOR_A_IN2, OUTPUT); digitalWrite(MOTOR_A_IN2, LOW);
  pinMode(MOTOR_B_IN3, OUTPUT); digitalWrite(MOTOR_B_IN3, LOW);
  pinMode(MOTOR_B_IN4, OUTPUT); digitalWrite(MOTOR_B_IN4, LOW);

  // --- PWM pins (analogWrite ไม่ต้องตั้งค่า LEDC) ---
  pinMode(MOTOR_A_ENA, OUTPUT);
  pinMode(MOTOR_B_ENB, OUTPUT);

  stopAll();

  // --- Encoder Input Pins ---
  pinMode(ENC_A_PHA, INPUT_PULLUP);
  pinMode(ENC_A_PHB, INPUT_PULLUP);
  pinMode(ENC_B_PHA, INPUT_PULLUP);
  pinMode(ENC_B_PHB, INPUT_PULLUP);

  // Attach interrupts (CHANGE = both edges → x2 counting)
  attachInterrupt(digitalPinToInterrupt(ENC_A_PHA), isr_enc_A, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_B_PHA), isr_enc_B, CHANGE);

  last_pid_ms = millis();
  last_cmd_ms = millis();

  // ส่ง ready message
  Serial.println("{\"status\":\"ready\",\"fw\":\"1.0\"}");
}

// ================================================================
//  MAIN LOOP
// ================================================================
void loop() {
  unsigned long now = millis();

  // ----------------------------------------------------------------
  //  1) รับคำสั่งจาก Pi5
  // ----------------------------------------------------------------
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 2) {
      StaticJsonDocument<128> doc;
      DeserializationError e = deserializeJson(doc, line);
      if (!e) {
        // คำสั่งความเร็ว: {"l": m/s, "r": m/s}
        if (doc.containsKey("l") || doc.containsKey("r")) {
          // Motor A = physical right, Motor B = physical left
          // (สลับเพื่อให้ตรง URDF: left_wheel y=+0.1, right_wheel y=-0.1)
          target_vel_A = doc["r"] | 0.0f;   // Motor A ← right command
          target_vel_B = doc["l"] | 0.0f;   // Motor B ← left command
          last_cmd_ms  = now;
        }
        // ปรับ PID gains แบบ runtime: {"pid_kp":80,"pid_ki":15,"pid_kd":1}
        if (doc.containsKey("pid_kp")) PID_KP = doc["pid_kp"];
        if (doc.containsKey("pid_ki")) PID_KI = doc["pid_ki"];
        if (doc.containsKey("pid_kd")) PID_KD = doc["pid_kd"];
        // Reset: {"reset":1}
        if (doc["reset"] == 1) {
          noInterrupts();
          enc_A_count = 0;
          enc_B_count = 0;
          interrupts();
          stopAll();
        }
      }
    }
  }

  // ----------------------------------------------------------------
  //  2) Safety Timeout — หยุดถ้าไม่ได้รับคำสั่งนาน CMD_TIMEOUT_MS
  // ----------------------------------------------------------------
  if ((now - last_cmd_ms) > CMD_TIMEOUT_MS) {
    target_vel_A = 0.0f;
    target_vel_B = 0.0f;
  }

  // ----------------------------------------------------------------
  //  3) PID Control Loop @ 20 Hz
  // ----------------------------------------------------------------
  unsigned long elapsed = now - last_pid_ms;
  if (elapsed >= PID_LOOP_MS) {
    float dt = (float)elapsed / 1000.0f;  // convert to seconds
    last_pid_ms = now;

    // อ่าน encoder แบบ atomic
    noInterrupts();
    long cur_A = enc_A_count;
    long cur_B = enc_B_count;
    interrupts();

    // คำนวณ velocity
    long  delta_A    = cur_A - prev_enc_A;
    long  delta_B    = cur_B - prev_enc_B;
    prev_enc_A       = cur_A;
    prev_enc_B       = cur_B;
    current_vel_A    = ((float)delta_A * DIST_PER_COUNT) / dt;  // m/s
    current_vel_B    = ((float)delta_B * DIST_PER_COUNT) / dt;

    // PID → PWM
    int pwm_A = computePID(target_vel_A, current_vel_A, pid_integ_A, pid_prev_A, dt);
    int pwm_B = computePID(target_vel_B, current_vel_B, pid_integ_B, pid_prev_B, dt);

    setMotorA(pwm_A);
    setMotorB(pwm_B);

    // ----------------------------------------------------------------
    //  4) ส่ง Odometry กลับไปที่ Pi5
    // ----------------------------------------------------------------
    StaticJsonDocument<192> out;
    // Encoder output: swap to match URDF left/right
    out["lt"] = cur_B;            // left ticks  ← Motor B (physical left)
    out["rt"] = cur_A;            // right ticks ← Motor A (physical right)
    out["lv"] = serialized(String(current_vel_B, 4));   // left  velocity
    out["rv"] = serialized(String(current_vel_A, 4));   // right velocity
    out["dt"] = (int)elapsed;     // actual loop time (ms)

    serializeJson(out, Serial);
    Serial.println();
  }
}
