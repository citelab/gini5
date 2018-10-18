/*
 * NAME: wirelessphy.c 
 * FUNCTION: Collection of functions implements the basic functional physical
 *                    layer. 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  wirelessphy.c
//======================================================= 
  #include "wirelessphy.h"

//=======================================================
//       FUNCTION:   IniNodePhy
//======================================================= 
 void IniNodePhy(NodeType type) {
	int id;
	
	if (prog_verbosity_level()==1){
		printf("[IniNodePhy]:: Initializing basic functional physical layer ... ");
	}	
	//initialize the basic functional physical layer.
	for (id = 1; id<=TotNodeNo; id++) {
	      if (type == NORMAL) {
               //allocate store space
			   WGNnode(id)->nodePhy = (NodePhy *)malloc(sizeof(NodePhy));
 	           WGNnode(id)->nodePhy->phyMib = (PhyMib *)malloc(sizeof(PhyMib));	   
	           //set value
	           (WGNnode(id)->nodePhy->phyMib) = SYS_INFO->phy_info;
          }
    }
	if (prog_verbosity_level()==1){
		printf("[ OK ]\n");
	}

    //initialize the attached modules (component).
	if (prog_verbosity_level()==2){
		PrintSystemInfo ("Initializing the physical layer modules ... ");
	}	
	IniNodeWirelessCard(NORMAL);
	IniNodeEnergy(NORMAL);
	IniNodeAntenna(NORMAL);
	IniNodeMobility(NORMAL);	
 }

//=======================================================
//       FUNCTION:   FinalizeNodePhy
//======================================================= 
 void FinalizeNodePhy(NodeType type) {
	int id;
	
    //finalize the atttached modules
	if (prog_verbosity_level()==2){
		PrintSystemInfo ("Finalizing the physical layer modules ... ");
	}	
	FinalizeNodeWirelessCard(NORMAL);
    FinalizeNodeEnergy(NORMAL);
    FinalizeNodeAntenna(NORMAL);	  
	FinalizeNodeMobility(NORMAL);
    
	//finalize the basic functional physical layer
	if (prog_verbosity_level()==1){
		printf("[FinalizeNodePhy]:: Finalizing basic functional physical layer ... ");
	}			
	for (id = 1; id<=TotNodeNo ; id++) {
	      if (type == NORMAL) {
			   free(WGNnode(id)->nodePhy);
          }
    }
	if (prog_verbosity_level()==1){
	    printf("[ OK ]\n");
	}
 }

//=======================================================
//       FUNCTION:   PhyProcess
//======================================================= 
  void PhyProcess() {
  }

//=======================================================
//       FUNCTION:   GetTxPwr			(db)
//======================================================= 
  double GetTxPwr(MobileNode *node) {
      return WToDB(node->nodePhy->nodeWCard->Pt);
  }

//=======================================================
//       FUNCTION:   SetPktTxPwr		 (db)
//======================================================= 
  void SetPktTxPwr(WGN_802_11_Mac_Frame *frame, double tx_pwr) {
      frame->pseudo_header->tx_pwr = tx_pwr;
  }

//=======================================================
//       FUNCTION:  GetRxPower        (db)
//       PURPOSE:   Compute the received power of the packet.
//======================================================= 
double  GetRxPwr( MobileNode *tx, MobileNode *rx ) {
	if ( GetRayleighSign() == OFF ) {  
	   return(PathLoss( tx, rx ));
	}
	else if ( GetRayleighSign() == ON ) {  
		//note that RayleighFad(node,ap)
	   if (tx->nodeType == NORMAL) {
		  return (PathLoss( tx, rx ) + RayleighFad( tx, rx ));
	   }
	}
    printf ("[ChannelRxPower]:: Unrecognized Fading type.\n");
	exit (1);
}

//=======================================================
//       FUNCTION:   SetPktRxPwr    (db)   
//       NOTE:           should be operated after SetPktTxPwr()	
//======================================================= 
  void SetPktRxPwr(WGN_802_11_Mac_Frame *frame, double rx_pwr) {
      frame->pseudo_header->rx_pwr = rx_pwr;
  }

//=======================================================
//       FUNCTION:   GetPktRxPwr    (db)   
//       NOTE:           should be operated after SetPktTxPwr()	
//======================================================= 
  double GetPktRxPwr(WGN_802_11_Mac_Frame *frame) {
      return (frame->pseudo_header->rx_pwr);
  }

//=======================================================
//       FUNCTION:  PhyUpPortSend  
//=======================================================
void PhyUpPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame) {
	verbose(4, "[PhyUpPortSend]:: NODE %d: PHY layer sends a packet to MAC layer.", node->Id);
    MacDownPortRecv(node, frame);
}

//=======================================================
//       FUNCTION:  PhyUpPortRecv  
//=======================================================
void PhyUpPortRecv(MobileNode *node,WGN_802_11_Mac_Frame *frame) {
	verbose(4, "[PhyUpPortRecv]:: NODE %d: PHY layer receives a packet from MAC layer.", node->Id);
	PhyDownPortSend(node, frame);
}

//=======================================================
//       FUNCTION:  PhyDownPortSend  
//=======================================================
   void PhyDownPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
	    int id;
		WGN_802_11_Mac_Frame *tmp_frame;

		//id is the identifier of the rx nodes
		for(id=1; id <= TotNodeNo; id++) { 
			  if(id != node->Id) {
				 //duplicate the frame.
		         tmp_frame = FrameDuplicate(frame);
				 //set the transmission rate.
				 tmp_frame->pseudo_header->signal = node->nodePhy->nodeWCard->bandwidth/100000;
				 ChannelDelivery(node->Id, id, tmp_frame);
			  } 
		}
	    verbose(4, "[PhyDownPortSend]:: NODE %d: PHY layer sends a packet to the channel.", node->Id);
   }

//=======================================================
//       FUNCTION:  PhyDownPortRecv  
//=======================================================
void PhyDownPortRecv(MobileNode *node,WGN_802_11_Mac_Frame *frame) {	
	verbose(4, "[PhyDownPortRecv]:: NODE %d: PHY layer receives a packet from the channel.", node->Id);
	PhyUpPortSend(node, frame);
}

//=======================================================
//       FUNCTION:  FrameDuplicate
//       PURPOSE:   
//=======================================================
   WGN_802_11_Mac_Frame *FrameDuplicate(WGN_802_11_Mac_Frame *frame) {
		 WGN_802_11_Mac_Frame *new_frame;

		 //initialize the new frame 
		 new_frame = (WGN_802_11_Mac_Frame *)malloc(sizeof(WGN_802_11_Mac_Frame));
		 new_frame->pseudo_header = (WGN_802_11_Mac_Pseudo_Header *)malloc(sizeof(WGN_802_11_Mac_Pseudo_Header));

		 //PLEASE NOTE: frame can be mac level or above level. for mac level frame, no frame boday
		 *(new_frame->pseudo_header) =  *(frame->pseudo_header);

		 if (frame->frame_body != NULL) {
			 new_frame->frame_body = (WGN_802_3_Mac_Frame *)malloc(sizeof(WGN_802_3_Mac_Frame));
			 new_frame->frame_body->data = (unsigned char*)malloc(sizeof(unsigned char)*frame->frame_body->payload_len);
			 new_frame->frame_body->payload_len = frame->frame_body->payload_len;
			 memcpy(&(new_frame->frame_body->header), &(frame->frame_body->header), DOT_3_HDR_LEN);
			 memcpy(new_frame->frame_body->data, frame->frame_body->data, frame->frame_body->payload_len);
		 }
		 else
			  new_frame->frame_body = NULL;

		  return (new_frame);		  
   }


//=======================================================
//       FUNCTION:   GetCSThreshold		
//======================================================= 
  double GetCSThreshold(MobileNode *node) {
       return (node->nodePhy->nodeWCard->CSThresh);
  }
 
 //=======================================================
//       FUNCTION:   GetRXThreshold		
//======================================================= 
  double GetRXThreshold(MobileNode *node) {
       return (node->nodePhy->nodeWCard->RXThresh);
  }

//=======================================================
//       FUNCTION:  IsOverRXThresh
//       PURPOSE:   Determine if the received power of the packet is 
//                              enough to be recoveried correctly
//======================================================= 
WGNflag IsOverRXThresh(double power, MobileNode *rx) { 
	if(power > GetRXThreshold(rx)) {
		return(TRUE);
	}
    else
		return(FALSE);
}

//=======================================================
//       FUNCTION:  IsOverCSThresh
//       PURPOSE:   Determine if the received power of the packet is 
//                              enough to be carrier sensed.
//======================================================= 
WGNflag IsOverCSThresh(double power, MobileNode *rx) {  
	if( power > GetCSThreshold(rx))
			return(TRUE);
    else
			return(FALSE);
}

//=======================================================
//       FUNCTION:   GetCapSign
//======================================================= 	
  Switch GetCapSign(MobileNode *node) {
     return(node->nodePhy->nodeWCard->capsign);
  }

//=======================================================
//       FUNCTION:   SetCapSign
//======================================================= 	
  void SetCapSign(MobileNode *node, Switch sign) {
     node->nodePhy->nodeWCard->capsign = sign;
  }
