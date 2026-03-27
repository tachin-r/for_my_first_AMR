# ====== รันใน Google Colab: copy ทั้งหมดใส่ 1 cell แล้วกด Run ======
# %matplotlib inline   ← ถ้า plot ไม่ขึ้น ให้เอา # หน้าบรรทัดนี้ออก

"""
PID Response Simulation — AMR Motor Controller
================================================
จำลอง PID Controller เดียวกับ ESP32 firmware (Kp=400, Ki=50, Kd=2)
"""
import matplotlib
matplotlib.rcParams['figure.figsize'] = (12, 7)
import matplotlib.pyplot as plt
import numpy as np

# === PID Parameters (same as ESP32 firmware: main.cpp) ===
KP = 400.0
KI = 50.0
KD = 2.0
PID_LOOP_MS = 50      # 20 Hz control loop
MAX_PWM = 250
MIN_START_PWM = 120   # dead-zone kickstart

# === Motor Physical Model (approximation from real robot) ===
MOTOR_GAIN = 0.0028   # m/s per PWM unit
MOTOR_TAU = 0.15      # time constant (seconds) — motor + gearbox inertia
FRICTION_PWM = 50     # PWM threshold to overcome static friction
NOISE_STD = 0.005     # sensor noise (m/s)

def target_profile(t):
    """Step changes in target velocity — simulates typical usage."""
    if t < 0.5:
        return 0.0
    elif t < 3.0:
        return 0.15    # forward 0.15 m/s
    elif t < 3.5:
        return 0.0     # stop
    elif t < 5.5:
        return 0.25    # forward faster 0.25 m/s
    elif t < 6.0:
        return 0.0     # stop
    elif t < 7.5:
        return -0.10   # reverse
    else:
        return 0.0

def simulate_pid(dt=0.05, duration=8.0):
    """Simulate PID controller with first-order motor model."""
    steps = int(duration / dt)

    # State variables
    actual_vel = 0.0
    integral = 0.0
    prev_err = 0.0

    times, targets, actuals, pwms = [], [], [], []

    for i in range(steps):
        t = i * dt
        target = target_profile(t)

        # --- PID computation (identical to ESP32 firmware) ---
        if abs(target) < 0.001:
            integral = 0.0
            prev_err = 0.0
            pwm = 0
        else:
            err = target - actual_vel
            integral += err * dt

            # Anti-windup
            integ_limit = 200.0 / (KI + 1e-6)
            integral = max(-integ_limit, min(integ_limit, integral))

            derivative = (err - prev_err) / dt
            prev_err = err

            output = KP * err + KI * integral + KD * derivative

            sign = 1 if output >= 0 else -1
            mag = min(int(abs(output)), MAX_PWM)

            # Dead-zone kickstart
            if 0 < mag < MIN_START_PWM:
                mag = MIN_START_PWM

            pwm = sign * mag

        # --- Motor model (first-order + friction + noise) ---
        effective_force = pwm * MOTOR_GAIN if abs(pwm) >= FRICTION_PWM else 0
        actual_vel += (effective_force - actual_vel) / MOTOR_TAU * dt
        measured_vel = actual_vel + np.random.normal(0, NOISE_STD)

        times.append(t)
        targets.append(target)
        actuals.append(measured_vel)
        pwms.append(pwm)

    return times, targets, actuals, pwms

# === Run ===
np.random.seed(42)
times, targets, actuals, pwms = simulate_pid()

# === Plot ===
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7),
                                gridspec_kw={'height_ratios': [3, 1]})
fig.suptitle('PID Velocity Controller Response — AMR Motor',
             fontsize=16, fontweight='bold')

# --- Velocity ---
ax1.plot(times, targets, 'r--', linewidth=2.5, label='Target Velocity', alpha=0.9)
ax1.plot(times, actuals, 'b-',  linewidth=1.5, label='Actual Velocity',  alpha=0.8)
ax1.set_ylabel('Velocity (m/s)', fontsize=13)
ax1.legend(fontsize=12, loc='upper right')
ax1.grid(True, alpha=0.3)
ax1.set_xlim(0, 8)
ax1.axhline(y=0, color='gray', linewidth=0.5)

# Annotations
ax1.annotate('Step: 0→0.15 m/s', xy=(0.5, 0.15), xytext=(1.0, 0.22),
             fontsize=10, arrowprops=dict(arrowstyle='->', color='gray'), color='gray')
ax1.annotate('Step: 0→0.25 m/s', xy=(3.5, 0.25), xytext=(4.0, 0.32),
             fontsize=10, arrowprops=dict(arrowstyle='->', color='gray'), color='gray')
ax1.annotate('Reverse: -0.10 m/s', xy=(6.0, -0.10), xytext=(6.5, -0.18),
             fontsize=10, arrowprops=dict(arrowstyle='->', color='gray'), color='gray')

# Info box
info = (f'PID: Kp={KP:.0f}  Ki={KI:.0f}  Kd={KD:.0f}\n'
        f'Loop: {1000/PID_LOOP_MS:.0f}Hz ({PID_LOOP_MS}ms)\n'
        f'Max PWM: {MAX_PWM}  Kickstart: {MIN_START_PWM}')
ax1.text(0.02, 0.97, info, transform=ax1.transAxes, fontsize=9,
         verticalalignment='top', family='monospace',
         bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# --- PWM ---
ax2.fill_between(times, pwms, 0, alpha=0.4, color='green')
ax2.plot(times, pwms, 'g-', linewidth=1, alpha=0.7, label='PWM Output')
ax2.set_ylabel('PWM', fontsize=13)
ax2.set_xlabel('Time (seconds)', fontsize=13)
ax2.legend(fontsize=11, loc='upper right')
ax2.grid(True, alpha=0.3)
ax2.set_xlim(0, 8)
ax2.set_ylim(-280, 280)
ax2.axhline(y=0, color='gray', linewidth=0.5)
ax2.axhline(y=MIN_START_PWM, color='orange', linewidth=0.8, linestyle=':',
            alpha=0.7)
ax2.axhline(y=-MIN_START_PWM, color='orange', linewidth=0.8, linestyle=':',
            alpha=0.7)

plt.tight_layout()
plt.savefig('pid_response_graph.png', dpi=200, bbox_inches='tight')
print("✅ Saved: pid_response_graph.png")
plt.show()

# --- Colab: โหลดไฟล์ PNG กลับเครื่อง ---
try:
    from google.colab import files
    files.download('pid_response_graph.png')
except ImportError:
    pass  # ไม่ได้รันใน Colab — ข้ามไป
