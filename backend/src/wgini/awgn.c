/*
 * NAME: wawgnch.c 
 * FUNCTION: Collection of functions implements the awgn module. It provides
 *                    functions to emulate the awgn noise affect to the wireless channel. 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  wawgnch.c
//======================================================= 
  #include "awgn.h"

// for wirless 802.11 AWGN channel, 
// Having in mind that the physical layer overhead is always 
// transmitted on 1 Mbps using DBPSK and the MPDU part 
// (MAC Protocol Data Unit) is transmitted on the chosen 
// transmission rate among 1, 2, 5.5 and 11 Mbps. So the 
// error probability is:
//    =======================
//    p = 1- (1-Pe_phy)(1-Pe_mac)
//    =======================
// Pe_phy is the physical layer overhead error probability
// whereas mac e Pe_mac is the MPDU error probability.
// PPDU = PLCP Preamble(18 bytes) + PLCP Header(6 bytes) + MPDU;
// MPDU = Mac Header (30 bytes) +  MSDU (IP packet Payload) + FCS (4 bytes);
// So we can obtain:
//    ===========================
//    Pe_phy = 1- (1-Pb_QBPSK)^(24*8)
//    ===========================
//    =================================
//    Pe_mac = 1- (1-Pb_*)^((34+MSDU_len)*8)
//    =================================
//    Pb_* is the bit error probabity for specific modulation method, such as:
//    DQPSK, CCK5.5 or CCK11

//=======================================================
//       FUNCTION:   GetAWGNErrProb
//======================================================= 
  double GetAWGNErrProb (double bandwidth, int machdrlen, int pktlen, double Es) {
    	double pe_phy;
		double pe_mac;
		double pb;
		double pe;
		double mac_snr;
		double phy_snr;
		double k;   

        //comput pe_phy
        k = bandwidth / 1000000.0;

        if (GetAwgnMode() == SNR) {
            mac_snr = DBToW(Channel->channelAwgn->snr);
			phy_snr = mac_snr * k;
        }
		else if (GetAwgnMode() == PWR) {
		    mac_snr = DBToW(Es) / ((DBToW(Channel->channelAwgn->noise*2))*bandwidth);            //unit of noise is db. 
		    phy_snr = DBToW(Es) / ((DBToW(Channel->channelAwgn->noise*2))*1000000.0);
		}
		else {
            printf ("[GetAWGNErrProb]:: Error, unrecognized awgn mode!\n");
		    exit(1);
		}

		pb = GetNCDDBPSKBitErrProb(phy_snr);
		pe_phy = 1- pow((1-pb), 24*8);

		//compute pe_mac
		if (bandwidth == 1000000.0) {	
			pb = GetNCDDBPSKBitErrProb(mac_snr);
		}
		else if (bandwidth == 2000000.0) {
			pb = GetDQPSKBitErrProb(mac_snr);
		}
		else{
			printf ("\n[GetAWGNErrProb]:: Awgn module can not handle this bit rate now, sorry!\n");
		    printf ("[GetAWGNErrProb]:: Awgn switch is closed automatically!\n"); 
			SetAwgnSign(OFF);
			return 0;
		}   
		pe_mac = 1- pow((1-pb), (machdrlen+pktlen)*8);

        //compute the total pe
		pe = 1- (1-pe_phy)*(1-pe_mac);
		return (pe);
   }

//=======================================================
//       FUNCTION:   GetAWGNErrProb
//======================================================= 
  WGNflag AWGNPktErr (double pe) {
       if (UnitUniform() < pe) 	{
		   //PrintSystemInfo ("Drop packet for can not be demulated correctly!");
		   return(TRUE);
	   }
       else 
		   return(FALSE);
  }

//=======================================================
//       FUNCTION:   AWGNPktHandler
//======================================================= 
  void AWGNPktHandler (WGN_802_11_Mac_Frame *frame) {
	double Es;
	double pktlen;
	double machdrlen;
	double prob; 
	
    verbose(5, "[PathLoss]:: Packet from node %d to node %d is handled by the 'AWGN Module'", 
		           frame->pseudo_header->srcid, frame->pseudo_header->dstid);		

	if (GetAwgnSign() == ON) {
		//bandwidth = node->nodePhy->nodeWCard->bandwidth;            // in our case the bandwidth is the same for tx and rx node.
        switch(GetFcSubtype (frame)) {
            case MAC_SUBTYPE_CTS:
                pktlen = 0;
			    machdrlen = MAC_CTS_LEN;
			    break;
            case MAC_SUBTYPE_ACK:
			    pktlen = 0;
			    machdrlen = MAC_ACK_LEN;
                break;
		    case MAC_SUBTYPE_RTS:
	            pktlen = 0;
			    machdrlen = MAC_RTS_LEN;
			    break;
			case MAC_SUBTYPE_DATA:
	            pktlen = frame->pseudo_header->mac_size - MAC_DATA_HDR_LEN;
			    machdrlen = MAC_DATA_HDR_LEN;
				break;
            default:
				printf ("[PhyDownPortRecv]:: Error, Invalid frame subtype!");
			    exit(1);
        }		
		Es = frame->pseudo_header->rx_pwr;
		prob = GetAWGNErrProb (frame->pseudo_header->signal*100000.0, machdrlen, pktlen, Es);   
		if (AWGNPktErr(prob) == TRUE) {
			//if can not be recoveryed, mark error.
			SetNoiseErrorSign(frame);
		} 
    }  
  }

void IniChannelAwgn() { 
		if (prog_verbosity_level()==2){
            printf("[IniChannelAwgn]:: Initializing awgn module ... ");
		}	
		Channel->channelAwgn = (ChannelAwgn *)malloc(sizeof(ChannelAwgn));
		Channel->channelAwgn->switcher = AwgnSign;
		Channel->channelAwgn->noise = noise;
        Channel->channelAwgn->snr = snr_Eb_N0;
		Channel->channelAwgn->mode = awgn_mode;
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
}

void FinalizeChannelAwgn() {
		if (prog_verbosity_level()==2){
            printf("[FinalizeChannelAwgn]:: Finalizing awgn module ... ");
		}
		free(Channel->channelAwgn);
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
}
