#include "msbLib.h"
#define CAN0_MESSAGE_RAM_SIZE (0)
#define CAN1_MESSAGE_RAM_SIZE (1728)
#include <ACANFD_FeatherM4CAN.h>

static const long PERIOD = 1000 ;
static long gBlinkDate = PERIOD ; 
int messageReading = 0;

MSBCANInterface msb;

void setup() {
  // put your setup code here, to run once:

  
  std::vector<EntityEnum> entityFilter = {EntityEnum::LAB_MONITOR,EntityEnum::ALL};
  msb.setup(entityFilter);

}

void loop() {
  // put your main code here, to run repeatedly:

  //******************************************************
  // Handling incoming messages and perform frequent tasks
  //******************************************************

  if (Serial.available() > 0) {
    char receivedChar = Serial.read(); // Read a single character
    if (receivedChar == ':'){
      messageReading = 1;
    } else if (messageReading == 1){
      if (receivedChar == 'D'){

        Serial.println("Trying to send shutdown command");

        messageReading = 0;
      } else if (receivedChar == 'U'){
        Serial.println("Trying to send start command");

        HeaderType outmsgHeader;
        outmsgHeader.setDestination(EntityEnum::ALL);
        outmsgHeader.setMessageType(MessageTypeEnum::SetEntityStateMDT);
        outmsgHeader.setSender(EntityEnum::LAB_MONITOR);
        
        SetEntityState outMsg;
        outMsg.setEntityID(EntityEnum::ALL);
        outMsg.setTargetState(EntityStateEnum::STARTING);

        Serial.println("    SetEntityStateMsg populated");

        canMsgStruct outSerial;
        outSerial.header = outmsgHeader;
        outSerial.msgFrame = outMsg.createNewMessage(outmsgHeader);
        
        uint32_t msbSendStatus = msb.sendMessage(outSerial.msgFrame);
        Serial.print("      MSB Sending Status: ");
        Serial.println(msbSendStatus);
  
      }

    }
  }

  // Incoming from MBS

  msb.msbLoop();

  if (msb.getQueueSize() > 0){

    Serial.println("Message Received");

    canMsgStruct msbMsgStruct = msb.getMessageFromQueue();
    EntityEnum candes = msbMsgStruct.header.getDestination();
    MessageTypeEnum canmt = msbMsgStruct.header.getMessageType();
    EntityEnum cansend = msbMsgStruct.header.getSender();

    Serial.print("      Message Type: ");
    Serial.println(getMessageTypeEnumString(canmt));


  }


  //******************************************************
  // Perform Periodic Tasks
  //******************************************************

  long currentTime = millis();
  if (gBlinkDate <= currentTime) {
    gBlinkDate += PERIOD ;

    // periodic stuff here

  }

  //******************************************************
  // Clear Outboxes
  //******************************************************


  

}
