/*
 * NAME: 802_11_frame.c 
 * FUNCTION: Collection of functions that handle the IEEE 802.11 frames 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  802_11_fame.c
//======================================================= 
  #include "802_11_frame.h"

//=======================================================
//       FUNCTION:   Set_WGN_802_11_Mac_Pseudo_Frame_Control
//======================================================= 
    //Set frame control protocol version 
	void set_fc_protocol_version(WGN_802_11_Mac_Pseudo_Frame_Control *fc, int version) { 
		fc->fc_protocol_version = version; 
	}
	//Set frame control type
	void set_fc_type(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int type) { 
		fc->fc_type = type; 
	}
	//Set frame control subtype 
	void set_fc_subtype(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int subtype) {
		fc->fc_subtype = subtype; 
	}
    //Set frame control to ds field 
    void set_fc_to_ds(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) { 
	    fc->fc_to_ds = flag; 
	}
	//Set frame control frome ds field
	void set_fc_from_ds(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) { 
		fc->fc_from_ds = flag; 
	}
    //Set frame control fragmentation field
	void set_fc_more_frag(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) { 
		fc->fc_more_frag = flag; 
	}
    //Set frame control retry field
    void set_fc_retry(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) { 
		fc->fc_retry = flag;
	}
	//Set frame control power management field 
	void set_fc_pwr_mgt(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) { 
		fc->fc_pwr_mgt = flag; 
	}
    //Set frame control more_data field
	void set_fc_more_data(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) {
		fc->fc_more_data = flag; 
	}
    //Set frame control WEP field
	void set_fc_wep(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) { 
		fc->fc_wep = flag; 
	}
	//Set frame control order field
	void set_fc_order(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag) { 
		fc->fc_order = flag; 
	}

//=======================================================
//       FUNCTION:   Set_WGN_802_11_Mac_Pseudo_Frame_Control
//======================================================= 	
void Set_WGN_802_11_Mac_Pseudo_Frame_Control(WGN_802_11_Mac_Pseudo_Frame_Control* fc, WGN_802_11_Mac_Frame_Type frame_type) {
	int version;
	int type;
	int subtype;

	version = MAC_PROTOCOL_VERSION;
    set_fc_protocol_version(fc, version); 
	
    switch(frame_type) {
        case MAC_DATA_FRAME:
 			type = MAC_TYPE_DATA;
            break;
		case MAC_RTS_FRAME:
 			type = MAC_TYPE_CONTROL;
            break; 
        case MAC_CTS_FRAME:
			type = MAC_TYPE_CONTROL;
            break;
        case MAC_ACK_FRAME:
			type = MAC_TYPE_CONTROL;
            break;
        default:
            printf("[Set_WGN_802_11_Mac_Pseudo_Frame_Control]:: Error, Invalid frame type!\n");
    }
	set_fc_type(fc, type); 

    switch(frame_type) {
        case MAC_DATA_FRAME:
 			subtype = MAC_SUBTYPE_DATA;
            break;
		case MAC_RTS_FRAME:
 			subtype = MAC_SUBTYPE_RTS;
            break; 
        case MAC_CTS_FRAME:
			subtype = MAC_SUBTYPE_CTS;
            break;
        case MAC_ACK_FRAME:
			subtype = MAC_SUBTYPE_ACK;
            break;
        default:
            printf("[Set_WGN_802_11_Mac_Pseudo_Frame_Control]:: Error, Invalid frame type!\n");
    }
	set_fc_subtype(fc, subtype);

	//Just for ADHOC mode !!!
    set_fc_to_ds(fc, 0);
	set_fc_from_ds(fc, 0); 
	
	//no fragment implementation so far
	set_fc_more_frag(fc, 0);
	//for the beginning of the transmission it should be set to be 0
    set_fc_retry(fc, 0); 
	//no psm implementation so far
	set_fc_pwr_mgt(fc, 0);
	//this param is related to the psm
	set_fc_more_data(fc, 0);
	//no wep implementation so far
	set_fc_wep(fc, 0);
	//no fragment implementation so far
	set_fc_order(fc , 0);
}

//=======================================================
//       FUNCTION:   Set_WGN_802_11_Mac_Pseudo_Sequence_Control 
//======================================================= 	
void  Set_WGN_802_11_Mac_Pseudo_Sequence_Control (MobileNode *node,
         WGN_802_11_Mac_Pseudo_Sequence_Control* sc) {
		 //no implementation about fragment number so far
		 sc->sc_fragment_number = 0;
		 sc->sc_sequence = GetSeqNumber(node);
}

//=======================================================
//       FUNCTION:   UpdateSeqNumber  
//======================================================= 
  void UpdateSeqNumber(MobileNode *node) {
	 // Range for sequence number is [0,4095]
	 if (node->nodeMac->seq_no < MAX_SEQ_NO)             
	     node->nodeMac->seq_no = node->nodeMac->seq_no + 1;
	 else
         node->nodeMac->seq_no = 0;
  }

//=======================================================
//       FUNCTIONS:   Get all kinds of fields value of the frame 
//======================================================= 
  int GetSeqNumber(MobileNode *node) {
	 return (node->nodeMac->seq_no);
  }

  int GetFctype(WGN_802_11_Mac_Frame *p) {
     return (p->pseudo_header->fc.fc_type);
  }

  int GetFcSubtype(WGN_802_11_Mac_Frame *p) {
     return (p->pseudo_header->fc.fc_subtype);
  }
  
  unsigned int GetDuration(WGN_802_11_Mac_Frame *p) {
     return (p->pseudo_header->duration);
  }

  char *GetSa(WGN_802_11_Mac_Frame *p) {
     return (p->pseudo_header->SA);
  }
  
  char *GetDa(WGN_802_11_Mac_Frame *p) {
     return (p->pseudo_header->DA);
  }

  char *GetTa(WGN_802_11_Mac_Frame *p) {
     return (p->pseudo_header->TA);
  }
  
  char *GetRa(WGN_802_11_Mac_Frame *p) {
     return (p->pseudo_header->RA);
  }	
  
  unsigned char *Dot_3_GetDa(WGN_802_3_Mac_Frame *p) {
     return (p->header.dst);
  }
  
  unsigned char *Dot_3_GetSa(WGN_802_3_Mac_Frame *p) {
     return (p->header.src);
  }

//=======================================================
//       FUNCTION:   Time Computation							   
//       PURPOSE:    
//======================================================= 
    double FrameTimeComp(MobileNode *node, int length, Pkt_Unit unit) { //seconds
		switch  (unit) {
            case BYTE: 
				return (8 * length / node->nodePhy->nodeWCard->bandwidth);
            case BIT: 
                return (length / node->nodePhy->nodeWCard->bandwidth);
            default:
                printf("[FrameTimeComp]:: Invalid scale for the traffic stream!\n");
        }
		printf("[FrameTimeComp]:: Invalid scale for the traffic stream!\n");
		return (-1);
    }

	double TX_Time(MobileNode *node) {
        double time;
		int length;
		length = node->nodeMac->pktTx->pseudo_header->mac_size;
		time = FrameTimeComp(node, length, BYTE) + 
			        (SYS_INFO->phy_info->PreambleLength+SYS_INFO->phy_info->PLCPHeaderLength)/1000000.0;
        return (time);
    }

	double RX_Time(MobileNode *node) {
        double time;
		int length;
		length = node->nodeMac->pktRx->pseudo_header->mac_size;
		time = FrameTimeComp(node, length, BYTE) +  
		            (SYS_INFO->phy_info->PreambleLength+SYS_INFO->phy_info->PLCPHeaderLength)/1000000.0;
        return (time);
    }

	double Frame_Time(MobileNode *node, WGN_802_11_Mac_Frame *frame) {
        double time;
		int length;
		length = frame->pseudo_header->mac_size;
		time = FrameTimeComp(node, length, BYTE) + 
			        (SYS_INFO->phy_info->PreambleLength+SYS_INFO->phy_info->PLCPHeaderLength)/1000000.0;
		return (time);
    }

//=======================================================
//       FUNCTIONS: Calculate the length for all kinds of frames   
//======================================================= 
    void SetDataHdrLen() {  //bytes
        MAC_DATA_HDR_LEN = SYS_INFO->mac_info->MAC_Data_Frame_Header_Length+
			                                    SYS_INFO->mac_info->MAC_Frame_Tailer_Length;

        PHY_DATA_HDR_LEN = (SYS_INFO->phy_info->PreambleLength>>3)+
			                                    (SYS_INFO->phy_info->PLCPHeaderLength>>3)+
			                                    SYS_INFO->mac_info->MAC_Data_Frame_Header_Length+
			                                    SYS_INFO->mac_info->MAC_Frame_Tailer_Length;
    }

    void SetRTSLen() {  //bytes
		MAC_RTS_LEN =  SYS_INFO->mac_info->MAC_RTS_Frame_Header_Length+
			                         SYS_INFO->mac_info->MAC_Frame_Tailer_Length;

        PHY_RTS_LEN =  (SYS_INFO->phy_info->PreambleLength>>3)+
			                         (SYS_INFO->phy_info->PLCPHeaderLength>>3)+
			                         SYS_INFO->mac_info->MAC_RTS_Frame_Header_Length+
			                         SYS_INFO->mac_info->MAC_Frame_Tailer_Length;
    }
    
	void SetCTSLen() {   //bytes
		MAC_CTS_LEN =   SYS_INFO->mac_info->MAC_CTS_Frame_Header_Length+
			                         SYS_INFO->mac_info->MAC_Frame_Tailer_Length;
        
		PHY_CTS_LEN =  (SYS_INFO->phy_info->PreambleLength>>3)+
			                         (SYS_INFO->phy_info->PLCPHeaderLength>>3)+
			                         SYS_INFO->mac_info->MAC_CTS_Frame_Header_Length+
			                         SYS_INFO->mac_info->MAC_Frame_Tailer_Length;
    }
   
	void SetACKLen() {   //bytes
        MAC_ACK_LEN =  SYS_INFO->mac_info->MAC_ACK_Frame_Header_Length+
			                         SYS_INFO->mac_info->MAC_Frame_Tailer_Length;

		PHY_ACK_LEN = (SYS_INFO->phy_info->PreambleLength>>3)+
			                         (SYS_INFO->phy_info->PLCPHeaderLength>>3)+
			                         SYS_INFO->mac_info->MAC_ACK_Frame_Header_Length+
			                         SYS_INFO->mac_info->MAC_Frame_Tailer_Length;
	}

//=======================================================
//       FUNCTIONS:   Calculate the transmission delay for different kinds 
//                                  of MAC-level frames
//======================================================= 
    void SetRTSTime(double bandwidth) {  // seconds
        SetRTSLen();
		RTS_Time = 8* MAC_RTS_LEN / bandwidth + 8*(PHY_RTS_LEN-MAC_RTS_LEN)/1000000.0;
    }
    
    void SetCTSTime(double bandwidth) {  // seconds
        SetCTSLen();
        CTS_Time = 8*MAC_CTS_LEN / bandwidth + 8*(PHY_CTS_LEN-MAC_CTS_LEN)/1000000.0;
    }
    
    void SetACKTime(double bandwidth) { // seconds
        SetACKLen();
		ACK_Time = 8 * MAC_ACK_LEN / bandwidth + 8*(PHY_ACK_LEN-MAC_ACK_LEN)/1000000.0;		 
    }

//=======================================================
//       FUNCTION:   Mac_802_11_RTS_Frame	 
//       PURPOSE:    Create Mac_802_11_RTS_Frame
//======================================================= 
  void Mac_802_11_RTS_Frame( MobileNode *node, unsigned char *ra, unsigned char *ta) {
		 WGN_802_11_Mac_Pseudo_Header *hdr;
		 
		 node->nodeMac->pktRts = (WGN_802_11_Mac_Frame*)malloc(sizeof(WGN_802_11_Mac_Frame));
		 
		 //construct the pseudo hdr 
		 node->nodeMac->pktRts->pseudo_header = (WGN_802_11_Mac_Pseudo_Header *)malloc(sizeof(WGN_802_11_Mac_Pseudo_Header));
		 hdr = node->nodeMac->pktRts->pseudo_header;
		 Set_WGN_802_11_Mac_Pseudo_Frame_Control(&(hdr->fc), MAC_RTS_FRAME); 
		 hdr->duration = RTS_DURATION (node);
		 memcpy(hdr->RA, ra, MAC_ADDR_LEN);
		 memcpy(hdr->TA, ta, MAC_ADDR_LEN);
		 memset(hdr->DA, 0, MAC_ADDR_LEN);
		 memset(hdr->SA, 0, MAC_ADDR_LEN);
		 memset(hdr->BSSID, 0, MAC_ADDR_LEN);

		 hdr->fcs = 0;
		 //Get the node id from the address group
		 hdr->srcid = 0;
	     hdr->dstid = 0;
	     hdr->txid = GetID(hdr->TA);
	     hdr->rxid = GetID(hdr->RA);

		 hdr->colErrorSign = FALSE;
		 hdr->fadErrorSign = FALSE;
		 hdr->noiseErrorSign = FALSE;
		 hdr->mac_size = MAC_RTS_LEN;
		 hdr->phy_size = PHY_RTS_LEN;
		 
		 //construct the real frame body
		 node->nodeMac->pktRts->frame_body = NULL;
    }

//=======================================================
//       FUNCTION:   Mac_802_11_CTS_Frame	 
//       PURPOSE:    Create Mac_802_11_CTS_Frame
//======================================================= 
  void Mac_802_11_CTS_Frame( MobileNode *node, unsigned int rts_duration, unsigned char *ra) {
		 WGN_802_11_Mac_Pseudo_Header *hdr;
	     
		  node->nodeMac->pktRsp = (WGN_802_11_Mac_Frame*)malloc(sizeof(WGN_802_11_Mac_Frame));

		 //construct the pseudo hdr 
		 node->nodeMac->pktRsp->pseudo_header = (WGN_802_11_Mac_Pseudo_Header *)malloc(sizeof(WGN_802_11_Mac_Pseudo_Header));
		 hdr = node->nodeMac->pktRsp->pseudo_header;
		 Set_WGN_802_11_Mac_Pseudo_Frame_Control(&(hdr->fc), MAC_CTS_FRAME); 
		 hdr->duration = CTS_DURATION (rts_duration);
		 memcpy(hdr->RA, ra, 6);
		 memset(hdr->TA, 0, MAC_ADDR_LEN);
		 memset(hdr->DA, 0, MAC_ADDR_LEN);
		 memset(hdr->SA, 0, MAC_ADDR_LEN);
		 memset(hdr->BSSID, 0, MAC_ADDR_LEN);
		 hdr->fcs = 0;
		 //Get the node id from the address group
		 hdr->srcid = 0;
	     hdr->dstid = 0;
	     hdr->txid = 0;
	     hdr->rxid = GetID(hdr->RA);
		 
		 hdr->colErrorSign = FALSE;
		 hdr->fadErrorSign = FALSE;
		 hdr->noiseErrorSign = FALSE;
		 hdr->mac_size = MAC_CTS_LEN;
		 hdr->phy_size = PHY_CTS_LEN;
		 
		 //construct the real frame body
		 node->nodeMac->pktRsp->frame_body = NULL;
  }

//=======================================================
//       FUNCTION:   Mac_802_11_ACK_Frame	 
//       PURPOSE:    Create Mac_802_11_ACK_Frame
//======================================================= 
  void Mac_802_11_ACK_Frame(MobileNode *node, unsigned char *ra) {
		 WGN_802_11_Mac_Pseudo_Header *hdr;
	     
		 node->nodeMac->pktRsp = (WGN_802_11_Mac_Frame*)malloc(sizeof(WGN_802_11_Mac_Frame));

		 //construct the pseudo hdr 
		 node->nodeMac->pktRsp->pseudo_header = (WGN_802_11_Mac_Pseudo_Header *)malloc(sizeof(WGN_802_11_Mac_Pseudo_Header));
		 hdr = node->nodeMac->pktRsp->pseudo_header;
         Set_WGN_802_11_Mac_Pseudo_Frame_Control(&(hdr->fc), MAC_ACK_FRAME); 
		 hdr->duration = ACK_DURATION ();
		 memcpy(hdr->RA, ra,  MAC_ADDR_LEN);
		 memset(hdr->TA, 0, MAC_ADDR_LEN);
		 memset(hdr->DA, 0, MAC_ADDR_LEN);
		 memset(hdr->SA, 0, MAC_ADDR_LEN);
		 memset(hdr->BSSID, 0, MAC_ADDR_LEN);
		 hdr->fcs = 0;
		 //Get the node id from the address group
		 hdr->srcid = 0;
	     hdr->dstid = 0;
	     hdr->txid = 0;
	     hdr->rxid = GetID(hdr->RA);
		 
		 hdr->colErrorSign = FALSE;
		 hdr->fadErrorSign = FALSE;
		 hdr->noiseErrorSign = FALSE;
		 hdr->mac_size = MAC_ACK_LEN;
		 hdr->phy_size = PHY_ACK_LEN;
		 
		 //construct the real frame body
		 node->nodeMac->pktRsp->frame_body = NULL;
    }

//=======================================================
//       FUNCTION:   Get_Payload_Length
//======================================================= 
int Get_Payload_Length (WGN_802_3_Mac_Frame *dot_3_frame) {
   int len;
   len = dot_3_frame->payload_len;
   return (len);
}

//=======================================================
//       FUNCTION:   Dot11FrameFree
//       PURPOSE:    Free the memory space of the 802.11 frame with  
//                               recursive structure
//======================================================= 
void Dot11FrameFree(WGN_802_11_Mac_Frame *frame) { 
        switch(GetFcSubtype (frame)) {
		    case MAC_SUBTYPE_RTS:	  
			   free(frame->pseudo_header);	
			   break;
            case MAC_SUBTYPE_CTS: 
			   free(frame->pseudo_header);
               break;
			case MAC_SUBTYPE_DATA:
			   free(frame->pseudo_header);
			   free(frame->frame_body->data);
			   free(frame->frame_body);
			   break;
            case MAC_SUBTYPE_ACK:
			   free(frame->pseudo_header);
               break;
            default:
			   printf ("[Dot11FrameFree]:: Error, Invalid frame subtype!");
			   exit(1);
        } 
		free(frame);
}

//=======================================================
//       FUNCTION:   Dot3FrameFree	
//       PURPOSE:    Free the memory space of the 802.3 frame with  
//                               recursive structure
//======================================================= 
void Dot3FrameFree(WGN_802_3_Mac_Frame *frame) { 
		free(frame->data);
		free(frame);
}
