#include "msbLib.h"
#define CAN0_MESSAGE_RAM_SIZE (0)
#define CAN1_MESSAGE_RAM_SIZE (1728)
#include <ACANFD_FeatherM4CAN.h>

static const long PERIOD = 1000 ;
static long gBlinkDate = PERIOD ; 

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

  // Incoming from MBS

  msb.msbLoop();

  if (msb.getQueueSize() > 0){

    canMsgStruct msbMsgStruct = msb.getMessageFromQueue();
    EntityEnum candes = msbMsgStruct.header.getDestination();
    MessageTypeEnum canmt = msbMsgStruct.header.getMessageType();
    EntityEnum cansend = msbMsgStruct.header.getSender();


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
