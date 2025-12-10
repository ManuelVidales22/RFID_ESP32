#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============================================
// CONFIGURACIÓN WIFI - RED REAL
// ============================================
const char* ssid = "ESP32-RFID";          // Nombre del WiFi que TIENES
const char* password = "12345678";        // Contraseña del WiFi

// Dirección del servidor (CAMBIAR según PC que uses)
const char* serverUrl = "http://10.74.67.178:5000/api/rfid"; // IP del PC con Flask

// ============================================
// CONFIGURACIÓN RFID Y LEDs
// ============================================
#define SS_PIN    8    // GPIO8 -> SDA/SS
#define RST_PIN   4    // GPIO4 -> RST
#define LED_WIFI  2    // GPIO2 - LED onboard azul
#define LED_RFID  13   // GPIO13 - LED para lectura (opcional)

MFRC522 mfrc522(SS_PIN, RST_PIN);

// ============================================
// VARIABLES GLOBALES
// ============================================
unsigned long lastReadTime = 0;
const unsigned long READ_INTERVAL = 3000; // 3 segundos entre lecturas

// ============================================
// CONEXIÓN WIFI AUTOMÁTICA AL ENCENDER
// ============================================
void connectToWiFi() {
    Serial.print("📡 Conectando a: ");
    Serial.println(ssid);
    
    // Configurar WiFi
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    
    // LED parpadea rápido mientras conecta
    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - startTime) < 15000) {
        digitalWrite(LED_WIFI, !digitalRead(LED_WIFI));
        delay(250);
        Serial.print(".");
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        digitalWrite(LED_WIFI, HIGH); // LED fijo = CONECTADO
        Serial.println("\n✅ WiFi CONECTADO!");
        Serial.print("📶 IP Local: ");
        Serial.println(WiFi.localIP());
        Serial.print("📡 RSSI: ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");
    } else {
        Serial.println("\n❌ FALLO WiFi");
        Serial.println("   El ESP32 se reiniciará en 5s...");
        digitalWrite(LED_WIFI, LOW);
        delay(5000);
        ESP.restart(); // Reinicia para intentar nuevamente
    }
}

// ============================================
// ENVÍO DE DATOS RFID AL SERVIDOR
// ============================================
bool sendRFIDData(String uidHex, String uidDec) {
    // Verificar conexión WiFi
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("⚠️  WiFi desconectado");
        digitalWrite(LED_WIFI, LOW);
        return false;
    }
    
    // Crear cliente HTTP
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000); // Timeout de 5 segundos
    
    // Crear JSON
    DynamicJsonDocument doc(256);
    doc["uid_hex"] = uidHex;
    doc["uid_dec"] = uidDec;
    doc["device"] = "ESP32-S3";
    doc["timestamp"] = millis() / 1000;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Mostrar info de envío
    Serial.println("\n📤 ENVIANDO DATOS:");
    Serial.print("   Destino: ");
    Serial.println(serverUrl);
    Serial.print("   Datos: ");
    Serial.println(jsonString);
    
    // Enviar POST
    int httpCode = http.POST(jsonString);
    
    // Procesar respuesta
    if (httpCode > 0) {
        if (httpCode == HTTP_CODE_OK) {
            String response = http.getString();
            Serial.print("✅ ÉXITO - Respuesta: ");
            Serial.println(response);
            http.end();
            
            // LED de RFID parpadea rápido (éxito)
            if (LED_RFID != -1) {
                digitalWrite(LED_RFID, HIGH);
                delay(100);
                digitalWrite(LED_RFID, LOW);
            }
            return true;
        } else {
            Serial.printf("⚠️  HTTP Code: %d\n", httpCode);
        }
    } else {
        Serial.printf("❌ Error HTTP: %s\n", http.errorToString(httpCode).c_str());
    }
    
    http.end();
    
    // LED de RFID parpadea lento (error)
    if (LED_RFID != -1) {
        for(int i = 0; i < 3; i++) {
            digitalWrite(LED_RFID, HIGH);
            delay(100);
            digitalWrite(LED_RFID, LOW);
            delay(100);
        }
    }
    
    return false;
}

// ============================================
// SETUP - EJECUTADO AL ENCENDER
// ============================================
void setup() {
    Serial.begin(115200);
    delay(1000); // Espera para estabilizar
    
    // Configurar LEDs
    pinMode(LED_WIFI, OUTPUT);
    pinMode(LED_RFID, OUTPUT);
    digitalWrite(LED_WIFI, LOW);
    digitalWrite(LED_RFID, LOW);
    
    // Secuencia de inicio
    Serial.println("\n\n" + String(80, '='));
    Serial.println("🚀 ESP32-S3 RFID CLIENT - INICIANDO");
    Serial.println(String(80, '='));
    
    // Parpadeo inicial de LEDs
    for(int i = 0; i < 3; i++) {
        digitalWrite(LED_WIFI, HIGH);
        digitalWrite(LED_RFID, HIGH);
        delay(200);
        digitalWrite(LED_WIFI, LOW);
        digitalWrite(LED_RFID, LOW);
        delay(200);
    }
    
    // CONEXIÓN AUTOMÁTICA A WIFI
    connectToWiFi();
    
    // Inicializar RFID
    SPI.begin();
    mfrc522.PCD_Init();
    
    // Verificar lector RFID
    byte version = mfrc522.PCD_ReadRegister(MFRC522::VersionReg);
    Serial.print("📟 Versión MFRC522: 0x");
    Serial.println(version, HEX);
    
    if (version == 0x00 || version == 0xFF) {
        Serial.println("❌ ERROR: Lector RFID NO detectado");
        Serial.println("   Verifica conexiones de pines:");
        Serial.println("   GPIO8 → SDA, GPIO4 → RST");
        Serial.println("   GPIO12 → SCK, GPIO11 → MOSI, GPIO13 → MISO");
        while(true); // Detener ejecución
    }
    
    Serial.println("\n🎫 SISTEMA LISTO");
    Serial.println(String(80, '='));
    Serial.println("📍 Acerca una tarjeta RFID al lector...");
    Serial.println(String(80, '=') + "\n");
}

// ============================================
// LOOP - EJECUTADO CONTINUAMENTE
// ============================================
void loop() {
    // Verificar WiFi cada 30 segundos
    static unsigned long lastWifiCheck = 0;
    if (millis() - lastWifiCheck > 30000) {
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("🔄 Reconectando WiFi...");
            digitalWrite(LED_WIFI, LOW);
            connectToWiFi();
        }
        lastWifiCheck = millis();
    }
    
    // LEER TARJETA RFID
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
        // Anti-rebote (3 segundos entre lecturas)
        if (millis() - lastReadTime < READ_INTERVAL) {
            mfrc522.PICC_HaltA();
            mfrc522.PCD_StopCrypto1();
            return;
        }
        
        lastReadTime = millis();
        
        // LED indica lectura
        if (LED_RFID != -1) {
            digitalWrite(LED_RFID, HIGH);
        }
        
        // EXTRAER UID HEX
        String uidHex = "";
        for (byte i = 0; i < mfrc522.uid.size; i++) {
            if (mfrc522.uid.uidByte[i] < 0x10) uidHex += "0";
            uidHex += String(mfrc522.uid.uidByte[i], HEX);
            if (i < mfrc522.uid.size - 1) uidHex += " ";
        }
        uidHex.toUpperCase();
        
        // EXTRAER UID DEC
        unsigned long uidDec = 0;
        for (byte i = 0; i < mfrc522.uid.size; i++) {
            uidDec = (uidDec << 8) | mfrc522.uid.uidByte[i];
        }
        
        // MOSTRAR EN MONITOR SERIAL
        Serial.println("\n" + String(40, '═'));
        Serial.println("🎫 TARJETA RFID DETECTADA");
        Serial.println(String(40, '═'));
        Serial.print("🔑 UID HEX: ");
        Serial.println(uidHex);
        Serial.print("🔢 UID DEC: ");
        Serial.println(uidDec);
        Serial.print("⏰ Hora: ");
        Serial.print(millis() / 1000);
        Serial.println(" segundos");
        
        // ENVIAR DATOS AL SERVIDOR
        bool success = sendRFIDData(uidHex, String(uidDec));
        
        if (success) {
            Serial.println("✅ Datos enviados al servidor");
        } else {
            Serial.println("❌ Error al enviar datos");
        }
        
        Serial.println(String(40, '═') + "\n");
        
        // Apagar LED RFID
        if (LED_RFID != -1) {
            digitalWrite(LED_RFID, LOW);
        }
        
        // Liberar tarjeta
        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
        
        delay(100); // Pequeña pausa
    }
    
    delay(50); // Delay para evitar sobrecarga
}