#include <SPI.h>

int SHUTDOWN_IND_PIN = 23;
int POWER_BUTTON_PIN = 13;

int messageReading = 0;


void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);

  SPI.end();

  pinMode(SHUTDOWN_IND_PIN,INPUT);
  pinMode(POWER_BUTTON_PIN,OUTPUT);

}

void loop() {
  // put your main code here, to run repeatedly:

  Serial.println(digitalRead(SHUTDOWN_IND_PIN));

  if (Serial.available() > 0) {
    char receivedChar = Serial.read(); // Read a single character
    if (receivedChar == ':'){
      messageReading = 1;
    } else if (messageReading == 1){
      if (receivedChar == 'P'){
        
        pinMode(POWER_BUTTON_PIN,OUTPUT);
        digitalWrite(POWER_BUTTON_PIN, LOW);
        Serial.println("Setting Pin D13 Low");



        messageReading = 0;
        delay(100);
        pinMode(POWER_BUTTON_PIN,INPUT);
        Serial.println("Setting Pin D13 to Input");

      } 

    }
  }

}
