/*
 * NAME: mac.c 
 * FUNCTION: Collection of functions implements the basic functional mac
 *                    layer.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  mac.c
//=======================================================
   #include "mac.h"

//=======================================================
//       FUNCTION:   IniNodeMac
//======================================================= 
   void IniNodeMac(NodeType type) {
	   int id;
   	   int i;
	   int j;
	   int buf_no;
	   
	   if (prog_verbosity_level()==1){
		   printf("[IniNodeMac]:: Initializing basic functional medium access control layer ... ");
	   }
	   
	   buf_no = MAC_DUP_CHK_BUF_SIZE*TotNodeNo;
	   
	   //initialize the general information;
	   //current version only support the identical bandwidth. (change it in the future)
	   SetRTSTime(WGNnode(1)->nodePhy->nodeWCard->bandwidth);
	   SetCTSTime(WGNnode(1)->nodePhy->nodeWCard->bandwidth);
	   SetACKTime(WGNnode(1)->nodePhy->nodeWCard->bandwidth);
	   SetWaitCTSTimeout(WGNnode(1)->nodePhy->nodeWCard->bandwidth);
	   
	   if (type == NORMAL) {
	       for (i=0; i<TotNodeNo; i++) {
		     //******************ALLOCATE MEMORY SPACE***************
			 id = i+1;
			 //nodeMac
			 WGNnode(id)->nodeMac = (NodeMac *)malloc(sizeof(NodeMac));
			 //time stuff
			 WGNnode(id)->nodeMac->nodeTimer = (NodeTimer *)malloc(sizeof(NodeTimer));
			 WGNnode(id)->nodeMac->nodeTimer->bf_timer = (BackoffTimer *)malloc(sizeof(BackoffTimer));
			 WGNnode(id)->nodeMac->nodeTimer->df_timer = (NormalTimer *)malloc(sizeof(NormalTimer));
			 WGNnode(id)->nodeMac->nodeTimer->nav_timer = (NormalTimer *)malloc(sizeof(NormalTimer));
			 WGNnode(id)->nodeMac->nodeTimer->if_timer = (NormalTimer *)malloc(sizeof(NormalTimer));
			 WGNnode(id)->nodeMac->nodeTimer->tx_timer = (NormalTimer *)malloc(sizeof(NormalTimer));
			 WGNnode(id)->nodeMac->nodeTimer->rx_timer = (NormalTimer *)malloc(sizeof(NormalTimer));
			 //macMib
			 WGNnode(id)->nodeMac->macMib = (MacMib *)malloc(sizeof(MacMib));
			 //mac_buffer 
			 WGNnode(id)->nodeMac->mac_buffer = 
			 (int *)malloc(sizeof(int)*buf_no);
			 //mac_buf_index
			 WGNnode(id)->nodeMac->mac_buf_index = (int *)malloc(TotNodeNo*sizeof(int));

			 //******************SET THE VALUES FOR THE VARIABLES******************
	         // So far, only IBSS is supported, so here the BSSID is fixed.
			 for (j=0; j<MAC_ADDR_LEN; j++) {
	               WGNnode(id)->nodeMac->BSSID[j] = 1;     
		     }                    
	         WGNnode(id)->nodeMac->seq_no = 0;
	         WGNnode(id)->nodeMac->frag_no = 0;     //not used now                  
	  		 memcpy(WGNnode(id)->nodeMac->mac_addr, mac_addr_array[i].addr, MAC_ADDR_LEN);
	         WGNnode(id)->nodeMac->TxActiveSign = FALSE;
	         WGNnode(id)->nodeMac->txStatus = MAC_IDLE;
	         WGNnode(id)->nodeMac->rxStatus = MAC_IDLE;
	   		 //reset all the timers
			 BFTimer_Stop(WGNnode(id));
			 DFTimer_Stop(WGNnode(id));
			 NAVTimer_Stop(WGNnode(id));
			 IFTimer_Stop(WGNnode(id));
			 TXTimer_Stop(WGNnode(id));
			 RXTimer_Stop(WGNnode(id));
			 //macMib
			 WGNnode(id)->nodeMac->macMib = SYS_INFO->mac_info;
			 //set pkt to NULL
	         WGNnode(id)->nodeMac->pktTx = NULL;
	         WGNnode(id)->nodeMac->pktRsp = NULL;
	         WGNnode(id)->nodeMac->pktRx = NULL;
			 //buffer stuff
			 for (j=0; j<buf_no; j++) {
			    WGNnode(id)->nodeMac->mac_buffer[j]= -1;
			 }
			 for (j=0; j<TotNodeNo; j++) {
			    WGNnode(id)->nodeMac->mac_buf_index[j]= 0;
			 }
			 WGNnode(id)->nodeMac->HasPkt = FALSE;
	       }
	   }       
	   if (prog_verbosity_level()==1){
	    	printf("[ OK ]\n");
	   }
	
	   if (prog_verbosity_level()==2){
		   PrintSystemInfo ("Initializing the mac layer modules ... ");
	   }		   
	   switch(SYS_INFO->mac_info->macType) {
			case CSMA:
				IniNodeCSMAMac(type); 
				break;
			case DCF_802_11:
				IniNodeS80211DcfMac(type);
				break;
			case NONE:
				IniNodeNoMac(type);
				break;
			default: 
				printf ("[IniNodeMac]:: Error, Invalid mac type: abort"); 
				exit(1); 
	   }
   }

//=======================================================
//       FUNCTION:   FinalizeNodeMac
//======================================================= 
   void FinalizeNodeMac(NodeType type) {
	   int id;
   	   int i;
	   
	   //finailize the attached modules
	   if (prog_verbosity_level()==2){
		   PrintSystemInfo ("[FinalizeNodeMac]:: Finalizing the mac layer modules ... ");
	   }	
	   switch(SYS_INFO->mac_info->macType) {
			case CSMA:
				FinalizeNodeCSMAMac(type); 
				break;
			case DCF_802_11:
				FinalizeNodeS80211DcfMac(type);
				break;
			case NONE:
				FinalizeNodeNoMac(type);
				break;
			default: 
				printf ("[FinalizeNodeMac]:: Error, Invalid mac type: abort");
				exit(1); 
	   }
	   //finalize the basic functional layers.
	   if (prog_verbosity_level()==1){
	        printf("Finalizing basic functional medium access control layer ... ");
	   }
	   if (type == NORMAL) {
	       for (i=0; i<TotNodeNo; i++) {
			 id = i+1;
			 free(WGNnode(id)->nodeMac->nodeTimer->bf_timer);
			 free(WGNnode(id)->nodeMac->nodeTimer->df_timer);
			 free(WGNnode(id)->nodeMac->nodeTimer->nav_timer);
			 free(WGNnode(id)->nodeMac->nodeTimer->if_timer);
			 free(WGNnode(id)->nodeMac->nodeTimer->tx_timer);
			 free(WGNnode(id)->nodeMac->nodeTimer->rx_timer);
			 free(WGNnode(id)->nodeMac->nodeTimer);
			 //free(WGNnode(id)->nodeMac->macMib);
			 free(WGNnode(id)->nodeMac->mac_buffer);
			 free(WGNnode(id)->nodeMac->mac_buf_index);
			 if (WGNnode(id)->nodeMac->pktTx != NULL) {
                 Dot11FrameFree(WGNnode(id)->nodeMac->pktTx);
			 }
			 if (WGNnode(id)->nodeMac->pktRsp != NULL) {
                 Dot11FrameFree(WGNnode(id)->nodeMac->pktRsp);
			 }
			 if (WGNnode(id)->nodeMac->pktRx != NULL) {
                 Dot11FrameFree(WGNnode(id)->nodeMac->pktRx);
			 }
			 free(WGNnode(id)->nodeMac);
           }
	   }
	   if (prog_verbosity_level()==1){
	       printf("[ OK ]\n");
	   }
   }

//=======================================================
//       FUNCTION:  MacSendPkt 			
//======================================================= 
    void MacSendPkt( MobileNode *node, WGN_802_11_Mac_Frame *p, unsigned int timeout)  {
 		unsigned int if_duration;   //nanosecond
		int size;
        SetTxActiveSign(node,TRUE) ;
		
         //If the node is receving a frame, it will be marked as collision error.
        if (GetRxStatus(node) != MAC_IDLE && PktRxIsEmpty(node) == FALSE) {		
            SetColErrorSign(node->nodeMac->pktRx);     
        }
        size = GetPhyFrameSize(p);
		if_duration = SecToNsec(FrameTimeComp(node, size, BYTE));
		IFTimer_Start(node, if_duration);
        TXTimer_Start(node, timeout); 
		// Send the frame to physical layer.
        MacDownPortSend(node, p);
    }

//=======================================================
//       FUNCTION:  SendDATA  	     
//======================================================= 
    void SendDATA(MobileNode *node, WGN_802_11_Mac_Frame *dot_11_frame) {  
		node->nodeStats->DataTxed += 1;
		node->nodeMac->pktTx = dot_11_frame;
		dot_11_frame = NULL;
		UpdateSeqNumber(node);
    }  

//=======================================================
//       FUNCTION:  SendACK  	     
//======================================================= 
    void SendACK(MobileNode *node, WGN_802_11_Mac_Frame *Data_frame) {
       	unsigned char *ra;
		node->nodeStats->AckTxed += 1;
		ra = GetSa(Data_frame);
        Mac_802_11_ACK_Frame(node, ra);       
    }  

//=======================================================
//       FUNCTION:   SetTxActiveSign
//       PURPOSE:    Set the value of TxActiveSign.
//======================================================= 	
  void SetTxActiveSign(MobileNode *node,WGNflag flag) {
     node->nodeMac->TxActiveSign = flag;
  }

//=======================================================
//       FUNCTION:   GetTxStatus
//======================================================= 	
  MacStatus GetTxStatus(MobileNode *node) {
     return (node->nodeMac->txStatus);
  }

//=======================================================
//       FUNCTION:   GetRxStatus
//=======================================================
  MacStatus GetRxStatus(MobileNode *node) {
     return (node->nodeMac->rxStatus);
  }

//=======================================================
//       FUNCTION:   GetTxActiveSign
//======================================================= 	
  WGNflag GetTxActiveSign(MobileNode *node) {
     return (node->nodeMac->TxActiveSign);
  }

 //=======================================================
//       FUNCTION:   GetColErrorSign
//======================================================= 	
  WGNflag GetColErrorSign(WGN_802_11_Mac_Frame *frame) {
     return (frame->pseudo_header->colErrorSign);
  }

//=======================================================
//       FUNCTION:   GetFadErrorSign
//======================================================= 	
  WGNflag GetFadErrorSign(WGN_802_11_Mac_Frame *frame) {
     return (frame->pseudo_header->fadErrorSign);
  }

//=======================================================
//       FUNCTION:   GetNoiseErrorSign
//======================================================= 	
  WGNflag GetNoiseErrorSign(WGN_802_11_Mac_Frame *frame) {
     return (frame->pseudo_header->noiseErrorSign);
  }

//=======================================================
//       FUNCTION:   SetColErrorSign
//======================================================= 	
  void SetColErrorSign(WGN_802_11_Mac_Frame *frame) {
     frame->pseudo_header->colErrorSign = TRUE;
  }

//=======================================================
//       FUNCTION:   SetFadErrorSign
//======================================================= 	
  void SetFadErrorSign(WGN_802_11_Mac_Frame *frame) {
     frame->pseudo_header->fadErrorSign = TRUE;
  }

//=======================================================
//       FUNCTION:   SetNoiseErrorSign
//======================================================= 	
  void SetNoiseErrorSign(WGN_802_11_Mac_Frame *frame) {
     frame->pseudo_header->noiseErrorSign = TRUE;
  }

//=======================================================
//       FUNCTION:   PktRxIsEmpty
//======================================================= 	
  WGNflag PktRxIsEmpty(MobileNode *node) {
    if (node->nodeMac->pktRx == NULL )
        return TRUE;
    else 
		return FALSE;
  }

//=======================================================
//       FUNCTION:   PktTxIsEmpty
//======================================================= 	
  WGNflag PktTxIsEmpty(MobileNode *node) {
    if (node->nodeMac->pktTx == NULL )
        return TRUE;
    else 
		return FALSE;
  }

//=======================================================
//       FUNCTION:   PktRtsIsEmpty
//======================================================= 	
  WGNflag PktRtsIsEmpty(MobileNode *node) {
    if (node->nodeMac->pktRts == NULL )
        return TRUE;
    else 
		return FALSE;
  }

//=======================================================
//       FUNCTION:   PktRspIsEmpty
//======================================================= 	
  WGNflag PktRspIsEmpty(MobileNode *node) {
    if (node->nodeMac->pktRsp == NULL )
        return TRUE;
    else 
		return FALSE;
  } 

//=======================================================
//       FUNCTION:   PktHasFadError
//======================================================= 	
  WGNflag PktRxHasFadError(MobileNode *node) {
    return (node->nodeMac->pktRx->pseudo_header->fadErrorSign);
  } 

//=======================================================
//       FUNCTION:   PktHasColError
//======================================================= 	
  WGNflag PktRxHasColError(MobileNode *node) {
    return (node->nodeMac->pktRx->pseudo_header->colErrorSign);
  } 

//=======================================================
//       FUNCTION:   PktHasNoiseError
//======================================================= 	
  WGNflag PktRxHasNoiseError(MobileNode *node) {
    return (node->nodeMac->pktRx->pseudo_header->noiseErrorSign);
  } 

//=======================================================
//       FUNCTION:   GetPhyFrameSize		
//======================================================= 
  int GetPhyFrameSize(WGN_802_11_Mac_Frame *pkt) {
       return (pkt->pseudo_header->phy_size);
  }

//=======================================================
//       FUNCTION:   GetCPThreshold		
//======================================================= 
  double GetCPThreshold(MobileNode *node) {
       return (node->nodePhy->nodeWCard->CPThresh);
  }

//=======================================================
//       FUNCTION:   IsOverCPThreshold                	
//======================================================= 
  WGNflag IsOverCPThreshold(MobileNode *node, 
	                                             WGN_802_11_Mac_Frame *frame_1, 
												 WGN_802_11_Mac_Frame *frame_2) {
	  //double threshold;
	  double dif;
	  dif = (frame_1->pseudo_header->rx_pwr) - (frame_2->pseudo_header->rx_pwr); 
	  //dif = (frame_1->pseudo_header->rx_pwr) - WToDB(DBToW(frame_2->pseudo_header->rx_pwr) + DBToW(noise)/1000);
	  if ( dif>= GetCPThreshold(node))
	       return (TRUE);
	  else
           return (FALSE);
  }

//=======================================================
//       FUNCTION:   GetID
//======================================================= 
    int GetID(unsigned char *mac_addr) {
	int i, j;
	for (i=0; i<TotNodeNo; i++) {
	    /*printf("MAC addr - "); for(j=0; j<6; j++) printf("%d.", mac_addr[j]);
	    printf("\n");
	    printf("AddrtoID - "); for(j=0; j<6; j++) printf("%d.",  AddrToIDMap[i].mac_addr[j]);
	    printf("\n");
	    
	    printf("MAC addr - ");
	    for (j = 0; j < MAC_ADDR_LEN; j++)
		printf("%d-", mac_addr[j]);
	    printf("AddrtoID - ");
	    for (j = 0; j < MAC_ADDR_LEN; j++)
		printf("%d-", AddrToIDMap[i].mac_addr[j]);
	    printf("\n");	    
	    */
	  
   	    if(memcmp(AddrToIDMap[i].mac_addr, mac_addr, MAC_ADDR_LEN)==0) {
		//printf("\nhere\n\n");
   	        return (AddrToIDMap[i].id);
   	    }
	}
   	//printf("Miss 1\n");
   	if(memcmp(MAC_BROADCAST_ADDR, mac_addr, MAC_ADDR_LEN)==0) {
	    return (BROADCASTID);
   	}
	//printf("Miss 2\n");	
  
	printf("[GetID]:: Error, can not find this node id.\n\n\n");
	return (-1); //return (AddrToIDMap[2].id);
   }
 
//=======================================================
//       FUNCTION:   CheckIfIsBroadCastPkt     		
//======================================================= 
	WGNflag CheckIfIsBroadCastPkt(WGN_802_11_Mac_Frame *p) {
		int tmp;
		tmp = memcmp(p->pseudo_header->DA, MAC_BROADCAST_ADDR, MAC_ADDR_LEN);
        if (tmp == 0) {
			return(TRUE);   
		}
		else
			return(FALSE);		
    }

//=======================================================
//       FUNCTION:   MacAddrIsSame     		
//======================================================= 
	WGNflag MacAddrIsSame(char *addr_1, char *addr_2) {
		int tmp;
		tmp = memcmp(addr_1, addr_2, MAC_ADDR_LEN);
        if (tmp == 0)
        	return (TRUE);
		else 
			return (FALSE);		
    }

//=======================================================
//       FUNCTION:   MacDownPortSend     		
//=======================================================
  void MacDownPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame) {

	 verbose(4, "[MacDownPortSend]:: NODE %d: MAC layer sends a packet to PHY layer.", node->Id);

     if (prog_verbosity_level()==6) {
		switch(GetFcSubtype (frame)) {
			case MAC_SUBTYPE_RTS:
				printf("[MacDownPortSend]:: RTS from node %d to node %d\n", 
				node->Id, frame->pseudo_header->rxid);					
				break;
			case MAC_SUBTYPE_CTS:
				printf("[MacDownPortSend]:: CTS from node %d to node %d\n", 
				node->Id, frame->pseudo_header->rxid);
				break;
			case MAC_SUBTYPE_DATA:
				printf("[MacDownPortSend]:: DATA from node %d to node %d\n", 
				node->Id, frame->pseudo_header->rxid);
				break;
			case MAC_SUBTYPE_ACK:
				printf("[MacDownPortSend]:: ACK from node %d to node %d\n", 
				node->Id, frame->pseudo_header->rxid);
				break;
			default:
				printf ("[MacDownPortSend]:: Error, Invalid frame type!\n");
				exit(1);
		 }
	 }		
     switch(SYS_INFO->mac_info->macType) {
		case CSMA:
            CSMAMacDownPortSend(node, frame);
			break;
		case DCF_802_11:
			S80211DcfMacDownPortSend(node, frame);
			break;
		case NONE:
			NoMacDownPortSend(node, frame);
			break;
		default: 
			printf ("[MacDownPortSend]:: Error, Invalid mac type!\n");
			exit(1); 
	 }
  }  

//=======================================================
//       FUNCTION:   MacDownPortRecv     		
//=======================================================
  void MacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame) {

	 verbose(4, "[MacDownPortRecv]:: NODE %d: MAC layer receives a packet from PHY layer.", node->Id);
	 switch(SYS_INFO->mac_info->macType) {
		case CSMA:	
            CSMAMacDownPortRecv(node, frame); 
			break;
		case DCF_802_11:	
			S80211DcfMacDownPortRecv(node, frame);
			break;
		case NONE:
			NoMacDownPortRecv(node, frame);
			break;
		default: 
			printf ("[MacDownPortRecv]:: Error, Invalid frame type!\n");
			exit(1); 
	 }
  }  

//=======================================================
//       FUNCTION:   MacUpPortSend   		
//=======================================================
  void MacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame) {

	 verbose(4, "[MacUpPortSend]:: NODE %d: MAC layer sends a packet to LLC layer.", node->Id);
	 switch(SYS_INFO->mac_info->macType) {
		case CSMA:
            CSMAMacUpPortSend(node, frame);
			break;
		case DCF_802_11:
			S80211DcfMacUpPortSend(node, frame);
			break;
		case NONE:
			NoMacUpPortSend(node, frame);
			break;
		default: 
			printf ("[MacUpPortSend]:: Error, Invalid frame type!\n"); 
			exit(1); 
     }
  }  

//=======================================================
//       FUNCTION:   MacUpPortRecv   		
//=======================================================
  void MacUpPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame) {

	 verbose(4, "[MacUpPortRecv]:: NODE %d: MAC layer receives a packet from LLC layer.", node->Id);
	 if (ThroutputComSign == TRUE) {
	     node->nodeStats->TotTxByteNo = node->nodeStats->TotTxByteNo + frame->pseudo_header->phy_size;
	 }
	 switch(SYS_INFO->mac_info->macType) {
		case CSMA:
			verbose(5, "[MacUpPortRecv]:: Packet from node %d to node %d is handled by the 'CSMA Module'", 
			node->Id, frame->pseudo_header->rxid);		
            CSMAMacUpPortRecv(node,frame);
			break;
		case DCF_802_11:
			verbose(5, "[MacUpPortRecv]:: Packet from node %d to node %d is handled by the '802.11Dcf Module'", 
			node->Id, frame->pseudo_header->rxid);	
			S80211DcfMacUpPortRecv(node, frame);
			break;
		case NONE:
			verbose(5, "[MacUpPortRecv]:: Packet from node %d to node %d is handled by the 'NONE Module'", 
			node->Id, frame->pseudo_header->rxid);	
			NoMacUpPortRecv(node, frame);
			break;
		default: 
			printf ("[MacUpPortRecv]:: Error, Invalid frame type!\n");
			exit(1); 
	}
  }

//=======================================================
//       FUNCTION:   ChMacMode   		
//=======================================================
  void ChMacMode(MAC_type type) {
	 int id;
	 int verbose;
	 verbose = prog_verbosity_level();
	 prog_set_verbosity_level(0);
	 for(id=1; id<=TotNodeNo; id++) {	 
	      pthread_mutex_lock(&(WGNnode(id)->nodeLlc->ltom_array_mutex));
		  pthread_mutex_lock(&(WGNnode(id)->nodeLlc->ltou_array_mutex));	
	 }
     FinalizeEvent();
	 FinalizeNodeMac(NORMAL);
	 SYS_INFO->mac_info->macType = type;
	 IniEvent();
	 IniNodeMac(NORMAL); 
	 for(id=1; id<=TotNodeNo; id++) {	 
	      pthread_mutex_unlock(&(WGNnode(id)->nodeLlc->ltom_array_mutex));
		  pthread_mutex_unlock(&(WGNnode(id)->nodeLlc->ltou_array_mutex));	
	 }
	 prog_set_verbosity_level(verbose);
  }
