/*
 * NAME: 802_11.c 
 * FUNCTION: Collection of functions that implement the IEEE 802.11 DCF module 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 * NOTE:   Some functions are implemented by taking ns-2 as reference.
 */

//=======================================================
//       File Name :  802_11.c
//======================================================= 
  #include "802_11.h"



char *MAC2Colon(char *buf, unsigned char mac_addr[])
{

        sprintf(buf, "%02x:%02x:%02x:%02x:%02x:%02x", mac_addr[0], mac_addr[1], mac_addr[2],
                mac_addr[3], mac_addr[4], mac_addr[5]);
        return buf;
}





//=======================================================
//       FUNCTION:   IniNodeMac
//======================================================= 
   void IniNodeS80211DcfMac(NodeType type) {
	   NodeId id;
	   if (prog_verbosity_level()==2){
           printf("[IniNodeS80211DcfMac]:: Initializing 802.11 dcf module ... ");
       }	
	   if (type == NORMAL) {
	       for (id=1; id<=TotNodeNo; id++) {
				  WGNnode(id)->nodeMac->cw = SYS_INFO->phy_info->CWMin;               
				  WGNnode(id)->nodeMac->short_retry_counter = 0;
	              WGNnode(id)->nodeMac->long_retry_counter = 0;
			      WGNnode(id)->nodeMac->pktRts = NULL;
	       }
	   }
	   if (prog_verbosity_level()==2){
		   printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTION:   FinalizeNodeS80211DcfMac
//======================================================= 
   void FinalizeNodeS80211DcfMac(NodeType type) {
	   NodeId id;
	   if (prog_verbosity_level()==2){
           printf("[FinalizeNodeS80211DcfMac]:: Finalizing 802.11 dcf module ... ");
       }	
	   if (type == NORMAL) {
	       for (id=1; id<=TotNodeNo; id++) {
				  if (WGNnode(id)->nodeMac->pktRts != NULL) {
			          Dot11FrameFree(WGNnode(id)->nodeMac->pktRts);
	              }	
	       }
	   }
	   if (prog_verbosity_level()==2){
		   printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTIONS:   GetSlotTime, GetSIFS, GetPIFS, GetDIFS, GetEIFS
//       PURPOSE:       Get the value of some time parameter.
//======================================================= 	
  double GetSlotTime() {
     return (SYS_INFO->phy_info->SlotTime);
  }

  double GetSIFS() {
     return (SYS_INFO->phy_info->SIFSTime);
  }

  double GetPIFS() {
     return (SYS_INFO->phy_info->PIFSTime);
  }
 	
  double GetDIFS() {
     return (SYS_INFO->phy_info->DIFSTime);
  }

  double GetEIFS() {
     return (SYS_INFO->phy_info->EIFSTime);
  }

//=======================================================
//       FUNCTION:   Update_cw
//       PURPOSE:    Update the contension window size
//======================================================= 	
    void Update_cw(MobileNode *node) {
        node->nodeMac->cw = (node->nodeMac->cw << 1) + 1;
        if (node->nodeMac->cw > SYS_INFO->phy_info->CWMax)  
		    node->nodeMac->cw = SYS_INFO->phy_info->CWMax;
    }

//=======================================================
//       FUNCTION:   Reset_cw
//       PURPOSE:    Reset the contension window size
//======================================================= 	
    void Reset_cw(MobileNode *node) {
        node->nodeMac->cw = SYS_INFO->phy_info->CWMin;
    }

//=======================================================
//       FUNCTION:   Set_Nav
//       PURPOSE:    Update the NAV process.
//======================================================= 	
    void Set_Nav(MobileNode *node, unsigned int duration_ns) {     
        WGNTime now;
        WGNTime new_nav;
		unsigned int time_dif;
		WGNflag flag;

		now = GetTime();
		new_nav = LocalTimeAdd(now, duration_ns);
		// if there is already a exiting NAV process, update the NAV ending time.
		if (Timer_SwitchSign(node, NAV_TIMER) == ON) {	
			time_dif = LocalTimeMinus(new_nav, node->nodeMac->nodeTimer->nav_timer->end_time);
		    //if the new NAV last longer than the current one
			if(time_dif > 0) {           
                NAVTimer_Stop(node);
				flag = EventDestroy(node->Id, NAVTimeOut);
			    if (flag == FALSE) {
				    printf("[Set_Nav]:: Error, Can not find the entry which will be destroyed!\n");
				    exit(1);
			    }
                NAVTimer_Start(node, duration_ns);
            }
		}
		//else create a new NAV process.
		else 
		   NAVTimer_Start(node, duration_ns);
		
		//The change of the NAV state can impact on the backoff process. 
		CheckBFTimer(node);
    }

//=======================================================
//       FUNCTION:   CheckIfChannelIdle								     
//       PURPOSE:    To check if the MAC status is IDLE.
//======================================================= 	
  WGNflag CheckIfChannelIdle(MobileNode *node) {
    if (node->nodeMac->txStatus != MAC_IDLE)
        return FALSE;
    if (node->nodeMac->rxStatus != MAC_IDLE)
        return FALSE;
    if (Timer_SwitchSign(node, NAV_TIMER) == ON)
        return FALSE;
    return TRUE;
  }

//=======================================================
//       FUNCTION:   CheckBFTimer		
//       PURPOSE:    Manage the state convert of the backoff timer
//======================================================= 
    void CheckBFTimer(MobileNode *node) {
		WGNflag flag;
		//Resume to the back off process once the channel becomes free.
        if ((CheckIfChannelIdle(node) == TRUE) && (Timer_PauseSign(node,BF_TIMER) == TRUE)) {
            BFTimer_Resume(node);
        } 
		//Stop the back off process once the channel becomes busy.
		if ((CheckIfChannelIdle(node) == FALSE) && (Timer_SwitchSign(node,BF_TIMER) == ON) && (Timer_PauseSign(node,BF_TIMER) == FALSE)) {
            BFTimer_Pause(node);
 			flag = EventDestroy(node->Id, BFTimeOut);
			if (flag == FALSE) {
				printf("[CheckBFTimer]:: Error, Can not find the entry which will be destroyed!\n");
				exit(1);
			}
        }
    }

//=======================================================
//       FUNCTION:   SetTxStatus
//       PURPOSE:    Set the transmission state
//======================================================= 	
  void SetTxStatus(MobileNode *node,MacStatus status) {
     node->nodeMac->txStatus = status;
	 //The change of the TX state can impact on the backoff process. 
	 CheckBFTimer(node);
  }

//=======================================================
//       FUNCTION:   SetRxStatus
//       PURPOSE:    Set the reception state
//======================================================= 	
  void SetRxStatus(MobileNode *node,MacStatus status) {
     node->nodeMac->rxStatus = status;
     //The change of the RX state can impact on the backoff process.
	 CheckBFTimer(node);
  }

//=======================================================
//       FUNCTION:   IsOverRTSThreshold        
//       PURPOSE:    To check if the RTS is needed
//======================================================= 
  WGNflag IsOverRTSThreshold(WGN_802_11_Mac_Frame* frame){
	  if (frame->pseudo_header->mac_size > SYS_INFO->mac_info->MAC_RTSThreshold)
	      return (TRUE);
	  else
          return (FALSE);
  }

//=======================================================
//       FUNCTIONS: @TimeoutHandler
//       PURPOSE:     Handle all kinds of MAC-level timeout event
//=======================================================  
  void BFTimeoutHandler(MobileNode *node) {  
     BFTimer_Stop(node);
	 // check whether there is some frame about to be transmitted.
     if ( node->nodeMac->pktRsp != NULL ) {
        return;
     } 		
     if (UpdateRtsBuf(node) == 0 )  {
        return;
     }
     if ( UpdateTxBuf(node) == 0 )   {
        return;
     }
  }

  void DFTimeoutHandler(MobileNode *node) {    
	 DFTimer_Stop(node);
	 // check whether there is some frame about to be transmitted.
	 if (UpdateRspBuf(node) == 0) {
        return;
        } 
     if (UpdateRtsBuf(node) == 0 )  {
        return;
     }
     if ( UpdateTxBuf(node) == 0 )   {
        return;
     }            
     tx_resume(node);      
  }
	
  void NAVTimeoutHandler(MobileNode *node) {    
	 NAVTimer_Stop(node);
	 CheckBFTimer(node);    
  }
	
  void IFTimeoutHandler(MobileNode *node) {   
     //NOTE: 
	 //TxActiveSign is different from txStatus!!!
     //TxActiveSign is only set for the time period of the frame transmission 
	 //delay while the txStatus will not stop untill the txtimeout event happens.
	 IFTimer_Stop(node);       
	 SetTxActiveSign(node,FALSE) ;   
  }

  void RXTimeoutHandler(MobileNode *node) {
     RXTimer_Stop(node);
     recv_timer(node);         
  }
    	
  void TXTimeoutHandler(MobileNode *node) {
     TXTimer_Stop(node);
     send_timer(node);       
  }

//=======================================================
//       FUNCTION:  tx_resume 
//       PURPOSE:   Resume to the transmission state
//======================================================= 	
  void tx_resume(MobileNode *node) {
	 unsigned int SIFS;
	 unsigned int DIFS;
     SIFS = SecToNsec(GetSIFS());
	 DIFS = SecToNsec(GetDIFS());

     // the node is in response state, so the bftimer can be 
	 // taken out of consideration.
     if ( node->nodeMac->pktRsp != NULL ) {
        //Need to send a CTS or ACK.   
        if(Timer_SwitchSign(node, DF_TIMER)==OFF)
           DFTimer_Start(node, SIFS);
     } 
     else if ( node->nodeMac->pktRts != NULL ) {
	    // If the backoff timer is off, it can be the following cases:
		//(1) no packet to send.
		//(2) in the first difs defer process.
		//(3) is sending packet now.
        if (Timer_SwitchSign(node, BF_TIMER)==OFF) {
            if(Timer_SwitchSign(node, DF_TIMER)==OFF)	   
               DFTimer_Start(node, DIFS); 
		}
     }  
	 else if ( node->nodeMac->pktTx != NULL ) { 
        if ( Timer_SwitchSign(node, BF_TIMER)==OFF) {
            if(Timer_SwitchSign(node, DF_TIMER)==OFF) {
               //This data frame is the beginning of the transmission (NOT attached with a RTS). 
               if ((IsOverRTSThreshold(node->nodeMac->pktTx) == FALSE) || (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE)) {
				  DFTimer_Start(node, DIFS);
               }
			   //This data frame is following the reception of CTS.
			   else 
			      DFTimer_Start(node, SIFS); 
			}
        }
     }
	 //Ask packet from the LLC layer.
     else {
        //If there is no frame waiting for transmission, set HasPkt to be FALSE.
		if (LlcDownPortSend(node) == FALSE) {
			node->nodeMac->HasPkt = FALSE;
		}
	 }
	 SetTxStatus(node,MAC_IDLE);
  }

//=======================================================
//       FUNCTION:  rx_resume 
//       PURPOSE:   Resume to receiving state
//======================================================= 	
  void rx_resume( MobileNode *node ) {
	 //If the total interference is less than the CS_threshold, the MAC state
	 //should be set to IDLE.
	 if (node->nodePhy->nodeAntenna->intPwr < GetCSThreshold(node)) {
         node->nodeMac->rxStatus = MAC_IDLE;
	 } 
	 else {
		 node->nodeMac->rxStatus = MAC_RECV;
	 } 
  }

//=======================================================
//       FUNCTIONS:  Update@Buf	     
//       PURPOSE:     Update All Kinds Of Buffers
//======================================================= 
  int UpdateRspBuf(MobileNode *node) {
   		WGN_802_11_Mac_Frame *frame;
        unsigned int timeout = 0;
		int subtype;

        if (PktRspIsEmpty(node) == TRUE)
            return -1;
        if (GetTxStatus(node)  == MAC_CTS || GetTxStatus(node)  == MAC_ACK)
            return -1;
        
		frame = node->nodeMac->pktRsp;
        subtype = GetFcSubtype (frame); 
        switch(subtype) {
            case MAC_SUBTYPE_CTS:
				if( CheckIfChannelIdle(node) == FALSE ) {
                    Dot11FrameFree(frame);                 
					node->nodeMac->pktRsp=NULL;
                    return 0;
                }
                SetTxStatus(node,MAC_CTS);
                //Set timeout period.
				timeout = UsecToNsec(GetDuration(frame))+ SecToNsec(CTS_Time);
                break;

            //IEEE 802.11 specs, section 9.2.8
            //Acknowledment should be sent after an SIFS, regardless to 
			//the busy/idle state of the medium.           
            case MAC_SUBTYPE_ACK:
				SetTxStatus(node,MAC_ACK);
                timeout = SecToNsec(ACK_Time);
                break;

            default:
				printf ("[UpdateRspBuf]:: Error, Invalid frame subtype!\n");
			    exit(1);
				break;
        }
          //printf("In UpdateRspBuf ..\n");
        MacSendPkt(node, frame, timeout);  
        return 0;
  }

  int UpdateRtsBuf(MobileNode *node){  	
		WGN_802_11_Mac_Frame *frame;
        unsigned int timeout = 0;
		int subtype;       
		
        if (PktRtsIsEmpty(node) == TRUE)
            return -1;
       frame =  node->nodeMac->pktRts;
	   subtype = GetFcSubtype (frame); 
       switch(subtype) {
            case MAC_SUBTYPE_RTS:
                if(CheckIfChannelIdle(node) == FALSE) {
                    Update_cw(node);
                    BFTimer_Start(node, FALSE);
                    return 0;
                }
                SetTxStatus(node,MAC_RTS);
                timeout = SecToNsec(Wait_CTS_Timeout);
                break;
            default:
				break;
        }
      //printf("In UpdateRtsBuf ..\n");
        MacSendPkt(node, frame, timeout); 
        return 0;
  }
    
  int UpdateTxBuf(MobileNode *node){  	
		WGN_802_11_Mac_Frame *frame;
        unsigned int timeout = 0;
		int subtype;       
		
		if (PktTxIsEmpty(node) == TRUE)
            return -1;
        
		frame =  node->nodeMac->pktTx;
		subtype = GetFcSubtype (frame);
		switch(subtype) {
            case MAC_SUBTYPE_DATA:
                if(CheckIfChannelIdle(node) == FALSE) {
                    SendRTS(node);		                           
					Update_cw(node);
                    BFTimer_Start(node, FALSE);
                    return 0;
                }
				SetTxStatus(node,MAC_SEND);
                if (CheckIfIsBroadCastPkt(frame) == FALSE)	 {
                    timeout = SecToNsec(GetWaitACKTimeout(node));
				}
                else					
                    timeout = SecToNsec(TX_Time(node));         
                break;
            default:
				printf ("[UpdateTxBuf]:: Error, Invalid frame subtype!\n");
			    exit(1);
                break;
        }
        //printf("In UpdateTxBuf ..\n");
        MacSendPkt(node, frame, timeout); 
        return 0;
  }

//=======================================================
//       FUNCTIONS:  Send@	     
//       PURPOSE:      Send different kinds of MAC-level frames
//======================================================= 
  void SendRTS(MobileNode *node) {
		unsigned char *ra;
		unsigned char *ta;	 

		//Create the RTS frame in the following cases:
        //(1) If the data frame size is larger than the RTS_threshold;
        //(2) If the data frame is a broadcast one;
        if ( IsOverRTSThreshold(node->nodeMac->pktTx) == FALSE || CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE ) {
            return;
        }  
		
		node->nodeStats->RtsTxed += 1;
		//Create a new RTS packet and put it inot the pktRts buffer
		ta = GetSa(node->nodeMac->pktTx);
		ra = GetDa(node->nodeMac->pktTx);
        Mac_802_11_RTS_Frame(node, ra, ta);
  }

  void SendCTS(MobileNode *node, WGN_802_11_Mac_Frame *RTS_frame)	{
        unsigned char *ra;
		unsigned int rts_duration;                    //micro seconds

	    node->nodeStats->CtsTxed += 1;
		ra = GetTa(RTS_frame);
		rts_duration = GetDuration(RTS_frame);
		Mac_802_11_CTS_Frame(node, rts_duration, ra);
  }

//=======================================================
//       FUNCTIONS:  CounterManagement     
//       PURPOSE:      Handle the operations for different kinds of counters
//                                 ShortRetryCounter / LongRetryCounter
//======================================================= 
  void UpdateSRCounter(MobileNode *node) {  
      node->nodeMac->short_retry_counter = node->nodeMac->short_retry_counter + 1;
  }  

  void UpdateLRCounter(MobileNode *node) {  
	  node->nodeMac->long_retry_counter = node->nodeMac->long_retry_counter + 1;
  } 

  void RstSRCounter(MobileNode *node) {  
	  node->nodeMac->short_retry_counter = 0;
  } 

  void RstLRCounter(MobileNode *node) {  
	  node->nodeMac->long_retry_counter = 0;
  }

  WGNflag SCounterIsOver(MobileNode *node) {  
       if (node->nodeMac->short_retry_counter >= node->nodeMac->macMib->MAC_ShortRetryLimit)
           return (TRUE);
       else 
           return (FALSE);
  }

  WGNflag LCounterIsOver(MobileNode *node) {  
	   if (node->nodeMac->long_retry_counter >= node->nodeMac->macMib->MAC_LongRetryLimit)
           return (TRUE);
       else 
           return (FALSE);
  }

//=======================================================
//       FUNCTIONS:  Retransmit@	     
//       PURPOSE:      Retransmit different kinds of frames
//======================================================= 
  void RetransmitRTS(MobileNode *node) {
        WGNflag idle;

        UpdateSRCounter(node);			
		
        if (SCounterIsOver(node) == TRUE) {     
			node->nodeStats->DropForExMaxRtsRetryNo += 1;
            Dot11FrameFree(node->nodeMac->pktRts);                                     
		    node->nodeMac->pktRts = NULL;
            Dot11FrameFree(node->nodeMac->pktTx);                                      
			node->nodeMac->pktTx = NULL;
            RstSRCounter(node);
            Reset_cw(node);
        } 
        else {
			node->nodeStats->ReTxRtsNum += 1;
			node->nodeStats->RtsTxed += 1;
            //Set the retry field in the pseudo header
            set_fc_retry(&(node->nodeMac->pktRts->pseudo_header->fc), 1);
            Update_cw(node);
            idle = CheckIfChannelIdle(node);
            BFTimer_Start(node,idle);
        }
  }
    
  void RetransmitData(MobileNode *node) {
        int rcount, thresh;
		WGNflag idle;
		WGNflag islargepkt;
        
		//Broadcast packets will never be retransmitted.  
        if (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE) {
			Dot11FrameFree(node->nodeMac->pktTx);
			node->nodeMac->pktTx = NULL;
            //reset the contension window but not double, because the previous 
			//broadcast packet will not be resent.
			Reset_cw(node);
			//because no ACK for the broadcast packet, always we treat it as a 
			//succesful transmission.
			BFTimer_Start(node, CheckIfChannelIdle(node));           
            return;
        }
		islargepkt = IsOverRTSThreshold(node->nodeMac->pktTx);
        if( islargepkt == FALSE) {
            UpdateSRCounter(node);
			rcount = node->nodeMac->short_retry_counter;
            thresh = node->nodeMac->macMib->MAC_ShortRetryLimit;
        }
        else {
            UpdateLRCounter(node);
			rcount = node->nodeMac->long_retry_counter;
			thresh = node->nodeMac->macMib->MAC_LongRetryLimit;
        }
        
		// Take a look at IEEE Spec section 9.2.3.5.
        if(rcount >= thresh) {
			node->nodeStats->DropForExMaxPktRetryNo += 1;
            Dot11FrameFree(node->nodeMac->pktTx);
			node->nodeMac->pktTx = NULL;
            if ( islargepkt == FALSE )
                RstSRCounter(node);
            else
                RstLRCounter(node);            
            Reset_cw(node);
        }
        else {
			node->nodeStats->ReTxPktNum += 1;
		    node->nodeStats->DataTxed += 1;
            set_fc_retry(&(node->nodeMac->pktTx->pseudo_header->fc), 1);
            SendRTS(node);
            Update_cw(node);
            idle = CheckIfChannelIdle(node);
            BFTimer_Start(node,idle);
        }
  }

//=======================================================
//       FUNCTION:  send_timer 	   
//       PURPOSE:   Called by the TXTimeoutHandler
//======================================================= 
  void send_timer (MobileNode *node) {
		switch(GetTxStatus(node)) {
            case MAC_RTS:  
              	//Waiting for the CTS.
                RetransmitRTS(node);
                break;
            case MAC_CTS:  
				//Waiting for the DATA.                
				Dot11FrameFree(node->nodeMac->pktRsp);
				node->nodeMac->pktRsp = NULL;
                break;
            case MAC_SEND: 
				//Waiting for the ACK.
                RetransmitData(node);
                break;
            case MAC_ACK:  
				// Sent an ACK, and now ready to resume transmission.
                Dot11FrameFree(node->nodeMac->pktRsp);
				node->nodeMac->pktRsp = NULL;
                break;
            default:
               printf("[send_timer]:: Error, Invalid mac state!\n");
			   exit(1);
        }
        tx_resume(node);			
  }

//=======================================================
//       FUNCTION:  recv_timer	 
//       PURPOSE:   Called by the RXTimeoutHandler
//======================================================= 
    void recv_timer(MobileNode *node) {
  		char *dst;
		unsigned duration_us;
        char tmpbuf[64];


		//If it is a MAC-level frame (RTS,CTS,ACK).
		if (node->nodeMac->pktRx->frame_body == NULL) {
            dst = GetRa(node->nodeMac->pktRx); 
            //printf("<<<< Got a Mac-Layer frame \n");
		}
		//If it is an ABOVE layer level frame (DATA). 
		else  
        {
			dst = GetDa(node->nodeMac->pktRx);
            //printf("<<<< Got a frame from the layer above \n");
        }
	    
		//If the frame arrives while the transmission, it can not be awared
		//by the node and should be dropped sliently. The EIFS deferral 
		//will not be activated because of the absence of the awareness 
		//for the erroneous received frame. 
        if (GetTxActiveSign(node) == TRUE) {
			node->nodeStats->DropForInTx += 1;
            Dot11FrameFree(node->nodeMac->pktRx);
			node->nodeMac->pktRx = NULL;
			//********************************FOR TEST ONLY***********************************//
			//if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
			    //PrintLine ();
			    //printf("NODE %d: PACKET HAS ERROR : RECV THE PACKET WHEN SENDING PACKET. DROPED.\n",node->Id);
                //PrintLine ();
			//}
			rx_resume(node);
			CheckBFTimer(node);
			return;
        }

		//Handle frame with receiving collision errors.
        if ( GetRxStatus(node) == MAC_COLL ) { 
			node->nodeStats->DropForCollision += 1;
			switch(GetFcSubtype(node->nodeMac->pktRx)) {
                  case MAC_SUBTYPE_RTS:
			     	    node->nodeStats->RtsDropForCollision += 1;
                        break;
                   case MAC_SUBTYPE_CTS:
					    node->nodeStats->CtsDropForCollision += 1;
                        break;
                   case MAC_SUBTYPE_ACK:
					    node->nodeStats->AckDropForCollision += 1;
                        break;
			       case MAC_SUBTYPE_DATA:
					    node->nodeStats->DataDropForCollision += 1;
                        break;
                   default:
                        printf("[recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
            }
			Dot11FrameFree(node->nodeMac->pktRx); 
			node->nodeMac->pktRx = NULL;
			//********************************FOR TEST ONLY***********************************//
			//if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
				//PrintLine ();
				//printf("NODE %d: PACKET HAS ERROR : COLLISION HAPPENED. DROPED.\n",node->Id);
				//PrintLine ();
			//}
			rx_resume(node);
            PktErrHandler(node); 
            return;
        }

        //Handle frame with power fading errors
        if( PktRxHasFadError(node) == TRUE ) {
			node->nodeStats->DropForLowRxPwr += 1;
			//********************************FOR TEST ONLY***********************************//
			//if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
			//	PrintLine ();
			//	printf("NODE %d: PACKET HAS ERROR : RECV POWER IS TOO LOW. DROPED.\n",node->Id);
			//	PrintLine ();
			//}
            Dot11FrameFree(node->nodeMac->pktRx);
			node->nodeMac->pktRx = NULL;
			rx_resume(node);
            PktErrHandler(node); 
            return;
        }
        
		//Handle frame with transmission collision errors.
        if( PktRxHasColError(node) == TRUE ) {
			node->nodeStats->DropForInTx += 1;
            Dot11FrameFree(node->nodeMac->pktRx);
			node->nodeMac->pktRx = NULL;
			//********************************FOR TEST ONLY***********************************//
			//if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
				//PrintLine ();
				//printf("NODE %d: PACKET HAS ERROR : RECV THE PACKET WHEN SENDING PACKET. DROPED.\n",node->Id);
				//PrintLine ();
			//}
			rx_resume(node);
            PktErrHandler(node); 		
		    return;
        }

		//Handle frame with awgn noise errors.
		if (PktRxHasNoiseError(node) == TRUE ) {
			node->nodeStats->DropForNoiseErr += 1;
            SetBFWaitTime(node, GetEIFS());
			Dot11FrameFree(node->nodeMac->pktRx);
			node->nodeMac->pktRx = NULL;
			//********************************FOR TEST ONLY***********************************//
			//if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
				//PrintLine ();
				//printf("NODE %d: PACKET HAS ERROR : THE PACKET HAS TOO MUCH NOISE. DROPED.\n",node->Id);
				//PrintLine ();
			//}
			rx_resume(node);
            PktErrHandler(node); 	            
			return;
		}
        
		// If the received frame is not addressed itself, update the NAV timer.
		// IEEE 802.11 specs, section 9.2.5.6
		if ((MacAddrIsSame(dst, node->nodeMac->mac_addr)) == FALSE) {
            //printf("Received frame is not addressed itself\n");
            duration_us = GetDuration(node->nodeMac->pktRx);
			Set_Nav(node, UsecToNsec(duration_us));
        }

        //printf("Dst MAC %s \n", MAC2Colon(tmpbuf, dst));
       //printf("Node MAC %s \n", MAC2Colon(tmpbuf, node->nodeMac->mac_addr));
        // If the received frame is neither addressed itself or a broadcast
		// frame, drop it.
        if(((MacAddrIsSame(dst, node->nodeMac->mac_addr)) == FALSE) && 
		   CheckIfIsBroadCastPkt(node->nodeMac->pktRx) == FALSE) {
		   node->nodeStats->NotForMeRxed += 1;
		   Dot11FrameFree(node->nodeMac->pktRx);
		   node->nodeMac->pktRx = NULL;
		   //********************************FOR TEST ONLY***********************************//
		   //PrintLine ();
		   //printf("NODE %d: PACKET IS NOT FOR ME. DROPED.\n",node->Id);
		   //PrintLine ();
           rx_resume(node);
           CheckBFTimer(node);
		   return;
        }
        
		switch(GetFctype(node->nodeMac->pktRx)) {
            case MAC_TYPE_MANAGEMENT:
				printf("[recv_timer]:: MAC_TYPE_MANAGEMENT type is not implemented now!\n");
			    break;              
            case MAC_TYPE_CONTROL:
                switch(GetFcSubtype(node->nodeMac->pktRx)) {
                    case MAC_SUBTYPE_RTS:
					    node->nodeStats->RtsRxed += 1;
                        recvRTS(node);
                        break;
                    case MAC_SUBTYPE_CTS:
					    node->nodeStats->CtsRxed += 1;
                        recvCTS(node);
                        break;
                    case MAC_SUBTYPE_ACK:
					    node->nodeStats->AckRxed += 1;
                        recvACK(node);
                        break;
                    default:
                        printf("[recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
                }
                break;
            case MAC_TYPE_DATA:
                switch(GetFcSubtype(node->nodeMac->pktRx)) {              
					case MAC_SUBTYPE_DATA:
					    node->nodeStats->DataRxed += 1;
                        recvDATA(node);
                        break;
                    default:
                        printf("[recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
					    break;
                }
                break;
            default:
               	printf("[recv_timer]:: Error, Invalid frame type!\n");
			    exit(1);
			    break;
        }

		// Only the RTS, CTS and ACK need to be free here.
		// For DATA frame, the pktRx is set to be NULL by recvDATA() and 
		// the DATA frame is passed to the LLC layer.
		if (node->nodeMac->pktRx != NULL) {
			Dot11FrameFree(node->nodeMac->pktRx); 
			node->nodeMac->pktRx = NULL;
		}
        rx_resume(node);
		CheckBFTimer(node);
    }

//=======================================================
//       FUNCTIONS:  recv@ 
//       PURPOSE:     Process the frame based on its type
//======================================================= 
  void recvRTS(MobileNode *node) { 
		WGNflag flag;

		if( GetTxStatus(node) != MAC_IDLE) {
            return;
        }

        //If the node is responding with someone else and ignores this RTS.
        if (PktRspIsEmpty(node) == FALSE) {
            return;
        }
		SendCTS(node, node->nodeMac->pktRx);

        //Stop deferral process that invoked by the frame which is ready to sent.
        if (Timer_SwitchSign(node, DF_TIMER) == ON) {
			DFTimer_Stop(node);
 			flag = EventDestroy(node->Id, DFTimeOut);
			if (flag == FALSE) {
				printf("[recvRTS]:: Error, Can not find the entry which will be destroyed!\n");
				exit(1);
			 }
		}
        tx_resume(node);        
  }

  void recvCTS(MobileNode *node) {
		WGNflag flag;
		
		if(GetTxStatus(node) != MAC_RTS) {
           return;
        }
		Dot11FrameFree(node->nodeMac->pktRts);
		node->nodeMac->pktRts = NULL;
		TXTimer_Stop(node);
 	    flag = EventDestroy(node->Id, TXTimeOut);
	    if (flag == FALSE) {
		    printf("[recvCTS]:: Error, Can not find the entry which will be destroyed!\n")	;
			exit(1);
		}

	    //According to the IEEE spec 9.2.4, The successful reception 
		//of the CTS packet can lead to the reset of the short retry counter
		//but not the contension window size. 
        RstSRCounter(node);
        tx_resume(node);        
    }

    void recvACK(MobileNode *node) {
		WGNflag idle;
		WGNflag flag;

        if (GetTxStatus(node) != MAC_SEND) {
			return;
        }  
        TXTimer_Stop(node);		
		flag = EventDestroy(node->Id, TXTimeOut);
		if (flag == FALSE) {
			printf("[recvACK]:: Error, Can not find the entry which will be destroyed!\n");
			exit(1);
		}        

        // The successful reception of the ACK frame implies
        // the successful DATA transmission.  Hence, Short/Long 
		// Retry Counter and the CW should be reset.
        if (IsOverRTSThreshold(node->nodeMac->pktTx) == FALSE)	{
            RstSRCounter(node);
		}
        else
           RstLRCounter(node);
		
		Reset_cw(node);
	    Dot11FrameFree(node->nodeMac->pktTx);
		node->nodeMac->pktTx = NULL;
		
		// Backoff before accessing the medium to transmit again.		        
        idle = CheckIfChannelIdle(node);
        BFTimer_Start(node,idle); 
        tx_resume(node);
    }   

    void recvDATA(MobileNode *node) {
		WGN_802_11_Mac_Frame *frame;
		unsigned int *temp;
		unsigned int seq_no;
		unsigned int srcid;
		WGNflag found;
		WGNflag flag;
		int i;

        if (CheckIfIsBroadCastPkt(node->nodeMac->pktRx) == FALSE) {	          
			if (IsOverRTSThreshold(node->nodeMac->pktRx) == TRUE) {
                if (GetTxStatus(node) == MAC_CTS) {
                    Dot11FrameFree(node->nodeMac->pktRsp);
					node->nodeMac->pktRsp = NULL;
                    TXTimer_Stop(node);
 			        flag = EventDestroy(node->Id, TXTimeOut);
			        if (flag == FALSE) {
				        printf("[recvDATA]:: Error, Can not find the entry which will be destroyed!\n");
				        exit(1);
			        }
                    //RstSRCounter(node);                              
                    //Reset_cw(node);                                
                }
                else {
                    return;
                }
                SendACK(node, node->nodeMac->pktRx);
                tx_resume(node);
            }
            else {
				//if the node is in the corresponsing with others it will simply 
				//drop the incoming packet.           
				if(PktRspIsEmpty(node) == FALSE) {
                    return;
                }
                SendACK(node, node->nodeMac->pktRx);
                if(Timer_SwitchSign(node, TX_TIMER) == OFF) {
                    tx_resume(node);
				}
				else {
				    //seems ok, but be carefull when debug!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
				}
            }
        }
        
        //Frame duplication checking procedure.
	    srcid = node->nodeMac->pktRx->pseudo_header->srcid;
		seq_no = node->nodeMac->pktRx->pseudo_header->sc.sc_sequence;
		temp = node->nodeMac->mac_buffer;
		temp = &(temp[(srcid-1) * MAC_DUP_CHK_BUF_SIZE]);
		found = FALSE;
		// If the packet is a retried one, check whether it is a duplicated one or not.
		if (node->nodeMac->pktRx->pseudo_header->fc.fc_retry == 1) {
             for(i=0;(i<MAC_DUP_CHK_BUF_SIZE)&&(found==FALSE);i++) {
		           if(temp[i] == seq_no) {
			           found = TRUE;
					   return;
			       }
		     }
		}
		//if the incoming packet is a new one, insert it to the buffer
		if (found == FALSE) {
		    temp[node->nodeMac->mac_buf_index[srcid-1]]= seq_no;
			//update the index. the index should always point to the position of the 
			//eariest incoming packet
			node->nodeMac->mac_buf_index[srcid-1] = (node->nodeMac->mac_buf_index[srcid-1] + 1) % MAC_DUP_CHK_BUF_SIZE;
		}
		
		frame = node->nodeMac->pktRx;
		node->nodeMac->pktRx = NULL;       
		//ship the frame to the uplayer (Logic Link Layer)
		MacUpPortSend(node, frame);
    }

//=======================================================
//       FUNCTION:  MacUpPortSend
//       PURPOSE:   Send the frame to the LLC layer
//=======================================================
	void S80211DcfMacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
		//********************************FOR TEST ONLY***********************************//
		//PrintSystemInfo ("SEND PACKET FROM MAC LAYER TO LLC LAYER");
		LlcDownPortRecv(node, frame);
	}

//=======================================================
//       FUNCTION:  MacUpPortRecv
//       PURPOSE:   Receive the frame from the LLC layer
//=======================================================
    void S80211DcfMacUpPortRecv (MobileNode *node, WGN_802_11_Mac_Frame *frame) {
	    unsigned int DIFS;
        DIFS = SecToNsec(GetDIFS());

	    //********************************FOR TEST ONLY***********************************//
		//PrintLine();
		//printf("NODE %d: MAC LAYER RECEIVE A PACKET FROM LLC LAYER.\n",node->Id);
		//PrintLine();
		
        node->nodeMac->HasPkt = TRUE;
		//Encapsulate the frame into 802.11 format. (actually pesudo 802.11 frame format)
		//and put it into the pktTx buffer to be sent when the channel is available
		SendDATA(node, frame);
        SendRTS(node);

		if (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE ) {
			node->nodeStats->BroadcastTx += 1;
        }	
		else
			node->nodeStats->UnicastTx += 1;
	
		if ( Timer_SwitchSign(node, BF_TIMER)==OFF ) {          
			if ( CheckIfChannelIdle(node) == TRUE ) {                 
                if ( Timer_SwitchSign(node, DF_TIMER)==OFF ) 
					 DFTimer_Start(node, DIFS);
            }
            //If the medium is NOT IDLE, then backoff timer may be started.     
            else {
                BFTimer_Start(node, FALSE);
            } 
        }
    }

//=======================================================
//       FUNCTION:  MacDownPortSend
//       PURPOSE:   Send the frame to the Physical layer
//=======================================================
void S80211DcfMacDownPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame) {
    //********************************FOR TEST ONLY***********************************// 
	//PrintLine();
    //printf("NODE %d: MAC LAYER SEND A PACKET TO PHYSICAL LAYER.\n",node->Id);
    //PrintLine();
	PhyUpPortRecv(node,frame);
}

//=======================================================
//       FUNCTION:  MacDownPortRecv
//       PURPOSE:   Receive the frame from the physical layer
//=======================================================
void S80211DcfMacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
		unsigned int time;
		double sec;
		double rxpktpwr; // (W)
		WGNTime end_time;
        
        //********************************FOR TEST ONLY***********************************// 
		//PrintLine();
	    //printf("NODE %d: MAC LAYER RECEIVE A PACKET FROM PHYSICAL LAYER.\n",node->Id);
        //PrintLine();
        
		rxpktpwr = DBToW(GetPktRxPwr(frame));
        
		//if the packet power is below CSThreshold, treat it as noise.
		if (IsOverCSThresh(rxpktpwr, node)==FALSE) {
            //Add the frame power into the total interference power.
			node->nodePhy->nodeAntenna->intPwr += rxpktpwr;		
			if (IsOverCSThresh(node->nodePhy->nodeAntenna->intPwr, node)==TRUE) {
                //if greater than the carrier sense range, change the MAC state to MAC_RECV.
                SetRxStatus(node, MAC_RECV);
            }        
		    //Set inteference timeout event
            end_time = LocalTimeAdd (GetTime(), Frame_Time(node, frame));
			AddNewEventToList(node->Id, INTTimeOut, end_time, (void*)frame);
		}		
		
		//If the frame power is bigger than the CSThreshold, treat it as a normal frame.
		else { 
			node->nodeStats->TotPktRxed += 1; 
			// If the node is transmitting, mark the frame as collision error.
			if ( (GetTxActiveSign(node) == TRUE) && ( GetColErrorSign(frame)== FALSE) ) {
				SetColErrorSign(frame);
			}
        		   
			if ( GetRxStatus(node)  == MAC_IDLE ) {
				SetRxStatus(node, MAC_RECV);
				node->nodeMac->pktRx = frame;
				sec = RX_Time(node);
				time = 	 SecToNsec(sec);
				RXTimer_Start(node, time);      
			}
			else { 
				node->nodeStats->DropForCollision += 1;
                // If the busy state of the MAC layer is caused by the interference,
				// Treat the new incoming frame as interference.
				if (node->nodeMac->pktRx == NULL) { 
					node->nodePhy->nodeAntenna->intPwr += rxpktpwr;
					end_time = LocalTimeAdd (GetTime(), Frame_Time(node, frame));
					AddNewEventToList(node->Id, INTTimeOut, end_time, (void*)frame);
				} 

				else if (GetCapSign(node) == ON) { 
					//If the power difference in dB scale between the currently being received
					//frame and the new incoming one is greater than the capture threshold, 
					//the new frame is treated as interference.
					if(IsOverCPThreshold(node, node->nodeMac->pktRx, frame) == TRUE) {
						node->nodeStats->AptCaptureNo += 1;
						Capture(node, frame);	
						node->nodePhy->nodeAntenna->intPwr += rxpktpwr;
						end_time = LocalTimeAdd (GetTime(), Frame_Time(node, frame));
						AddNewEventToList(node->Id, INTTimeOut, end_time, (void*)frame);
					} 
					else { 
						Collision(node, frame);
						// Note: Here it is uneccessary to add the pkt power to intPwr.
						// The pkt with the longest  living time will stay in the pktRx buffer
						// which will keep the "MAC_COLL" status for mac layer. 
						// The only purpose we compute the interference is for after the total
						// interference value above the CSThres, we should change the mac
						// layer status to "MAC_RECV". In this case, all the dropped pkt for
						// collison will be freed before the "MAC_COLL" status is over. So the
						// interference power which contributed by the collision packets will not
						// impact on the GINI performance.
					}
				}			
				else { 
					Collision(node, frame);
				}
			}//3
	   }//4
 }

//=======================================================
//       FUNCTION:  Capture
//       PURPOSE:   Handle the capture effect event 
//=======================================================
    void Capture(MobileNode *node, WGN_802_11_Mac_Frame *frame) {         
		switch(GetFcSubtype(frame)) {
             case MAC_SUBTYPE_RTS:
				node->nodeStats->RtsDropForCollision += 1;
                break;
             case MAC_SUBTYPE_CTS:
				 node->nodeStats->CtsDropForCollision += 1;
                 break;
             case MAC_SUBTYPE_ACK:
				 node->nodeStats->AckDropForCollision += 1;
                 break;
			 case MAC_SUBTYPE_DATA:
				 node->nodeStats->DataDropForCollision += 1;
                 break;
             default:
                 printf("[Capture]:: Error, Invalid frame subtype!\n");
				 exit(1);
        }			
    }

//=======================================================
//       FUNCTION:  Collision
//       PURPOSE:   Handle the collisions
//=======================================================
void Collision(MobileNode *node, WGN_802_11_Mac_Frame *frame)  {
	WGNflag flag;

	switch(GetRxStatus(node)) {
	    case MAC_RECV:
		    SetRxStatus(node, MAC_COLL);
		    // NOTE: NO BREAK here!!! 
	    case MAC_COLL:
            // Update the RXTimeout time 		
		    if(SecToNsec(Frame_Time(node, frame)) > RXTimer_Remain(node)) {
			   RXTimer_Stop(node);
			   flag = EventDestroy(node->Id, RXTimeOut);
			   if (flag == FALSE) {
				   printf("[Collision]:: Error, Can not find the entry which will be destroyed!\n");
				   exit(1);
			   }
			   switch(GetFcSubtype(node->nodeMac->pktRx)) {
                   case MAC_SUBTYPE_RTS:
			     	    node->nodeStats->RtsDropForCollision += 1;
                        break;
                   case MAC_SUBTYPE_CTS:
					    node->nodeStats->CtsDropForCollision += 1;
                        break;
                   case MAC_SUBTYPE_ACK:
					    node->nodeStats->AckDropForCollision += 1;
                        break;
			       case MAC_SUBTYPE_DATA:
					    node->nodeStats->DataDropForCollision += 1;
                        break;
                   default:
                        printf("[Collision]:: Error, Invalid subtype!\n");
					    exit(1);
               }

			   Dot11FrameFree(node->nodeMac->pktRx);
			   node->nodeMac->pktRx = NULL;
			   node->nodeMac->pktRx = frame;
			   frame = NULL;
			   RXTimer_Start(node, SecToNsec(RX_Time(node)));
			   //here we need not mark the frame with collision error, it will be drop after 
			   //reception for the MAC rx state of MAC_COLL
		    }
		    else {
			   switch(GetFcSubtype(frame)) {
                   case MAC_SUBTYPE_RTS:
			     	    node->nodeStats->RtsDropForCollision += 1;
                        break;
                   case MAC_SUBTYPE_CTS:
					    node->nodeStats->CtsDropForCollision += 1;
                        break;
                   case MAC_SUBTYPE_ACK:
					    node->nodeStats->AckDropForCollision += 1;
                        break;
			       case MAC_SUBTYPE_DATA:
					    node->nodeStats->DataDropForCollision += 1;
                        break;
                   default:
                        printf("[Collision]:: Error, Invalid frame subtype!\n");
					    exit(1);
               }
			   Dot11FrameFree(frame);
		    }
		    break;
	    default:
			printf("[Collision]:: Error, unpredictable rx status comes out!\n");
    }
}

//=======================================================
//       FUNCTION:  SetWaitCTSTimeout                               
//       PURPOSE:   Set the CTS timeout period 
//======================================================= 
    void SetWaitCTSTimeout() { //seconds
        Wait_CTS_Timeout = (RTS_Time + CTS_Time) + 2 * GetSIFS();  
    }

//=======================================================
//       FUNCTION:  GetWaitACKTimeout                              
//       PURPOSE:   Get the ACK timeout period 
//======================================================= 
    double GetWaitACKTimeout(MobileNode *node) { //seconds     
        return (TX_Time(node) + ACK_Time + GetSIFS() + GetDIFS());
    }

//=======================================================
//       FUNCTION:   Duration Computation Functions	
//       PURPOSE:    Calculate the value of the "duration" field in the frame
//                               header.
//======================================================= 
    // Taking 802.11 spec 7.2.1.1 as reference.
	int  RTS_DURATION (MobileNode *node) { // micro seconds
        return (SecToUsec (GetSIFS() *3 + CTS_Time + TX_Time(node) + ACK_Time));
    }  

    int  CTS_DURATION(unsigned int rts_duration) { // micro seconds    
        return (SecToUsec(rts_duration*(0.000001) - (CTS_Time + GetSIFS())));
    }
    
	int  DATA_DURATION( ) { // micro seconds
        return (SecToUsec (ACK_Time + GetSIFS()));
    }
    
	int  ACK_DURATION( ) { // micro seconds
       //no fragment is implemented so far, set to be 0 
	   return 0;           
    }

//=======================================================
//       FUNCTION:   PktErrHandler
//       PURPOSE:    Set the waiting time of the backoff timer to be EIFS
//                               if receives an erroneous frame 
//======================================================= 
  void PktErrHandler(MobileNode *node) { 
	  if ( Timer_SwitchSign(node, BF_TIMER)==OFF ) {            		 
		  if ( CheckIfChannelIdle(node) == TRUE ) {                 
               if ( Timer_SwitchSign(node, DF_TIMER)==OFF ) 
					DFTimer_Start(node, SecToNsec(GetEIFS()));
          }  
      }
	  else if ((CheckIfChannelIdle(node) == TRUE) && (Timer_PauseSign(node,BF_TIMER) == TRUE)) {
		   SetBFWaitTime(node, GetEIFS());
		   BFTimer_Resume(node);
	  }  
  }
