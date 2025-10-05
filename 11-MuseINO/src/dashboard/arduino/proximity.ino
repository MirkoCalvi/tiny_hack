// nicla_people_counter_tof_fomo_udp.ino (ToF-only + fallback count senza FOMO)
//
// - Soglie adattate: ENTER=550 mm, EXIT=700 mm
// - Modalità attuale: ToF-only (CONFIRM_MODE = None) -> conta sempre
// - Fallback: se in futuro usi OnDeviceFOMO ma il modello non è pronto, conta comunque
//
// Board: Arduino Nicla Vision (Arduino Mbed OS Nicla Boards)

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <VL53L1X.h>

#if defined(ARDUINO_ARCH_MBED)
  #include <mbed.h>
  #include <rtos.h>
  using rtos::Thread;
  using rtos::Mutex;
#else
  #warning "Questo sketch usa RTOS (Mbed). Su core non-Mbed disabilita il threading."
#endif

// ============================== CONFIG =======================================
namespace cfg {
  constexpr char WIFI_SSID[]   = "toolbox";
  constexpr char WIFI_PASS[]   = "Toolbox.Torino";
  const IPAddress SERVER_IP(10,100,18,17);
  constexpr uint16_t SERVER_PORT = 5005;
  constexpr uint16_t LOCAL_PORT  = 5006;
  constexpr char CAM_ID[]        = "nicla-01";

  constexpr uint8_t  TICK_HZ      = 10;
  constexpr uint8_t  TELEMETRY_HZ = 5;

  enum class ConfirmMode : uint8_t { None=0, OnDeviceFOMO=1 };
  // 🔴 Modalità corrente: SENZA FOMO → contiamo sempre con ToF
  constexpr ConfirmMode CONFIRM_MODE = ConfirmMode::None;

  // Soglie e tempi (tarati sul tuo log)
  constexpr int      ENTER_TH_MM      = 550;   // entra sotto ~55 cm
  constexpr int      EXIT_TH_MM       = 700;   // esce sopra ~70 cm (isteresi)
  constexpr uint32_t ENTER_HOLD_MS    = 200;
  constexpr uint32_t EXIT_HOLD_MS     = 400;
  constexpr uint32_t MISSING_TIMEOUT  = 1500;

  constexpr float    EMA_ALPHA        = 0.4f;

  // Parametri FOMO (lasciati per futuro uso)
  constexpr uint16_t FOMO_IMG_W      = 96;
  constexpr uint16_t FOMO_IMG_H      = 96;
  constexpr uint32_t FOMO_TIMEOUT_MS = 25000;
  constexpr float    FOMO_CONF_TH    = 0.70f;
  constexpr const char* FOMO_TARGET_LABEL = "person";
}

// ============================== HW: ToF ======================================
namespace hw {
  VL53L1X tof;

  bool begin_tof() {
    Wire1.begin();
    Wire1.setClock(400000);
    tof.setBus(&Wire1);
    if (!tof.init()) return false;
    tof.setDistanceMode(VL53L1X::Long);
    tof.setMeasurementTimingBudget(10000);
    tof.startContinuous(10);
    return true;
  }

  inline int read_tof_mm() { return (int)tof.read(); }
}

// ============================== NET: UDP =====================================
namespace net {
  WiFiUDP udp;
  unsigned long lastTickMs      = 0;
  unsigned long lastTelemetryMs = 0;
  const unsigned long tickPeriodMs      = 1000ul / cfg::TICK_HZ;
  const unsigned long telemetryPeriodMs = 1000ul / cfg::TELEMETRY_HZ;

  void connect_wifi() {
    if (WiFi.status() == WL_CONNECTED) return;
    Serial.print("[WiFi] Connecting to "); Serial.println(cfg::WIFI_SSID);
    WiFi.begin(cfg::WIFI_SSID, cfg::WIFI_PASS);
    const unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
      delay(200); Serial.print('.');
    }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("[WiFi] IP="); Serial.println(WiFi.localIP());
      udp.begin(cfg::LOCAL_PORT);
      Serial.print("[UDP] listening on "); Serial.println(cfg::LOCAL_PORT);
    } else {
      Serial.println("[WiFi] Connect timeout");
    }
  }

  int send_raw(const char* json, size_t len) {
    udp.beginPacket(cfg::SERVER_IP, cfg::SERVER_PORT);
    udp.write((const uint8_t*)json, len);
    return udp.endPacket();
  }
}

// ============================ VISION: FOMO (placeholder) =====================
namespace vision {
  struct Result { bool ok=false; float conf=0.f; };
  static bool s_model_ready = false;
  static volatile bool s_job_running = false;
  static volatile bool s_job_done    = false;
  static Result s_last;
#if defined(ARDUINO_ARCH_MBED)
  Thread s_worker(osPriorityNormal, 8 * 1024);
#endif

  bool begin() {
    // 🔧 Collega qui camera + runtime modello quando pronto
    s_model_ready = false;  // oggi non usiamo FOMO
    return s_model_ready;
  }
  bool is_ready() { return s_model_ready; }
  bool is_busy()  { return s_job_running; }

  // Stub per compatibilità
  bool start_async_once() { return false; }
  bool poll_result(Result* out) { (void)out; return false; }
}

// =============================== APP =========================================
namespace app {
  enum class State : uint8_t { IDLE=0, CANDIDATE=1, ACTIVE=2 };

  static State  sm = State::IDLE;
  static uint32_t t_enter = 0;
  static uint32_t t_lastSeen = 0;
  static uint32_t t_sessionStart = 0;
  static uint32_t t_candidateStart = 0;

  static uint32_t seq = 0;
  static uint32_t people_count = 0;
  static float    d_f = 0;

  void send_event(const char* ev, int tof_mm, uint32_t dwell_ms = 0, float fomo_conf = -1.f) {
    char buf[352];
    const double ts = millis() / 1000.0;
    size_t off = 0;

    off += snprintf(buf + off, sizeof(buf) - off,
      "{\"ts\":%.3f,\"seq\":%lu,\"cam_id\":\"%s\",\"event\":\"%s\",\"tof_mm\":%d",
      ts, (unsigned long)++seq, cfg::CAM_ID, ev, tof_mm);

    if (dwell_ms > 0) off += snprintf(buf + off, sizeof(buf) - off, ",\"dwell_ms\":%lu", (unsigned long)dwell_ms);
    if (fomo_conf >= 0.f) off += snprintf(buf + off, sizeof(buf) - off, ",\"fomo_conf\":%.3f", fomo_conf);
    off += snprintf(buf + off, sizeof(buf) - off, "}\n");

    net::send_raw(buf, off);
    Serial.print("[EVT] "); Serial.write(buf, off);
  }

  void send_telemetry(int tof_mm) {
    char buf[320];
    const double ts = millis() / 1000.0;
    const char* mode_str = (cfg::CONFIRM_MODE == cfg::ConfirmMode::None) ? "tof_only" : "tof+fomo";
    const bool fomo_ready = (cfg::CONFIRM_MODE != cfg::ConfirmMode::None) && vision::is_ready();
    const bool fomo_busy  = (cfg::CONFIRM_MODE != cfg::ConfirmMode::None) && vision::is_busy();

    const size_t n = snprintf(buf, sizeof(buf),
      "{\"ts\":%.3f,\"seq\":%lu,\"cam_id\":\"%s\",\"mode\":\"%s\",\"state\":%u,"
      "\"count\":%lu,\"tof_mm\":%d,\"fps\":%.1f,\"fomo_ready\":%s,\"fomo_busy\":%s}\n",
      ts, (unsigned long)++seq, cfg::CAM_ID, mode_str, (unsigned)sm,
      (unsigned long)people_count, tof_mm, (double)cfg::TELEMETRY_HZ,
      fomo_ready ? "true" : "false",
      fomo_busy  ? "true" : "false"
    );
    net::send_raw(buf, n);
    Serial.print("[HB ] "); Serial.write(buf, n);
  }

  void tick_logic() {
    const unsigned long now = millis();

    // ToF + filtro
    const int d = hw::read_tof_mm();
    if (d_f <= 0) d_f = (float)d;
    d_f = (1.0f - cfg::EMA_ALPHA) * d_f + cfg::EMA_ALPHA * (float)d;

    switch (sm) {
      case State::IDLE: {
        if (d_f > 0 && d_f < cfg::ENTER_TH_MM) {
          if (t_enter == 0) t_enter = now;
          if (now - t_enter >= cfg::ENTER_HOLD_MS) {
            t_lastSeen = now;
            t_enter = 0;
            send_event("prox_enter", (int)d_f);

            if (cfg::CONFIRM_MODE == cfg::ConfirmMode::OnDeviceFOMO && vision::is_ready()) {
              // (non usato ora) in futuro: candida e attendi FOMO
              sm = State::CANDIDATE;
              t_candidateStart = now;
              (void)vision::start_async_once();
            } else if (cfg::CONFIRM_MODE == cfg::ConfirmMode::OnDeviceFOMO && !vision::is_ready()) {
              // Fallback: FOMO non pronto → conta comunque
              Serial.println("[FOMO] Non pronto: procedo ToF-only (fallback).");
              sm = State::ACTIVE; t_sessionStart = now;
              send_event("fomo_skipped", (int)d_f);
              people_count++;  // ✅ conteggio in ingresso
            } else {
              // Modalità ToF-only (corrente)
              sm = State::ACTIVE; t_sessionStart = now;
              send_event("auto_confirmed", (int)d_f);
              people_count++;  // ✅ conteggio in ingresso
            }
          }
        } else {
          t_enter = 0;
        }
      } break;

      case State::CANDIDATE: {
        // (non usato in ToF-only) – lasciato per futuro uso col FOMO
        if (d_f > 0 && d_f < cfg::ENTER_TH_MM) t_lastSeen = now;

        vision::Result r{};
        if (vision::poll_result(&r)) {
          if (r.ok && r.conf >= cfg::FOMO_CONF_TH) {
            sm = State::ACTIVE; t_sessionStart = now;
            send_event("fomo_confirmed", (int)d_f, 0, r.conf);
            people_count++; // conteggio all'avvio sessione
          } else {
            send_event("fomo_rejected", (int)d_f, 0, r.conf);
            sm = State::IDLE;
          }
        }
        if (now - t_candidateStart > cfg::FOMO_TIMEOUT_MS || (now - t_lastSeen > cfg::MISSING_TIMEOUT)) {
          sm = State::IDLE;
        }
      } break;

      case State::ACTIVE: {
        static uint32_t t_exitStart = 0;
        if (d_f > cfg::EXIT_TH_MM || d_f <= 0) {
          if (t_exitStart == 0) t_exitStart = now;
          if (now - t_exitStart >= cfg::EXIT_HOLD_MS) {
            const uint32_t dwell = now - t_sessionStart;
            send_event("visit_end", (int)d_f, dwell);
            sm = State::IDLE;
            t_exitStart = 0;
          }
        } else {
          t_exitStart = 0;
          t_lastSeen = now;
        }
        if (now - t_lastSeen > cfg::MISSING_TIMEOUT) {
          const uint32_t dwell = now - t_sessionStart;
          send_event("visit_end", (int)d_f, dwell);
          sm = State::IDLE;
        }
      } break;
    }
  }
}

// ============================== ARDUINO ======================================
void setup() {
  Serial.begin(115200);
  delay(300);
  net::connect_wifi();

  if (!hw::begin_tof()) {
    Serial.println("[TOF] VL53L1X init FAILED"); while (1) delay(1000);
  }
  (void)vision::begin(); // oggi non usa FOMO (placeholder)
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    net::connect_wifi();
    if (WiFi.status() != WL_CONNECTED) { delay(100); return; }
  }

  const unsigned long now = millis();

  if (now - net::lastTickMs >= net::tickPeriodMs) {
    net::lastTickMs = now;
    app::tick_logic();
  }

  if (now - net::lastTelemetryMs >= net::telemetryPeriodMs) {
    net::lastTelemetryMs = now;
    app::send_telemetry((int)app::d_f);
  }

  delay(1);
}
