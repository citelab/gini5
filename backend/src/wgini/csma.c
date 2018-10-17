/*
 * NAME: csma.c 
 * FUNCTION: Collection of functions implements the csma module
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  csma.c
//======================================================= 
  #include "csma.h"

//=======================================================
//       FUNCTION:   IniNodeMac
//======================================================= 
   void IniNodeCSMAMac(NodeType type) {
	   NodeId id;
	   if (prog_verbosity_level()==2){
           printf("[IniNodeCSMAMac]:: Initializing CSMA module ... ");
       }	
	   if (type == NORMAL) {
	       for (id=1; id<=TotNodeNo; id++) {            
			 WGNnode(id)->nodeMac->normal_retry_counter = 0;
			 WGNnode(id)->nodeMac->txprob = TxProbArray[id-1];
	       }
	   }
	   if (prog_verbosity_level()==2){
		   printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTION:   FinalizeiNodeCSMAMac
//======================================================= 
   void FinalizeNodeCSMAMac(NodeType type) {
	   if (prog_verbosity_level()==2){
           printf("[FinalizeNodeCSMAMac]:: Finalizing CSMA module ... ");
       }	
	   if (prog_verbosity_level()==2){
		   printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTION:  AllowToTx  	   
//=======================================================
   WGNflag AllowToTx(MobileNode *node) {
       if (UnitUniform() < node->nodeMac->txprob) 
		   return(TRUE);
       else 
		   return(FALSE);
   }

//=======================================================
//       FUNCTION:   CSMAMacSet_Nav
//======================================================= 	
  void CSMAMacSet_Nav(MobileNode *node, unsigned int duration_ns) {     
     NAVTimer_Start(node, duration_ns);
  }

//=======================================================
//       FUNCTION:   GetMaxPropDelay
//======================================================= 	
  double GetMaxPropDelay() {     
     return ((double)sqrt(pow(SYS_INFO->map_info->x_width,2.0)+
		         pow(SYS_INFO->map_info->y_width,2.0)+
		         pow(SYS_INFO->map_info->z_width,2.0))/WAVESPD);
  }

//=======================================================
//       FUNCTION:  CSMAMacUpdateTxBuf  	   
//======================================================= 
    int CSMAMacUpdateTxBuf(MobileNode *node) {
    	
		//WGN_802_11_Mac_Frame *frame;
        unsigned int timeout;
		int subtype;   
		timeout = 0;
		//frame =  node->nodeMac->pktTx; 

		if (PktTxIsEmpty(node) == TRUE)
            return -1;

		subtype = GetFcSubtype (node->nodeMac->pktTx);
		
		switch(subtype) {
            case MAC_SUBTYPE_DATA:
				CSMAMacSetTxStatus(node,MAC_SEND);
                if (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == FALSE)	 {
                    timeout = SecToNsec(TIMEOUT_TIME); 
				}
                else					
                    timeout = SecToNsec(TX_Time(node));         
                break;
            default:
				printf ("[CSMAMacUpdateTxBuf]:: Invalid frame subtype!");
			    exit(1);
        }
        MacSendPkt(node, node->nodeMac->pktTx, timeout); // send the duplicated frame
        return 0;
    }

//=======================================================
//       FUNCTION:  CSMAMacUpdateRspBuf  	     
//======================================================= 
    int CSMAMacUpdateRspBuf(MobileNode *node) {
   		//WGN_802_11_Mac_Frame *frame;
        unsigned int timeout = 0;
		int subtype;
		
		//PrintDebugInfo ("IN UpdateRspBuf!");
		//frame = node->nodeMac->pktRsp; 

        if (PktRspIsEmpty(node) == TRUE)
            return -1;
        if (GetTxStatus(node)  == MAC_ACK)
            return -1;

        subtype = GetFcSubtype (node->nodeMac->pktRsp); 
        switch(subtype) {   
            case MAC_SUBTYPE_ACK:
				CSMAMacSetTxStatus(node,MAC_ACK);
			    //PrintDebugInfo ("SetTxStatus to be MAC_ACK!");
                timeout = SecToNsec(ACK_Time);
				//printf("timeout1 is %d \n", timeout);
                break;
			default:
				printf ("[CSMAMacUpdateRspBuf]:: Invalid frame subtype!\n");
				exit(1);
        }
        MacSendPkt(node, node->nodeMac->pktRsp, timeout);   // send the duplicated frame
        return 0;
    }

//=======================================================
//       FUNCTION:  CSMAMacUpPortSend
//       PURPOSE:   
//=======================================================
	void CSMAMacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
	    //send the packet to the switch use vpl.
		//printf("Node %d: CSMAMacUpPortSend\n\n", node->Id);
		LlcDownPortRecv(node, frame);
	}

//=======================================================
//       FUNCTION:  CSMAMacUpPortRecv
//=======================================================
  void CSMAMacUpPortRecv (MobileNode *node, WGN_802_11_Mac_Frame *frame) {
		//debug
		//FILE* in;
		//in = fopen("EVENTRECORD", "a+");
		//fprintf(in, "Node %d: A pkt comes in\n", node->Id);					 
		//fclose(in);
		//printf("Node %d: CSMAMacUpPortRecv\n\n", node->Id);

        node->nodeMac->HasPkt = TRUE;
		SendDATA(node, frame);
        
		if (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE ) {
			node->nodeStats->BroadcastTx += 1;
        }	
		else
			node->nodeStats->UnicastTx += 1;  
		
		//if(Timer_SwitchSign(node, TX_TIMER) == OFF)	 {  
		if (GetTxStatus(node) == MAC_IDLE){
		   CSMAMac_tx_resume(node);
		}
  }

//=======================================================
//       FUNCTION:  CSMAMacDownPortSend
//       PURPOSE:   
//=======================================================
void CSMAMacDownPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame) {
    //PrintLine();
    //printf("NODE %d: MAC LAYER SEND A PACKET TO PHYSICAL LAYER.\n",node->Id);
    //PrintLine();
	//printf("Node %d: CSMAMacDownPortSend\n\n", node->Id);
	PhyUpPortRecv(node,frame);
}

//=======================================================
//       FUNCTION:  CSMAMacDownPortRecv 
//=======================================================
void CSMAMacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
		unsigned int time;
		double sec;

		//PrintLine();
	    //printf("NODE %d: MAC LAYER RECEIVE A PACKET FROM PHYSICAL LAYER.\n",node->Id);
        //PrintLine();
		//printf("Node %d: CSMAMacDownPortRecv\n\n", node->Id);
		node->nodeStats->TotPktRxed += 1;
        // if in transmission state, drop the signal
        if ( (GetTxActiveSign(node) == TRUE) && ( GetColErrorSign(frame)== FALSE) ) {
            //mark it as error
			SetColErrorSign(frame);
        }
        
        //Rong: the physial layer should pass me all the signal that has been received
        if ( GetRxStatus(node)  == MAC_IDLE ) {
            //if it is greater than the receiving threshold
            CSMAMacSetRxStatus(node, MAC_RECV);
            node->nodeMac->pktRx = frame;
			sec = RX_Time(node);
			time = 	 SecToNsec(sec);
			RXTimer_Start(node, time);
		    //AddNewEventToList(node->Id, RXTimeOut, node->nodeMac->nodeTimer->rx_timer->end_time,NULL); 
		}

        else {
		    //If the power of the incoming packet is smaller than the
		    //power of the packet currently being received by at least
            //the capture threshold, then we ignore the new packet.
		    node->nodeStats->DropForCollision += 1;

			if (GetCapSign(node) == ON) {
				if(IsOverCPThreshold(node, node->nodeMac->pktRx, frame) == TRUE) {
					node->nodeStats->AptCaptureNo += 1;
					CSMAMacCapture(node, frame);
				} 
				else {
					CSMAMacCollision(node, frame);
				}
			}
			else {
				CSMAMacCollision(node, frame);
			}
		}
}

//=======================================================
//       FUNCTION:  CSMAMacCapture
//=======================================================
    void CSMAMacCapture(MobileNode *node, WGN_802_11_Mac_Frame *frame) {         

		//PrintSystemInfo ("Capture Happened !!!");
			
		switch(GetFcSubtype(frame)) {
             case MAC_SUBTYPE_ACK:
				 node->nodeStats->AckDropForCollision += 1;
                 break;
			 case MAC_SUBTYPE_DATA:
				 node->nodeStats->DataDropForCollision += 1;
                 break;
             default:
                 printf("[CSMAMacCapture]:: Invalid frame subtype!\n");
				 exit(1);
        }			
        Dot11FrameFree(frame);
		frame=NULL;
    }

//=======================================================
//       FUNCTION:  CSMAMacCollision
//       PURPOSE:   
//=======================================================
void CSMAMacCollision(MobileNode *node, WGN_802_11_Mac_Frame *frame)  {
	WGNflag flag;

	//PrintSystemInfo ("Collision Happened !!!");	
	switch(GetRxStatus(node)) {
	    case MAC_RECV:
		    CSMAMacSetRxStatus(node, MAC_COLL);
		    //NOTE: no break here!!! 
	    case MAC_COLL:
		    //  Since a collision has occurred, figure out
		    //  which packet that caused the collision will
		    //  "last" the longest.  Make this packet,
		    //  pktRx_ and reset the Recv Timer if necessary.			
		    if(SecToNsec(Frame_Time(node, frame)) > RXTimer_Remain(node)) {
			   //stop timer before timeout
			   RXTimer_Stop(node);
			   flag = EventDestroy(node->Id, RXTimeOut);
			   if (flag == FALSE) {
				   printf("[CSMAMacCollision]:: Error, Can not find the entry which will be destroyed!\n");
				   exit(1);
			   }
			   //statistic stuff
			   switch(GetFcSubtype(node->nodeMac->pktRx)) {
                   case MAC_SUBTYPE_ACK:
					    node->nodeStats->AckDropForCollision += 1;
                        break;
			       case MAC_SUBTYPE_DATA:
					    node->nodeStats->DataDropForCollision += 1;
                        break;
                   default:
                        printf("[CSMAMacCollision]:: Error, Invalid frame subtype!\n");
					    exit(1);
               }

			   Dot11FrameFree(node->nodeMac->pktRx);
			   node->nodeMac->pktRx = frame;
			   RXTimer_Start(node, SecToNsec(RX_Time(node)));
		       //AddNewEventToList(node->Id, RXTimeOut, node->nodeMac->nodeTimer->rx_timer->end_time,NULL); 
			   //here we need not mark the packet with error, it will be drop after being
			   //received cause the rxstatus is MAC_COLL
		    }
		    else {
			   //statistic stuff
			   switch(GetFcSubtype(frame)) {
                   case MAC_SUBTYPE_ACK:
					    node->nodeStats->AckDropForCollision += 1;
                        break;
			       case MAC_SUBTYPE_DATA:
					    node->nodeStats->DataDropForCollision += 1;
                        break;
                   default:
                        printf("[CSMAMacCollision]:: Error, Invalid frame subtype!\n");
					    exit(1);
               }
			   Dot11FrameFree(frame);
			   frame=NULL;
		    }
		    break;
	    default:
			printf("[CSMAMacCollision]:: Error, unpredictable rx status comes out!\n");
    }
}

//=======================================================
//       FUNCTION:   SetTxStatus
//======================================================= 	
  void CSMAMacSetTxStatus(MobileNode *node,MacStatus status) {
     node->nodeMac->txStatus = status;
  }

//=======================================================
//       FUNCTION:   CSMAMacSetRxStatus
//======================================================= 	
  void CSMAMacSetRxStatus(MobileNode *node,MacStatus status) {
     node->nodeMac->rxStatus = status;
  }

//=======================================================
//       FUNCTION:   CSMAMacRXTimeoutHandler
//       PURPOSE:    To handle RXTimer Timeout Event
//======================================================= 	
  void CSMAMacRXTimeoutHandler(MobileNode *node) {
     RXTimer_Stop(node);
     CSMAMac_recv_timer(node);         
  }

//=======================================================
//       FUNCTION:   CSMAMacTXTimeoutHandler
//       PURPOSE:    To handle TXTimer Timeout Event
//======================================================= 	
  void CSMAMacTXTimeoutHandler(MobileNode *node) {
    //PrintDebugInfo ("txeventhandler 1");
	 TXTimer_Stop(node);
	 //CSMAMacSetTxStatus(node,MAC_IDLE);
     CSMAMac_send_timer(node);       
  }

//=======================================================
//       FUNCTION:   CSMAMacIFTimeoutHandler
//       PURPOSE:    To handle InterFaceTimer Timeout Event
//======================================================= 	
  void CSMAMacIFTimeoutHandler(MobileNode *node) {   
     IFTimer_Stop(node);       
	 SetTxActiveSign(node,FALSE) ;   
  }

//=======================================================
//       FUNCTION:   CSMAMacNAVTimeoutHandler
//       PURPOSE:    To handle NAVTimer Timeout Event
//======================================================= 	
  void CSMAMacNAVTimeoutHandler(MobileNode *node) {    
	 NAVTimer_Stop(node);
	 //printf("NAV TIMEOUT HANDLER\n\n");
	 if (GetTxStatus(node) == MAC_IDLE)	 {  
		 CSMAMac_tx_resume(node);
	 }
  }

//=======================================================
//       FUNCTION:  CSMAMac_send_timer 	     
//======================================================= 
    void CSMAMac_send_timer (MobileNode *node) {
        //printf("send_timer(): ......\n");
		switch(GetTxStatus(node)) {
            case MAC_SEND: 
				// Sent DATA, but did not receive an ACK packet.
                CSMAMacRetransmitData(node);                            
                break;
            case MAC_ACK:  // Sent an ACK, and now ready to resume transmission.
                Dot11FrameFree(node->nodeMac->pktRsp);
				node->nodeMac->pktRsp = NULL;         
                break;	
            case MAC_IDLE:       
                break;	
            default:
               printf("[CSMAMac_send_timer]:: Error, Invalid mac state!\n");
			   exit(1);
        }
        CSMAMac_tx_resume(node);			 //?if no pkt is waiting for sending, ask for packet from the uplayer
    }

//=======================================================
//       FUNCTION:  CSMAMac_recv_timer	     
//======================================================= 
    void CSMAMac_recv_timer(MobileNode *node) {
  		char *dst;

		if (node->nodeMac->pktRx->frame_body == NULL) {
            dst = GetRa(node->nodeMac->pktRx); 
		}
		else  //it is an ABOVE level packet 
			dst = GetDa(node->nodeMac->pktRx);
	    
        //If the interface is in TRANSMIT mode when this packet
        //"arrives", then I would never have seen it and should
        //do a silent discard without adjusting the NAV.
        if (GetTxActiveSign(node) == TRUE) {
			node->nodeStats->DropForInTx += 1;
            Dot11FrameFree(node->nodeMac->pktRx);
			node->nodeMac->pktRx = NULL;
			if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
			    //PrintLine ();
			    //printf("NODE %d: PACKET HAS ERROR : RECV THE PACKET WHEN SENDING PACKET. DROPED.\n",node->Id);
                //PrintLine ();
			}
			CSMAMac_rx_resume(node);
			return;
        }

		//Handle collisions.
        if ( GetRxStatus(node) == MAC_COLL ) { 
			//the node should experience the nav process for eifs after receiving 
			//a corrupted packet.
			node->nodeStats->DropForCollision += 1;
			   //statistic stuff
			switch(GetFcSubtype(node->nodeMac->pktRx)) {
                   case MAC_SUBTYPE_ACK:
					    node->nodeStats->AckDropForCollision += 1;
                        break;
			       case MAC_SUBTYPE_DATA:
					    node->nodeStats->DataDropForCollision += 1;
                        break;
                   default:
                        printf("[CSMAMac_recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
            }
			Dot11FrameFree(node->nodeMac->pktRx); 
			node->nodeMac->pktRx = NULL;
			if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
				//PrintLine ();
				//printf("NODE %d: PACKET HAS ERROR : COLLISION HAPPENED. DROPED.\n",node->Id);
				//PrintLine ();
			}
			CSMAMac_rx_resume(node);   
            return;
        }

        if( PktRxHasFadError(node) == TRUE ) {
			node->nodeStats->DropForLowRxPwr += 1;
            Dot11FrameFree(node->nodeMac->pktRx);
			node->nodeMac->pktRx = NULL;
			if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
				//PrintLine ();
				//printf("NODE %d: PACKET HAS ERROR : RECV POWER IS TOO LOW. DROPED.\n",node->Id);
				//PrintLine ();
			}
			CSMAMac_rx_resume(node);
            return;
        }

        if( PktRxHasColError(node) == TRUE ) {
			//node->nodeStats->DropForCollision += 1;
			node->nodeStats->DropForInTx += 1;
            Dot11FrameFree(node->nodeMac->pktRx);
			node->nodeMac->pktRx = NULL;
			if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
				//PrintLine ();
				//printf("NODE %d: PACKET HAS ERROR : RECV THE PACKET WHEN SENDING PACKET. DROPED.\n",node->Id);
				//PrintLine ();
			}
			CSMAMac_rx_resume(node);
            return;
        }
		
        if(((MacAddrIsSame(dst, node->nodeMac->mac_addr)) == FALSE) && 
		   CheckIfIsBroadCastPkt(node->nodeMac->pktRx) == FALSE) {
		   node->nodeStats->NotForMeRxed += 1;
		   Dot11FrameFree(node->nodeMac->pktRx);
		   node->nodeMac->pktRx = NULL;
		   //PrintLine ();
		   //printf("NODE %d: PACKET IS NOT FOR ME. DROPED.\n",node->Id);
		   //PrintLine ();
           CSMAMac_rx_resume(node);
           return;
        }

	    //PrintSystemInfo ("recv_timer 1");
        
		switch(GetFctype(node->nodeMac->pktRx)) {
            case MAC_TYPE_MANAGEMENT:
				printf("[CSMAMac_recv_timer]:: MAC_TYPE_MANAGEMENT type is not implemented now!\n");
			    break;              
            case MAC_TYPE_CONTROL:
                switch(GetFcSubtype(node->nodeMac->pktRx)) {
                    case MAC_SUBTYPE_ACK:
						//PrintSystemInfo ("Recv a ACK packet!");
					    node->nodeStats->AckRxed += 1;
                        CSMAMacRecvACK(node);                                            
                        break;
                    default:
                        printf("[CSMAMac_recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
                }
                break;
            case MAC_TYPE_DATA:
                switch(GetFcSubtype(node->nodeMac->pktRx)) {              
					case MAC_SUBTYPE_DATA:
						//PrintSystemInfo ("Recv a DATA packet!");
					    node->nodeStats->DataRxed += 1;
                        CSMAMacRecvDATA(node);                                     
                        break;
                    default:
                        printf("[CSMAMac_recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
					    break;
                }
                break;
            default:
               	printf("[CSMAMac_recv_timer]:: Error, Invalid frame subtype!\n");
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
        CSMAMac_rx_resume(node);
    } 

//=======================================================
//       FUNCTION:  CSMAMac_tx_resume 
//       PURPOSE:   
//======================================================= 	
  void CSMAMac_tx_resume(MobileNode *node) {
     
	 CSMAMacSetTxStatus(node,MAC_IDLE);
	 /*if (node->nodeMac->pktRsp != NULL) {
		  CSMAMacUpdateRspBuf(node);
	      return;
	 } */ 
     if (CheckIfChannelIdle(node) == TRUE) {
	     if (node->nodeMac->pktRsp != NULL) {
		     CSMAMacUpdateRspBuf(node);
	     }  
		 else if ( node->nodeMac->pktTx != NULL ) {
			if (AllowToTx(node) == TRUE) {
				CSMAMacUpdateTxBuf(node);
			}
			else {
				//try to sense the channel after some time.
				CSMAMacSet_Nav(node, SecToNsec(GetMaxPropDelay()));
			}
		}
	 }
	 if ((node->nodeMac->pktRsp == NULL)&&(node->nodeMac->pktTx == NULL)) {
		if (LlcDownPortSend(node) == FALSE) {
			node->nodeMac->HasPkt = FALSE;
		}	
	 }
  }

//=======================================================
//       FUNCTION:  CSMAMac_rx_resume 
//       PURPOSE:   
//======================================================= 	
  void CSMAMac_rx_resume( MobileNode *node ) {
     CSMAMacSetRxStatus(node,MAC_IDLE);
	 //if(Timer_SwitchSign(node, TX_TIMER) == OFF)	 { 
	if (GetTxStatus(node) == MAC_IDLE)	 {
		CSMAMac_tx_resume(node);
	 }
  }

//=======================================================
//       FUNCTION:  CSMAMacRecvACK     
//=======================================================
    void CSMAMacRecvACK(MobileNode *node) {
		WGNflag flag;

		//printf("Node %d: CSMAMacRecvACK!\n\n", node->Id);

        if (GetTxStatus(node) != MAC_SEND) {
			return;
        }  
        TXTimer_Stop(node);
 		//CSMAMacSetTxStatus(node,MAC_IDLE);

		flag = EventDestroy(node->Id, TXTimeOut);

		if (flag == FALSE) {
			printf("[CSMAMacRecvACK]:: Error, Can not find the entry which will be destroyed!\n");
			exit(1);
		}        

        CSMARstRetryCounter(node);        

        // Backoff before sending again.	        
	    Dot11FrameFree(node->nodeMac->pktTx);
		node->nodeMac->pktTx = NULL;
		CSMAMac_tx_resume(node);                                        
    }   

//=======================================================
//       FUNCTION:  CSMAMacRecvDATA     
//=======================================================
    void CSMAMacRecvDATA(MobileNode *node) {
		WGN_802_11_Mac_Frame *frame;
		unsigned int *temp;
		unsigned int seq_no;
		unsigned int srcid;
		WGNflag found;
		int i;

		//printf("Node %d: CSMAMacRecvDATA!\n\n", node->Id);

        if (CheckIfIsBroadCastPkt(node->nodeMac->pktRx) == FALSE) {	          
				if(PktRspIsEmpty(node) == FALSE) {
                    return;
                }
                SendACK(node, node->nodeMac->pktRx);
                //if(Timer_SwitchSign(node, TX_TIMER) == OFF)	 {
				if (GetTxStatus(node) == MAC_IDLE){	
                    CSMAMac_tx_resume(node);                                
				}
				else {
					//free(node->nodeMac->pktRsp);
					//node->nodeMac->pktRsp = NULL;
					//PrintSystemInfo ("I am here"); 
				    //seems ok, but be carefull when debug!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
				}
        }
        
        //duplication check
	    srcid = node->nodeMac->pktRx->pseudo_header->srcid;
		seq_no = node->nodeMac->pktRx->pseudo_header->sc.sc_sequence;
		temp = node->nodeMac->mac_buffer;
		temp = &(temp[(srcid-1) * MAC_DUP_CHK_BUF_SIZE]);
		found = FALSE;
		//if the packet is a retried one, check the received packet buffer at the receiver side
		//or it is unnecessary to do so
		if (node->nodeMac->pktRx->pseudo_header->fc.fc_retry == 1) {
             for(i=0;(i<MAC_DUP_CHK_BUF_SIZE)&&(found==FALSE);i++) {
		           if(temp[i] == seq_no) {
			           found = TRUE;
			 		   //free the duplicated packet
			 		   //free((node->nodeMac->pktRx);
					   return;
			       }
		     }
		}
		//if the incoming packet is not in the buffer, insert it to the buffer
		if (found == FALSE) {
		    temp[node->nodeMac->mac_buf_index[srcid-1]]= seq_no;
			//update the index. the index should always point to the position of the eariest 
			//incoming packet
			if (node->nodeMac->mac_buf_index[srcid-1] == MAC_DUP_CHK_BUF_SIZE-1)
			    node->nodeMac->mac_buf_index[srcid-1] = 0;
		    else
				node->nodeMac->mac_buf_index[srcid-1] = 
				node->nodeMac->mac_buf_index[srcid-1] + 1;
		}
		
		//point the pktRx to be NULL to prevent the frame which is pointed by it
		//from being free after the recv process
		frame = node->nodeMac->pktRx;
		node->nodeMac->pktRx = NULL;       
		//ship the 802.3 frame to the uplayer (Logic Link Layer)
		MacUpPortSend(node, frame);
    }

//=======================================================
//       FUNCTION:  CSMAMacRetransmitData  	     
//======================================================= 
	void CSMAMacRetransmitData(MobileNode *node) {
        
        if (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE) {
			//PrintSystemInfo ("RetransmitData1");
			Dot11FrameFree(node->nodeMac->pktTx);
			node->nodeMac->pktTx = NULL; 
            return;
        }
        
		CSMAUpdateRetryCounter(node);

		// IEEE Spec section 9.2.3.5 says this should be greater than or equal
        if(node->nodeMac->normal_retry_counter >= RETX_MAX_NUM) {
			node->nodeStats->DropForExMaxPktRetryNo += 1;
            Dot11FrameFree(node->nodeMac->pktTx);
			node->nodeMac->pktTx = NULL;
            CSMARstRetryCounter(node);
        }
        else {
		    //statistics
			node->nodeStats->ReTxPktNum += 1;
		    node->nodeStats->DataTxed += 1;
			//if (islargepkt == TRUE) {
			//	node->nodeStats->ReTxRtsNum += 1;
			//}
            set_fc_retry(&(node->nodeMac->pktTx->pseudo_header->fc), 1);
        }
    }

//=======================================================
//       FUNCTION:  CSMARstRetryCounter     
//=======================================================
  void CSMARstRetryCounter(MobileNode *node) {
     node->nodeMac->normal_retry_counter = 0;
  }

//=======================================================
//       FUNCTION:  UpdateRetryCounter  	     
//=======================================================
    void CSMAUpdateRetryCounter(MobileNode *node) {  
		node->nodeMac->normal_retry_counter += 1;
    }  
