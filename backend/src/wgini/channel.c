/*
 * NAME: channel.c 
 * FUNCTION: Collection of functions of the basic functional channel
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  channel.c
//======================================================= 
  #include "channel.h"

//=======================================================
//       Function Part
//======================================================= 
//=======================================================
//       FUNCTION:   PrintChannelFading
//       PURPOSE:    Record the channel fading information into the output
//                               file
//======================================================= 
	void PrintChannelFading(double *fad, int i) { 
		int j;
		FILE* in;  

		in = fopen(ch_rep_name, "a+");
		if(in==NULL) {
			printf("[PrintChannelFading]:: Error, Can't create or open the file.\n");
			return;
		}
		if (i==1) {
			fprintf (in, "==================================="); 
			fprintf (in, "\nChannel Fading Factor was updated ...");
			fprintf (in, "\n===================================");
		}
		fprintf (in, "\nNode %d: ", i);
		for (j=0; j<TotNodeNo; j++) {
			   fprintf (in, "%f   ", fad[j]);
		} 
		fprintf (in, "\n");  
		fclose(in);
	}

//=======================================================
//       FUNCTION:   ChannelProcess
//       PURPOSE:    Update the channel status based on the time unit.
//======================================================= 
    void ChannelProcess () {
		if (GetRayleighSign() == ON) {
		    FadingComp(Channel->channelFad->pha,Channel->channelFad->incr,
				                   Channel->channelFad->coef,Channel->channelFad->fad);
		}			
    }

//=======================================================
//       FUNCTION:   IniChannel
//======================================================= 
    void IniChannel() {
		//initialization of the basic functional channel.
		if (prog_verbosity_level()==1){
			PrintSystemInfo ("Initializing the network channel of wireless GINI ... ");
			printf("[IniChannel]:: Initializing basic functional channel ... ");
		}	
		Ch_update_remain = SecToNsec(SYS_INFO->time_info->Ch_timeunit);

		Channel = (ChannelMib *)malloc(sizeof(ChannelMib));
         
		//current version only support the identical bandwidth. (change it in the future)
        Channel->channelbandwidth = WGNnode(1)->nodePhy->nodeWCard->bandwidth;
        Channel->channelFadPrintSign = PrintChFadSign;
		IniChannelLinkStateMatrix();

		if (prog_verbosity_level()==1){
			printf("[ OK ]\n");
		}
	    //initialization of the modules.
		if (prog_verbosity_level()==2){
		    PrintSystemInfo ("Initializing the channel modules ... ");
	    }	
		IniChannelAwgn();
		IniChannelPropagation();
		IniChannelFading()	;
	}

//=======================================================
//       FUNCTION:   FinalizeChannel
//======================================================= 
    void FinalizeChannel() {
		int i;
		//finalize the attached channel modules
		if (prog_verbosity_level()==2){
		    PrintSystemInfo ("Finalizing the channel modules ... ");
	    }	
		FinalizeChannelAwgn();
		FinalizeChannelPropagation();
		FinalizeChannelFading();
		
		//finalize the basic functional channel
		if (prog_verbosity_level()==1){
			PrintSystemInfo ("Finalizing the network channel of wireless GINI ... ");
			printf("[FinalizeChannel]:: Finalizing basic functional channel ... ");		
		}	
		for(i=0; i<TotNodeNo; i++){
			 free(Channel->linkmatrix[i]);
	    }
		free(Channel->linkmatrix);		
		free(Channel);
		if (prog_verbosity_level()==1){
		    printf("[ OK ]\n");
		}
	}

//=======================================================
//       FUNCTION:   ChannelDelivery
//======================================================= 
    void ChannelDelivery(int src_id, int dst_id, WGN_802_11_Mac_Frame *frame) {
		double tmpPwr;								   //(db)
		unsigned int prop_delay;	                   //nanosecond
		WGNTime link_end_time;
        
		verbose(4, "[ChannelDelivery]:: Packet from node %d to node %d is deliveried by channel", src_id, dst_id);

	    //Calculate the rx power by "propagation module" & "fading module"
	    tmpPwr = GetRxPwr(WGNnode(src_id), WGNnode(dst_id));			 
		frame->pseudo_header->dstid = dst_id;
		SetPktTxPwr(frame, GetTxPwr(WGNnode(src_id)));
		SetPktRxPwr(frame, tmpPwr);
	    if (IsOverRXThresh(DBToW(tmpPwr), WGNnode(dst_id))==FALSE) { 
		     SetFadErrorSign(frame);	  //mark this frame as fading error
		}
		
 		//Marking demodulation error based on noise power by "awgn module"
		//count all the packets with "collison error" and "pwr too low error" out,
		//the only packet left should be only affected by "AWGN noise" or 
		//"survived from capture". The AWGNPktHandler can handler the pkt with
		//"AWGN noise" by theoretical error probability formula. But when handle the
		//latter packets, error diffenrence will be introduced, because the interference
		//changes the characters of the channel. Fortunately, the probability that the 
		// latter comes out will be at the order of 10^(-2)*10^(-4~-8) 
		//(P{collison happens}*P{error probabitlity with SNR more than CPThreshold}).
		//So it will not impact on the system performance.
		if (GetAwgnSign() == ON) {
			AWGNPktHandler (frame);    
		}
		//Emulate the propagation delay.
		verbose(5, "[ChannelDelivery]:: Packet from node %d to node %d in propagation delay procedure is handled by the channel.", src_id, dst_id);
		SetLinkStartTime(frame, GetTime());
		prop_delay = SecToNsec(GetPropDelay(WGNnode(src_id), WGNnode(dst_id)));
		link_end_time = LocalTimeAdd (GetTime(), prop_delay);
		SetLinkEndTime(frame, link_end_time);	
		
		if (frame == NULL) {
			printf("[ChannelDelivery]:: Duplicate a NULL packet from node %d to node %d.\n", src_id, dst_id);
		}
		AddNewEventToList(dst_id, START_RX, link_end_time, (void*)frame); 
	}

//=======================================================
//       FUNCTION:   SetDefJamInt
//       PURPOSE:    Add some interference on the specified node manually
//======================================================= 
    void SetJamInt (int id, double interference) {
        WGNnode(id)->nodePhy->nodeAntenna->intPwr += interference;
		WGNnode(id)->nodePhy->nodeAntenna->jamInt = interference;
	}

//=======================================================
//       FUNCTION:   KillJamInt
//       PURPOSE:    Remove all the "jam" interference power from the 
//                               specified node
//======================================================= 
    void KillJamInt (int id) {
        WGNnode(id)->nodePhy->nodeAntenna->intPwr -= WGNnode(id)->nodePhy->nodeAntenna->jamInt;
		WGNnode(id)->nodePhy->nodeAntenna->jamInt = 0;
        rx_resume(WGNnode(id));
		CheckBFTimer(WGNnode(id));
	}

//=======================================================
//       FUNCTION:  GetPropDelay
//       PURPOSE:   Compute the channel propagation delay.
//======================================================= 
double GetPropDelay(MobileNode *tx, MobileNode *rx) {    
    double dist;
    dist = DistComp(tx->nodePhy->nodeMobility->curPosition, rx->nodePhy->nodeMobility->curPosition);
	return (dist/WAVESPD);
}

//=======================================================
//       FUNCTION:  GetPropType
//=======================================================
	Prop_type GetPropType() {
	    return  (Channel->channelProp->prop_type);
	}

//=======================================================
//       FUNCTION:  SetPropType
//=======================================================
	void SetPropType(Prop_type type) {
	    Channel->channelProp->prop_type = type;
	}

//=======================================================
//       FUNCTION:  GetRayleighSign
//=======================================================
	Switch GetRayleighSign() {
	    return  (Channel->channelFad->switcher);
	}

//=======================================================
//       FUNCTION:  GetRayleighSign
//=======================================================
	void SetRayleighSign(Switch state) {
	    Channel->channelFad->switcher = state;
	}

//=======================================================
//       FUNCTION:  GetAwgnSign
//=======================================================
	Switch GetAwgnSign() {
	    return  (Channel->channelAwgn->switcher);
	}

//=======================================================
//       FUNCTION:  SetAwgnSign
//=======================================================
	void SetAwgnSign(Switch state) {
	    Channel->channelAwgn->switcher = state;
	}

//=======================================================
//       FUNCTION:  GetAwgnSign
//=======================================================
	Awgn_Mode GetAwgnMode() {
	    return  (Channel->channelAwgn->mode);
	}

//=======================================================
//       FUNCTION:  GetAwgnSign
//=======================================================
	void SetAwgnMode(Awgn_Mode mode) {
	    Channel->channelAwgn->mode = mode;
	}

//=======================================================
//       FUNCTION:   SetLinkStartTime    	
//======================================================= 
  void SetLinkStartTime(WGN_802_11_Mac_Frame *frame, WGNTime link_start_time) {
      frame->pseudo_header->link_start_time = link_start_time;
  }

//=======================================================
//       FUNCTION:   SetLinkEndTime    	
//======================================================= 
  void SetLinkEndTime(WGN_802_11_Mac_Frame *frame, WGNTime link_end_time) {
      frame->pseudo_header->link_end_time = link_end_time;
  }

//=======================================================
//       FUNCTION:  INTTimeoutHandler
//======================================================= 
  void INTTimeoutHandler( MobileNode * node, WGN_802_11_Mac_Frame *frame) { 
	   node->nodePhy->nodeAntenna->intPwr -= DBToW(GetPktRxPwr(frame));
	   Dot11FrameFree(frame);
       if (node->nodePhy->nodeAntenna->intPwr < GetCSThreshold(node) / IFACTOR) 
           node->nodePhy->nodeAntenna->intPwr = 0.0;
       if (GetRxStatus(node) == MAC_RECV) {
            if ((IsOverCSThresh(node->nodePhy->nodeAntenna->intPwr, node)==FALSE) && (node->nodeMac->pktRx) == NULL) {
                SetRxStatus(node,MAC_IDLE);
                PktErrHandler(node); 
            }    
       }
  }

//=======================================================
//       FUNCTION:   IniLinkStateMatrix
//       PURPOSE:    Initialize the Rayleigh fading matrix 
//======================================================= 
	void IniChannelLinkStateMatrix() {
		int i,j;
		Channel->linkmatrix=(int **)malloc(TotNodeNo*sizeof(int *));
		if(Channel->linkmatrix==NULL) {
		puts("[IniChannelLinkStateMatrix]:: Malloc error");
		exit(1);
		}
		for(i=0; i<TotNodeNo; i++){
			 Channel->linkmatrix[i]=(int *)malloc(TotNodeNo*sizeof(int));
			 if(Channel->linkmatrix[i]==NULL) {
				puts("[IniChannelLinkStateMatrix]:: Malloc error");
				exit(1);
			 }
			 for (j=0; j<TotNodeNo; j++) {
				   Channel->linkmatrix[i][j] = 0;
		     }
	    } 
	}

//=======================================================
//       FUNCTION:   LinkStateComp    	
//======================================================= 
  void LinkStateComp() {
	  int sid, did;
	  double tmpPwr;

      for (sid=1; sid<=TotNodeNo; sid++) {
	        for (did=1; did<=TotNodeNo; did++) {
	               if (sid!=did) {
						tmpPwr = GetRxPwr(WGNnode(sid), WGNnode(did));			 
						if (IsOverRXThresh(DBToW(tmpPwr), WGNnode(did))==TRUE)
							Channel->linkmatrix[sid-1][did-1] = 3;
						else if (IsOverCSThresh(DBToW(tmpPwr), WGNnode(did))==TRUE)
                            Channel->linkmatrix[sid-1][did-1] = 2;
						else
							Channel->linkmatrix[sid-1][did-1] = 1;
	               }
			}
	  }
  }
