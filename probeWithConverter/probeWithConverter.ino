/***************************************************
  This is a library example for the MLX90614 Temp Sensor

  Designed specifically to work with the MLX90614 sensors in the
  adafruit shop
  ----> https://www.adafruit.com/products/1747 3V version
  ----> https://www.adafruit.com/products/1748 5V version

  These sensors use I2C to communicate, 2 pins are required to
  interface
  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit Industries.
  BSD license, all text above must be included in any redistribution
 ****************************************************/

#include <Adafruit_MLX90614.h>

Adafruit_MLX90614 mlx = Adafruit_MLX90614();
int messageReading = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  Serial.println("Adafruit MLX90614 test");

  if (!mlx.begin()) {
    Serial.println("Error connecting to MLX sensor. Check wiring.");
    while (1);
  };
  if (!ina260.begin(0x18)) {
    Serial.println("Couldn't find INA260 chip");
    while (1);
  }
  Serial.println("Found INA260 chip");

  if (!tempsensor.begin(0x18)) {
    Serial.println("Couldn't find MCP9808! Check your connections and verify the address is correct.");
    while (1);
  }

  tempsensor.setResolution(1);
  tempsensor.wake();


  
}

void loop() {

  if (Serial.available() > 0) {
    char receivedChar = Serial.read(); // Read a single character
    if (receivedChar == ':'){
      messageReading = 1;
    } else if (messageReading == 1){
      if (receivedChar == 'T'){
        Serial.print(":M:"); 
        Serial.print(mlx.readAmbientTempF());
        Serial.print(",");
        Serial.print(mlx.readObjectTempF()); 
        Serial.print(",");
        
        Serial.print(tempsensor.readTempF());
        Serial.print(",");

        Serial.print(ina260.readBusVoltage());
        Serial.print(",");

        Serial.print(ina260.readCurrent());
        Serial.print(",");

        Serial.println(ina260.readPower());

        messageReading = 0;
      }
    }
  }

}
