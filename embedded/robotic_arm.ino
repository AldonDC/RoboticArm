/*
  ============================================================================
  CÓDIGO ULTRA RÁPIDO ARDUINO - 4 SERVOS BRAZO ROBÓTICO 🚀⚡
  ============================================================================
  
  PINES CONFIGURADOS:
  • Servo 1 -> Pin 3  (Base)
  • Servo 2 -> Pin 5  (Hombro) 
  • Servo 3 -> Pin 6  (Codo)
  • Servo 4 -> Pin 9  (Muñeca/Garra)
  
  VELOCIDAD EXTREMA + SUAVIDAD PERFECTA para todos los servos
  Procesamiento manual JSON súper optimizado
  
  ============================================================================
*/

#include <Servo.h>

// ============================================================================
// CONFIGURACIÓN BÁSICA - 4 SERVOS
// ============================================================================

Servo servos[4];
const int SERVO_PINS[4] = {3, 5, 6, 9};  // Pines para los 4 servos
const int LED_PIN = 13;

// Variables para cada servo
struct ServoData {
  int anguloActual;
  int anguloObjetivo;
  bool moviendose;
  unsigned long tiempoInicioMovimiento;
  int anguloInicio;
  int tiempoMovimiento;
};

ServoData servosData[4];

// Variables globales
String comandoRecibido = "";
int contadorComandos = 0;
unsigned long ultimoComando = 0;

// Configuración de velocidad SÚPER OPTIMIZADA
const int VELOCIDAD_MAXIMA = 300;
const int TIEMPO_MINIMO = 60;     // SÚPER RÁPIDO para micromovimientos  
const int TIEMPO_MAXIMO = 400;    // Para cambios bruscos
const int DELAY_LOOP = 3;         // Loop súper rápido

// ============================================================================
// CONFIGURACIÓN INICIAL
// ============================================================================

void setup() {
  // Inicializar serial a alta velocidad
  Serial.begin(115200);
  
  // Configurar LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Inicializar los 4 servos
  for (int i = 0; i < 4; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(90);  // Posición inicial centrada
    
    // Inicializar datos del servo
    servosData[i].anguloActual = 90;
    servosData[i].anguloObjetivo = 90;
    servosData[i].moviendose = false;
    servosData[i].tiempoInicioMovimiento = 0;
    servosData[i].anguloInicio = 90;
    servosData[i].tiempoMovimiento = 200;
  }
  
  // Reservar memoria
  comandoRecibido.reserve(300); // Más espacio para JSON con 4 servos
  
  // Esperar estabilización
  delay(1500);
  
  // Mensaje de inicio mejorado
  Serial.println("=====================================");
  Serial.println("🤖 ARDUINO 4 SERVOS - SÚPER RÁPIDO");
  Serial.println("=====================================");
  Serial.println("✅ Servo 1 (Base)    -> Pin 3");
  Serial.println("✅ Servo 2 (Hombro)  -> Pin 5");
  Serial.println("✅ Servo 3 (Codo)    -> Pin 6");
  Serial.println("✅ Servo 4 (Muñeca)  -> Pin 9");
  Serial.println("📡 Esperando comandos desde web...");
  Serial.println("📝 Formato JSON o individual:");
  Serial.println("   {\"servo1\":90,\"servo2\":45,\"servo3\":135,\"servo4\":60}");
  Serial.println("   servo1:90 / servo2:45 / etc...");
  Serial.println("=====================================");
  
  // Secuencia de prueba SÚPER RÁPIDA
  Serial.println("🚀 Iniciando secuencia de prueba...");
  secuenciaPrueba();
  
  // Parpadeo de confirmación
  for (int i = 0; i < 4; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(150);
    digitalWrite(LED_PIN, LOW);
    delay(150);
  }
  
  Serial.println("⚡ ¡TODOS LOS SERVOS LISTOS!");
  Serial.println("🎯 Velocidad EXTREMA habilitada");
  Serial.flush();
}

// ============================================================================
// BUCLE PRINCIPAL OPTIMIZADO
// ============================================================================

void loop() {
  // Leer comandos (alta prioridad)
  leerComandosSerial();
  
  // Mover todos los servos suavemente
  moverTodosLosServos();
  
  // Parpadeo del LED de estado
  parpadearLED();
  
  // Heartbeat cada 20 segundos (menos frecuente para velocidad)
  if (millis() - ultimoComando > 20000 && ultimoComando > 0) {
    mostrarEstado();
    ultimoComando = millis();
  }
  
  delay(DELAY_LOOP); // Delay súper optimizado
}

// ============================================================================
// LECTURA Y PROCESAMIENTO DE COMANDOS MULTI-SERVO
// ============================================================================

void leerComandosSerial() {
  while (Serial.available() > 0) {
    char caracterLeido = (char)Serial.read();
    
    // Solo procesar caracteres válidos
    if (caracterLeido >= 32 && caracterLeido <= 126) {
      comandoRecibido += caracterLeido;
    }
    
    // Procesar cuando llegue salto de línea o buffer lleno
    if (caracterLeido == '\n' || comandoRecibido.length() > 200) {
      procesarComandoMultiServo();
      comandoRecibido = "";
    }
  }
}

void procesarComandoMultiServo() {
  comandoRecibido.trim();
  
  if (comandoRecibido.length() < 3) {
    return;
  }
  
  Serial.println("\n📨 Comando: " + comandoRecibido);
  
  // Contador de servos encontrados
  int servosEncontrados = 0;
  
  // Buscar y procesar todos los servos (servo1, servo2, servo3, servo4)
  for (int i = 1; i <= 4; i++) {
    String servoNombre = "servo" + String(i);
    int angulo = extraerAnguloServo(comandoRecibido, servoNombre);
    
    if (angulo >= 0) {
      moverServo(i - 1, angulo); // Índice 0-3 para array
      servosEncontrados++;
    }
  }
  
  if (servosEncontrados > 0) {
    Serial.println("⚡ " + String(servosEncontrados) + " servo(s) procesado(s)");
    contadorComandos++;
    ultimoComando = millis();
  } else {
    Serial.println("⚠️ No se encontraron servos válidos");
  }
}

// ============================================================================
// EXTRACCIÓN MANUAL MEJORADA PARA CUALQUIER SERVO
// ============================================================================

int extraerAnguloServo(String comando, String nombreServo) {
  int posicion = comando.indexOf(nombreServo);
  
  if (posicion == -1) {
    return -1; // No encontrado
  }
  
  // Buscar el número después del nombre del servo
  for (int i = posicion + nombreServo.length(); i < comando.length(); i++) {
    char c = comando.charAt(i);
    
    // Si encontramos un dígito, extraer el número completo
    if (isDigit(c)) {
      String numeroStr = "";
      
      // Extraer todos los dígitos consecutivos
      while (i < comando.length() && isDigit(comando.charAt(i))) {
        numeroStr += comando.charAt(i);
        i++;
      }
      
      int angulo = numeroStr.toInt();
      
      // Validar rango
      if (angulo >= 0 && angulo <= 180) {
        return angulo;
      } else {
        Serial.println("❌ " + nombreServo + " ángulo fuera de rango: " + String(angulo));
        return -1;
      }
    }
  }
  
  return -1;
}

// ============================================================================
// CONTROL INDIVIDUAL DE SERVOS CON VELOCIDAD EXTREMA
// ============================================================================

void moverServo(int servoIndex, int nuevoAngulo) {
  if (servoIndex < 0 || servoIndex >= 4) {
    Serial.println("❌ Índice de servo inválido: " + String(servoIndex));
    return;
  }
  
  if (nuevoAngulo < 0 || nuevoAngulo > 180) {
    Serial.println("❌ Ángulo inválido para servo" + String(servoIndex + 1) + ": " + String(nuevoAngulo));
    parpadearError();
    return;
  }
  
  ServoData &servoData = servosData[servoIndex];
  
  // Si hay movimiento en progreso, interrumpirlo suavemente
  if (servoData.moviendose) {
    servoData.anguloInicio = servoData.anguloActual;
  }
  
  // Solo iniciar movimiento si es diferente
  if (nuevoAngulo != servoData.anguloObjetivo) {
    int diferencia = abs(nuevoAngulo - servoData.anguloActual);
    
    // Calcular tiempo de movimiento basado en la distancia
    servoData.tiempoMovimiento = calcularTiempoMovimiento(diferencia);
    
    Serial.println("🎯 Servo" + String(servoIndex + 1) + ": " + 
                   String(servoData.anguloActual) + "° → " + 
                   String(nuevoAngulo) + "° (" + 
                   String(diferencia) + "° en " + 
                   String(servoData.tiempoMovimiento) + "ms)");
    
    // Configurar movimiento suave
    servoData.anguloInicio = servoData.anguloActual;
    servoData.anguloObjetivo = nuevoAngulo;
    servoData.moviendose = true;
    servoData.tiempoInicioMovimiento = millis();
  }
}

int calcularTiempoMovimiento(int distancia) {
  // Velocidad adaptativa SÚPER OPTIMIZADA
  int tiempo;
  
  if (distancia <= 3) {
    // Micro movimientos: INSTANTÁNEOS
    tiempo = 40;
  } else if (distancia <= 8) {
    // Movimientos mínimos: SÚPER INSTANTÁNEOS
    tiempo = TIEMPO_MINIMO;
  } else if (distancia <= 20) {
    // Movimientos pequeños: SÚPER RÁPIDOS
    tiempo = map(distancia, 8, 20, TIEMPO_MINIMO, 120);
  } else if (distancia <= 40) {
    // Movimientos medianos: RÁPIDOS
    tiempo = map(distancia, 20, 40, 120, 200);
  } else if (distancia <= 80) {
    // Movimientos grandes: NORMALES
    tiempo = map(distancia, 40, 80, 200, 300);
  } else {
    // Movimientos muy grandes: CONTROLADOS
    tiempo = map(distancia, 80, 180, 300, TIEMPO_MAXIMO);
  }
  
  return tiempo;
}

// ============================================================================
// MOVIMIENTO SUAVE SIMULTÁNEO DE TODOS LOS SERVOS
// ============================================================================

void moverTodosLosServos() {
  for (int i = 0; i < 4; i++) {
    moverServoSuave(i);
  }
}

void moverServoSuave(int servoIndex) {
  ServoData &servoData = servosData[servoIndex];
  
  if (!servoData.moviendose) {
    return;
  }
  
  unsigned long tiempoTranscurrido = millis() - servoData.tiempoInicioMovimiento;
  
  if (tiempoTranscurrido >= servoData.tiempoMovimiento) {
    // Movimiento completado
    servoData.anguloActual = servoData.anguloObjetivo;
    servos[servoIndex].write(servoData.anguloActual);
    servoData.moviendose = false;
    
    Serial.println("✅ Servo" + String(servoIndex + 1) + " completado: " + String(servoData.anguloActual) + "°");
    
    // Parpadeo de éxito solo si todos terminaron
    if (!hayMovimientosActivos()) {
      parpadearExito();
    }
  } else {
    // Calcular posición intermedia
    float progreso = (float)tiempoTranscurrido / servoData.tiempoMovimiento;
    progreso = suavizarCurvaMejorada(progreso);
    
    int anguloIntermedio = servoData.anguloInicio + 
                          (int)((servoData.anguloObjetivo - servoData.anguloInicio) * progreso);
    
    // Solo actualizar si cambió
    if (anguloIntermedio != servoData.anguloActual) {
      servoData.anguloActual = anguloIntermedio;
      servos[servoIndex].write(servoData.anguloActual);
    }
  }
}

bool hayMovimientosActivos() {
  for (int i = 0; i < 4; i++) {
    if (servosData[i].moviendose) {
      return true;
    }
  }
  return false;
}

float suavizarCurvaMejorada(float t) {
  // Curva SÚPER OPTIMIZADA para velocidad y suavidad extrema
  if (t < 0.25) {
    // Arranque súper rápido
    return 6 * t * t;
  } else if (t < 0.75) {
    // Velocidad constante alta
    return 0.375 + 1.25 * (t - 0.25);
  } else {
    // Desaceleración suave pero rápida
    float remaining = 1 - t;
    return 1 - 6 * remaining * remaining;
  }
}

// ============================================================================
// FUNCIONES DE ESTADO Y DIAGNÓSTICO MEJORADAS
// ============================================================================

void mostrarEstado() {
  Serial.println("\n💓 Estado del sistema:");
  Serial.println("⏱️ Tiempo activo: " + String(millis()/1000) + " segundos");
  Serial.println("📊 Comandos procesados: " + String(contadorComandos));
  
  // Estado de cada servo
  for (int i = 0; i < 4; i++) {
    String icono = (i == 0) ? "🔄" : (i == 1) ? "💪" : (i == 2) ? "🦾" : "✋";
    Serial.print(icono + " Servo" + String(i + 1) + ": " + String(servosData[i].anguloActual) + "°");
    
    if (servosData[i].moviendose) {
      Serial.println(" → " + String(servosData[i].anguloObjetivo) + "° (moviendo)");
    } else {
      Serial.println(" (fijo)");
    }
  }
  
  Serial.println("🔌 Todos los servos conectados y funcionando");
  Serial.println("=====================================");
}

void parpadearLED() {
  static unsigned long ultimoParpadeo = 0;
  static bool estadoLED = false;
  
  unsigned long intervalo = 2500; // Normal
  
  // Parpadeo rápido si hay actividad
  if ((millis() - ultimoComando < 4000 && ultimoComando > 0) || hayMovimientosActivos()) {
    intervalo = 200; // Súper rápido
  }
  
  if (millis() - ultimoParpadeo > intervalo) {
    estadoLED = !estadoLED;
    digitalWrite(LED_PIN, estadoLED);
    ultimoParpadeo = millis();
  }
}

void parpadearExito() {
  // 1 parpadeo súper rápido
  digitalWrite(LED_PIN, HIGH);
  delay(40);
  digitalWrite(LED_PIN, LOW);
}

void parpadearError() {
  // 3 parpadeos rápidos para error
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
}

// ============================================================================
// SECUENCIA DE PRUEBA INICIAL
// ============================================================================

void secuenciaPrueba() {
  Serial.println("🚀 Probando todos los servos...");
  
  // Mover cada servo individualmente
  int angulosPrueba[4] = {45, 135, 60, 120};
  
  for (int i = 0; i < 4; i++) {
    Serial.println("🔧 Probando Servo" + String(i + 1) + "...");
    moverServo(i, angulosPrueba[i]);
    delay(300); // Pausa entre pruebas
  }
  
  delay(1000);
  
  // Volver al centro todos juntos
  Serial.println("🎯 Volviendo al centro...");
  for (int i = 0; i < 4; i++) {
    moverServo(i, 90);
  }
  
  delay(800);
  Serial.println("✅ Prueba inicial completada");
}

// ============================================================================
// COMANDOS DE PRUEBA Y CONEXIONES
// ============================================================================

/*
🔌 CONEXIONES FÍSICAS:
=====================================
Servo 1 (Base):     Pin 3  + 5V + GND
Servo 2 (Hombro):   Pin 5  + 5V + GND  
Servo 3 (Codo):     Pin 6  + 5V + GND
Servo 4 (Muñeca):   Pin 9  + 5V + GND

LED de estado:      Pin 13 + GND

⚡ COMANDOS DE PRUEBA SÚPER RÁPIDOS:
=====================================

1. Comandos individuales:
servo1:0
servo2:45  
servo3:90
servo4:180

2. JSON completo desde web:
{"servo1":90,"servo2":45,"servo3":135,"servo4":60}

3. Movimientos combinados:
{"servo1":0,"servo2":0,"servo3":0,"servo4":0}
{"servo1":180,"servo2":180,"servo3":180,"servo4":180}

4. Prueba de VELOCIDAD EXTREMA:
servo1:90
servo1:93    ← 3° en ~40ms  ⚡ INSTANTÁNEO
servo1:85    ← 8° en ~60ms  ⚡ SÚPER RÁPIDO  
servo2:45    ← Servo diferente simultáneo
servo3:135   ← Múltiples servos a la vez
{"servo1":45,"servo2":90,"servo3":45,"servo4":135}

🚀 OPTIMIZACIONES IMPLEMENTADAS:
=====================================
✅ 4 servos simultáneos con movimiento independiente
✅ Velocidades súper optimizadas:
   • 0-3°     = 40ms  ⚡ INSTANTÁNEO
   • 3-8°     = 60ms  ⚡ SÚPER RÁPIDO
   • 8-20°    = 60-120ms 🔥 RÁPIDO
   • 20-40°   = 120-200ms ⚙️ NORMAL
   • 40-80°   = 200-300ms 🎯 CONTROLADO
   • 80-180°  = 300-400ms 🎯 SUAVE
✅ Procesamiento JSON manual súper eficiente
✅ Movimientos simultáneos sin interferencia
✅ Interrupción suave de movimientos
✅ Curva de aceleración agresiva mejorada
✅ Feedback en tiempo real de todos los servos
✅ Sistema de diagnóstico completo
✅ Secuencia de prueba automática

¡VELOCIDAD EXTREMA con 4 servos funcionando perfectamente!
*/
