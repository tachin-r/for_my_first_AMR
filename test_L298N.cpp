// ==========================================
// กำหนดขาสำหรับ Motor A (ฝั่งซ้าย)
// ==========================================
const int ENA_PIN = 14; 
const int IN1_PIN = 26; 
const int IN2_PIN = 27; 
const int ENCA_A_PIN = 32; 
const int ENCA_B_PIN = 33; 

// ==========================================
// กำหนดขาสำหรับ Motor B (ฝั่งขวา)
// ==========================================
const int ENB_PIN = 21; 
const int IN3_PIN = 22; 
const int IN4_PIN = 23; 
const int ENCB_A_PIN = 19; 
const int ENCB_B_PIN = 18; 

// ตัวแปรเก็บค่าตำแหน่ง Encoder 
volatile long encoderPosA = 0;
volatile long encoderPosB = 0;

// *** เพิ่มบรรทัดนี้: ประกาศตัวแปร Mux สำหรับทำ Critical Section ของ ESP32 ***
portMUX_TYPE timerMux = portMUX_INITIALIZER_UNLOCKED;

// ==========================================
// ฟังก์ชัน Interrupt Service Routine (ISR)
// ==========================================
void IRAM_ATTR readEncoderA() {
  if (digitalRead(ENCA_B_PIN) > 0) {
    encoderPosA++;
  } else {
    encoderPosA--;
  }
}

void IRAM_ATTR readEncoderB() {
  if (digitalRead(ENCB_B_PIN) > 0) {
    encoderPosB++;
  } else {
    encoderPosB--;
  }
}

void setup() {
  Serial.begin(115200);

  // ตั้งค่าขามอเตอร์
  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  // ตั้งค่าขา Encoder
  pinMode(ENCA_A_PIN, INPUT_PULLUP);
  pinMode(ENCA_B_PIN, INPUT_PULLUP);
  pinMode(ENCB_A_PIN, INPUT_PULLUP);
  pinMode(ENCB_B_PIN, INPUT_PULLUP);

  // ผูก Interrupt
  attachInterrupt(digitalPinToInterrupt(ENCA_A_PIN), readEncoderA, RISING);
  attachInterrupt(digitalPinToInterrupt(ENCB_A_PIN), readEncoderB, RISING);

  Serial.println("System Ready! Starting Motors...");
}

// ==========================================
// ฟังก์ชันสำหรับสั่งขับมอเตอร์
// ==========================================
void driveMotorA(int speed) {
  if (speed > 0) {
    digitalWrite(IN1_PIN, HIGH);
    digitalWrite(IN2_PIN, LOW);
    analogWrite(ENA_PIN, speed);
  } else if (speed < 0) {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, HIGH);
    analogWrite(ENA_PIN, -speed); 
  } else {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, LOW);
    analogWrite(ENA_PIN, 0); 
  }
}

void driveMotorB(int speed) {
  if (speed > 0) {
    digitalWrite(IN3_PIN, HIGH);
    digitalWrite(IN4_PIN, LOW);
    analogWrite(ENB_PIN, speed);
  } else if (speed < 0) {
    digitalWrite(IN3_PIN, LOW);
    digitalWrite(IN4_PIN, HIGH);
    analogWrite(ENB_PIN, -speed);
  } else {
    digitalWrite(IN3_PIN, LOW);
    digitalWrite(IN4_PIN, LOW);
    analogWrite(ENB_PIN, 0);
  }
}

void loop() {
  // 1. สั่งมอเตอร์เดินหน้า
  driveMotorA(128);
  driveMotorB(128);

  // 2. อ่านค่า Encoder อย่างปลอดภัย
  long currentPosA = 0;
  long currentPosB = 0;
  
  // *** เรียกใช้งาน timerMux เพื่อบล็อก Interrupt ชั่วขณะตอนอ่านค่า ***
  portENTER_CRITICAL(&timerMux); 
  currentPosA = encoderPosA;
  currentPosB = encoderPosB;
  portEXIT_CRITICAL(&timerMux);  

  // 3. ปริ้นท์ค่าลง Serial Monitor
  Serial.print("Encoder A: ");
  Serial.print(currentPosA);
  Serial.print(" | Encoder B: ");
  Serial.println(currentPosB);

  delay(100); 
}