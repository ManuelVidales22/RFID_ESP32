#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============================================
// CONFIGURACIÓN WIFI
// ============================================
const char* ssid = "MANUEL_ANTONIO";
const char* password = "6319142A";

// ============================================
// CONFIGURACIÓN SERVIDOR
// ============================================
const char* serverIP = "192.168.1.5";
const int serverPort = 5000;
const char* endpoint = "/api/rfid";

String serverURL = "http://" + String(serverIP) + ":" + String(serverPort) + endpoint;

// ============================================
// CONFIGURACIÓN RFID
// ============================================
#define SS_PIN    8    // GPIO8 -> SDA/SS
#define RST_PIN   4    // GPIO4 -> RST
#define SCK_PIN   12   // GPIO12 -> SCK
#define MOSI_PIN  11   // GPIO11 -> MOSI  
#define MISO_PIN  13   // GPIO13 -> MISO

MFRC522 mfrc522(SS_PIN, RST_PIN);

// ============================================
// SISTEMA ANTI-REBOTE
// ============================================
#define MIN_READ_INTERVAL 3000  // 3 segundos mínimo
unsigned long lastCardTime = 0;
String lastCardUID = "";

// ============================================
// DECLARACIÓN DE FUNCIONES (ARREGLO DEL ERROR)
// ============================================
void enviarDatos(String uidHex, String uidDec);

// ============================================
// SETUP
// ============================================
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("🚀 RFID SIMPLE - Solo UID HEX y DEC");
    
    // Iniciar SPI y RFID
    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);
    mfrc522.PCD_Init();
    
    // Conectar WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✅ WiFi Conectado");
    
    Serial.println("\n🎫 Acerca tarjeta/llavero...");
}

// ============================================
// FUNCIÓN: Enviar datos al servidor
// ============================================
void enviarDatos(String uidHex, String uidDec) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("❌ WiFi desconectado");
        return;
    }
    
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");
    
    // Solo UID HEX y DEC
    DynamicJsonDocument doc(128);
    doc["uid_hex"] = uidHex;
    doc["uid_dec"] = uidDec;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    Serial.print("📤 Enviando: ");
    Serial.println(jsonString);
    
    int httpCode = http.POST(jsonString);
    
    if (httpCode > 0) {
        Serial.print("📥 HTTP: ");
        Serial.println(httpCode);
        
        if (httpCode == HTTP_CODE_OK) {
            Serial.println("✅ Enviado correctamente");
        }
    } else {
        Serial.print("❌ Error: ");
        Serial.println(http.errorToString(httpCode));
    }
    
    http.end();
}

// ============================================
// LOOP PRINCIPAL
// ============================================
void loop() {
    // Verificar tarjeta
    if (!mfrc522.PICC_IsNewCardPresent()) {
        delay(50);
        return;
    }
    
    // Leer tarjeta
    if (!mfrc522.PICC_ReadCardSerial()) {
        return;
    }
    
    // Obtener UID HEX
    String uidHex = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        if (mfrc522.uid.uidByte[i] < 0x10) uidHex += "0";
        uidHex += String(mfrc522.uid.uidByte[i], HEX);
        if (i < mfrc522.uid.size - 1) uidHex += " ";
    }
    uidHex.toUpperCase();
    
    // Obtener UID DEC
    unsigned long uidDec = 0;
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        uidDec = uidDec << 8;
        uidDec |= mfrc522.uid.uidByte[i];
    }
    
    // Anti-rebote
    String currentUID = uidHex;
    unsigned long now = millis();
    
    if (currentUID == lastCardUID && (now - lastCardTime) < MIN_READ_INTERVAL) {
        Serial.println("⏭️  Ignorado (anti-rebote)");
        mfrc522.PICC_HaltA();
        return;
    }
    
    lastCardUID = currentUID;
    lastCardTime = now;
    
    // Mostrar en Serial
    Serial.println("\n════════════════════════════════");
    Serial.print("UID HEX: ");
    Serial.println(uidHex);
    Serial.print("UID DEC: ");
    Serial.println(uidDec);
    Serial.println("════════════════════════════════");
    
    // Enviar al servidor
    enviarDatos(uidHex, String(uidDec));
    
    // Detener tarjeta
    mfrc522.PICC_HaltA();
    delay(100);
}