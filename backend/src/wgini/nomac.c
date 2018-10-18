/*
 * NAME: nomac.c 
 * FUNCTION: Collection of functions implements the NONE mac module.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  nomac.c
//======================================================= 
  #include "nomac.h"

//=======================================================
//       FUNCTION:   IniNodeMac
//======================================================= 
   void IniNodeNoMac(NodeType type) {
	   NodeId id;
	   if (prog_verbosity_level()==2){
           printf("[IniNodeNoMac]:: Initializing NONE mac module ... ");
       }	
	   if (type == NORMAL) {
	       for (id=1; id<=TotNodeNo; id++) {            
			 WGNnode(id)->nodeMac->normal_retry_counter = 0;
	       }
	   }
	   if (prog_verbosity_level()==2){
		   printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTION:   FinalizeNodeNoMac
//======================================================= 
   void FinalizeNodeNoMac(NodeType type) {
	   if (prog_verbosity_level()==2){
           printf("[FinalizeNodeNoMac]:: Finalizing NONE mac module ... ");
       }	
	   if (prog_verbosity_level()==2){
		   printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTION:  NoMacUpdateTxBuf  	   
//======================================================= 
    int NoMacUpdateTxBuf(MobileNode *node) {
    	
		WGN_802_11_Mac_Frame *frame;
        unsigned int timeout = 0;
		int subtype;       
		frame =  node->nodeMac->pktTx;

		if (PktTxIsEmpty(node) == TRUE)
            return -1;

		subtype = GetFcSubtype (frame);
		
		switch(subtype) {
            case MAC_SUBTYPE_DATA:
				NoMacSetTxStatus(node,MAC_SEND);
                if (CheckIfIsBroadCastPkt(frame) == FALSE)	 {
                    timeout = SecToNsec(TIMEOUT_TIME); 
				}
                else					
                    timeout = SecToNsec(TX_Time(node));         
                break;
            default:
				printf ("[NoMacUpdateTxBuf]:: Error, Invalid frame subtype!");
			    exit(1);
        }
        MacSendPkt(node, frame, timeout); // send the duplicated frame
        return 0;
    }

//=======================================================
//       FUNCTION:  NoMacUpdateRspBuf  	     
//======================================================= 
    int NoMacUpdateRspBuf(MobileNode *node) {
   		WGN_802_11_Mac_Frame *frame;
        unsigned int timeout = 0;
		int subtype;
		
		//PrintDebugInfo ("IN UpdateRspBuf!");
		frame = node->nodeMac->pktRsp;

        if (PktRspIsEmpty(node) == TRUE)
            return -1;
        if (GetTxStatus(node)  == MAC_ACK)
            return -1;

		//PrintDebugInfo ("IN UpdateRspBuf2!");
        subtype = GetFcSubtype (frame); 
        switch(subtype) {   
            case MAC_SUBTYPE_ACK:
				NoMacSetTxStatus(node,MAC_ACK);
			    //PrintDebugInfo ("SetTxStatus to be MAC_ACK!");
                timeout = SecToNsec(ACK_Time);
				//printf("timeout1 is %d \n", timeout);
                break;
            default:
				printf ("[NoMacUpdateRspBuf]:: Error, Invalid frame subtype!");
			    exit(1);
        }
        MacSendPkt(node, frame, timeout);   // send the duplicated frame
        return 0;
    }

//=======================================================
//       FUNCTION:  NoMacUpPortSend
//       PURPOSE:   
//=======================================================
	void NoMacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
	    //send the packet to the switch use vpl.
		//PrintSystemInfo ("SEND PACKET FROM MAC LAYER TO LLC LAYER");
		LlcDownPortRecv(node, frame);
	}

//=======================================================
//       FUNCTION:  NoMacUpPortRecv
//=======================================================
  void NoMacUpPortRecv (MobileNode *node, WGN_802_11_Mac_Frame *frame) {
		//debug
		//FILE* in;
		//in = fopen("EVENTRECORD", "a+");
		//fprintf(in, "Node %d: A pkt comes in\n", node->Id);					 
		//fclose(in);
		 
        node->nodeMac->HasPkt = TRUE;
		SendDATA(node, frame);
        
		if (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE ) {
			node->nodeStats->BroadcastTx += 1;
        }	
		else
			node->nodeStats->UnicastTx += 1;  
		
		if(Timer_SwitchSign(node, TX_TIMER) == OFF)	 {
		   NoMac_tx_resume(node);
		}
  }

//=======================================================
//       FUNCTION:  NoMacDownPortSend
//       PURPOSE:   
//=======================================================
void NoMacDownPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame) {
    //PrintLine();
    //printf("NODE %d: MAC LAYER SEND A PACKET TO PHYSICAL LAYER.\n",node->Id);
    //PrintLine();
	PhyUpPortRecv(node,frame);
}

//=======================================================
//       FUNCTION:  NoMacDownPortRecv 
//=======================================================
void NoMacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
		unsigned int time;
		double sec;

		//PrintLine();
	    //printf("NODE %d: MAC LAYER RECEIVE A PACKET FROM PHYSICAL LAYER.\n",node->Id);
        //PrintLine();

		node->nodeStats->TotPktRxed += 1;
        // if in transmission state, drop the signal
        if ( (GetTxActiveSign(node) == TRUE) && ( GetColErrorSign(frame)== FALSE) ) {
            //mark it as error
			SetColErrorSign(frame);
        }
        
        //Rong: the physial layer should pass me all the signal that has been received
        if ( GetRxStatus(node)  == MAC_IDLE ) {
            //if it is greater than the receiving threshold
            NoMacSetRxStatus(node, MAC_RECV);
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
					NoMacCapture(node, frame);
				} 
				else {
					NoMacCollision(node, frame);
				}
			}
			else {
			   NoMacCollision(node, frame);
			}
		}
}

//=======================================================
//       FUNCTION:  NoMacCapture
//       PURPOSE:   
//=======================================================
    void NoMacCapture(MobileNode *node, WGN_802_11_Mac_Frame *frame) {         

		//PrintSystemInfo ("Capture Happened !!!");
			
		switch(GetFcSubtype(frame)) {
             case MAC_SUBTYPE_ACK:
				 node->nodeStats->AckDropForCollision += 1;
                 break;
			 case MAC_SUBTYPE_DATA:
				 node->nodeStats->DataDropForCollision += 1;
                 break;
             default:
                 printf ("[NoMacCapture]:: Error, Invalid frame subtype!");
				 exit(1);
        }			
        Dot11FrameFree(frame);
    }

//=======================================================
//       FUNCTION:  NoMacCollision
//       PURPOSE:   
//=======================================================
void NoMacCollision(MobileNode *node, WGN_802_11_Mac_Frame *frame)  {
	WGNflag flag;

	//PrintSystemInfo ("Collision Happened !!!");	
	switch(GetRxStatus(node)) {
	    case MAC_RECV:
		    NoMacSetRxStatus(node, MAC_COLL);
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
				   printf("[NoMacCollision]:: Error, Can not find the entry which will be destroyed!\n");
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
                        printf("[NoMacCollision]:: Error, Invalid frame subtype!\n");
					    exit(1);
               }

			   Dot11FrameFree(node->nodeMac->pktRx);
			   //node->nodeStats->DropForCollision += 1;
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
                        printf("[NoMacCollision]:: Error, Invalid frame subtype!\n");
					    exit(1);
               }
			   Dot11FrameFree(frame);
		    }
		    break;
	    default:
			printf("[NoMacCollision]:: error, unpredictable rx status comes out!\n");
    }
}

//=======================================================
//       FUNCTION:   SetTxStatus
//======================================================= 	
  void NoMacSetTxStatus(MobileNode *node,MacStatus status) {
	 //PrintDebugInfo ("In SetTxStatus!");
     node->nodeMac->txStatus = status;
  }

//=======================================================
//       FUNCTION:   NoMacSetRxStatus
//======================================================= 	
  void NoMacSetRxStatus(MobileNode *node,MacStatus status) {
     node->nodeMac->rxStatus = status;
  }

//=======================================================
//       FUNCTION:   RXTimeoutHandler
//       PURPOSE:    To handle RXTimer Timeout Event
//======================================================= 	
  void NoMacRXTimeoutHandler(MobileNode *node) {
     RXTimer_Stop(node);
     NoMac_recv_timer(node);         
  }

//=======================================================
//       FUNCTION:   NoMacTXTimeoutHandler
//       PURPOSE:    To handle TXTimer Timeout Event
//======================================================= 	
  void NoMacTXTimeoutHandler(MobileNode *node) {
     //PrintDebugInfo ("txeventhandler 1");
	 TXTimer_Stop(node);
	 //NoMacSetTxStatus(node,MAC_IDLE);
     NoMac_send_timer(node);       
  }

//=======================================================
//       FUNCTION:   NoMacIFTimeoutHandler
//       PURPOSE:    To handle InterFaceTimer Timeout Event
//======================================================= 	
  void NoMacIFTimeoutHandler(MobileNode *node) {   
     IFTimer_Stop(node);       
     //NOTE: TxActiveSign is different from txStatus!!!
     //TxActiveSign will only lasts for time period of txtime(packet)
     //txStatus will not stop untill the txtimeout event happens
	 SetTxActiveSign(node,FALSE) ;   
  }

//=======================================================
//       FUNCTION:  NoMac_send_timer 	     
//======================================================= 
    void NoMac_send_timer (MobileNode *node) {
        //printf("send_timer(): ......\n");
		switch(GetTxStatus(node)) {
            case MAC_SEND: 
				// Sent DATA, but did not receive an ACK packet.
                NoMacRetransmitData(node);                            
                break;
            case MAC_ACK:  // Sent an ACK, and now ready to resume transmission.
                Dot11FrameFree(node->nodeMac->pktRsp);
				node->nodeMac->pktRsp = NULL;         
                break;	
            case MAC_IDLE:       
                break;	
            default:
               printf("[NoMac_send_timer]:: Error, Invalid mac status!\n");
			   exit(1);
        }
        NoMac_tx_resume(node);			 //?if no pkt is waiting for sending, ask for packet from the uplayer
    }

//=======================================================
//       FUNCTION:  NoMac_recv_timer	     
//======================================================= 
    void NoMac_recv_timer(MobileNode *node) {
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
			NoMac_rx_resume(node);               
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
                        printf("[NoMac_recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
            }
			Dot11FrameFree(node->nodeMac->pktRx); 
			node->nodeMac->pktRx = NULL;
			if (MacAddrIsSame(dst, node->nodeMac->mac_addr) == TRUE)	{
				//PrintLine ();
				//printf("NODE %d: PACKET HAS ERROR : COLLISION HAPPENED. DROPED.\n",node->Id);
				//PrintLine ();
			}
			NoMac_rx_resume(node);   
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
			NoMac_rx_resume(node);
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
			NoMac_rx_resume(node);
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
           NoMac_rx_resume(node);
           return;
        }

	    //PrintSystemInfo ("recv_timer 1");
        
		switch(GetFctype(node->nodeMac->pktRx)) {
            case MAC_TYPE_MANAGEMENT:
				printf("[NoMac_recv_timer]:: MAC_TYPE_MANAGEMENT type is not implemented now!\n");
			    break;              
            case MAC_TYPE_CONTROL:
                switch(GetFcSubtype(node->nodeMac->pktRx)) {
                    case MAC_SUBTYPE_ACK:
						//PrintSystemInfo ("Recv a ACK packet!");
					    node->nodeStats->AckRxed += 1;
                        NoMacRecvACK(node);                                            
                        break;
                    default:
                        printf("[NoMac_recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
                }
                break;
            case MAC_TYPE_DATA:
                switch(GetFcSubtype(node->nodeMac->pktRx)) {              
					case MAC_SUBTYPE_DATA:
						//PrintSystemInfo ("Recv a DATA packet!");
					    node->nodeStats->DataRxed += 1;
                        NoMacRecvDATA(node);                                     
                        break;
                    default:
                        printf("[NoMac_recv_timer]:: Error, Invalid frame subtype!\n");
					    exit(1);
					    break;
                }
                break;
            default:
                printf("[NoMac_recv_timer]:: Error, Invalid frame subtype!\n");
			    exit(1);
			    break;
        }
        
		if (node->nodeMac->pktRx != NULL) {
			Dot11FrameFree(node->nodeMac->pktRx);  
			node->nodeMac->pktRx = NULL;
	    }
        NoMac_rx_resume(node);
    } 

//=======================================================
//       FUNCTION:  NoMac_tx_resume 
//       PURPOSE:   
//======================================================= 	
  void NoMac_tx_resume(MobileNode *node) {
	 
	 NoMacSetTxStatus(node,MAC_IDLE);

	 if ( node->nodeMac->pktRsp != NULL ) {
        NoMacUpdateRspBuf(node);
     }  
	 else if ( node->nodeMac->pktTx != NULL ) {
		NoMacUpdateTxBuf(node);
     }
     else {
		//NoMacSetTxStatus(node,MAC_IDLE);
		if (LlcDownPortSend(node) == FALSE) {
			node->nodeMac->HasPkt = FALSE;
		}	  	
	 }	 
	 //PrintDebugInfo ("SetTxStatus to be IDLE!");
  }

//=======================================================
//       FUNCTION:  NoMac_rx_resume 
//       PURPOSE:   
//======================================================= 	
  void NoMac_rx_resume( MobileNode *node ) {
     NoMacSetRxStatus(node,MAC_IDLE);
  }

//=======================================================
//       FUNCTION:  NoMacRecvACK     
//=======================================================
    void NoMacRecvACK(MobileNode *node) {
		WGNflag flag;

        if (GetTxStatus(node) != MAC_SEND) {
			return;
        }  
        TXTimer_Stop(node);

		flag = EventDestroy(node->Id, TXTimeOut);

		if (flag == FALSE) {
			printf("[NoMacRecvACK]:: Error, Can not find the entry which will be destroyed!\n");
			exit(1);
		}        

        RstRetryCounter(node);        

        // Backoff before sending again.	        
	    Dot11FrameFree(node->nodeMac->pktTx);
		node->nodeMac->pktTx = NULL;
        NoMac_tx_resume(node);                                        
    }   

//=======================================================
//       FUNCTION:  NoMacRecvDATA     
//=======================================================
    void NoMacRecvDATA(MobileNode *node) {
		WGN_802_11_Mac_Frame *frame;
		unsigned int *temp;
		unsigned int seq_no;
		unsigned int srcid;
		WGNflag found;
		int i;

        if (CheckIfIsBroadCastPkt(node->nodeMac->pktRx) == FALSE) {	          
				if(PktRspIsEmpty(node) == FALSE) {
                    return;
                }
                SendACK(node, node->nodeMac->pktRx);
                if(Timer_SwitchSign(node, TX_TIMER) == OFF)	 {
					//SendACK(node, node->nodeMac->pktRx);
                    NoMac_tx_resume(node);                                
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
//       FUNCTION:  NoMacRetransmitData  	     
//======================================================= 
	void NoMacRetransmitData(MobileNode *node) {
        
        if (CheckIfIsBroadCastPkt(node->nodeMac->pktTx) == TRUE) {
			//PrintSystemInfo ("RetransmitData1");
			Dot11FrameFree(node->nodeMac->pktTx);
			node->nodeMac->pktTx = NULL; 
            return;
        }
        
		UpdateRetryCounter(node);

		// IEEE Spec section 9.2.3.5 says this should be greater than or equal
        if(node->nodeMac->normal_retry_counter >= RETX_MAX_NUM) {
			node->nodeStats->DropForExMaxPktRetryNo += 1;
            Dot11FrameFree(node->nodeMac->pktTx);
			node->nodeMac->pktTx = NULL;
            RstRetryCounter(node);
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
//       FUNCTION:  RstRetryCounter     
//=======================================================
  void RstRetryCounter(MobileNode *node) {
     node->nodeMac->normal_retry_counter = 0;
  }

//=======================================================
//       FUNCTION:  UpdateRetryCounter  	     
//=======================================================
    void UpdateRetryCounter(MobileNode *node) {  
		node->nodeMac->normal_retry_counter += 1;
    }  
