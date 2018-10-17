//=======================================================
//                                     File Name :  802_11.h
//=======================================================
 #ifndef __802_11_H_
 #define __802_11_H_
 
 #include <stdio.h>
 #include <stdio.h>      
 #include <sys/socket.h> 
 #include <arpa/inet.h>  
 #include <stdlib.h>    
 #include <string.h>     
 #include <unistd.h>     
 #include <math.h>
 #include <pthread.h>
 #include <slack/prog.h>

 #include "gwcenter.h"
 #include "mobility.h"
 #include "mathlib.h"
 #include "antenna.h"
 #include "energy.h"
 #include "channel.h"
 #include "propagation.h"
 #include "nomac.h"
 #include "mac.h"
 #include "802_11_frame.h"
 #include "timer.h"
 #include "wirelessphy.h"
 #include "llc.h"
 #include "vpl.h"
 #include "event.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"

//=======================================================
//                                                  Functions
//======================================================= 
   void IniNodeS80211DcfMac(NodeType type); 
   void FinalizeNodeS80211DcfMac(NodeType type);
   double GetSlotTime(); 	
   double GetSIFS(); 
   double GetPIFS();
   double GetDIFS();
   double GetEIFS();	
   void Update_cw(MobileNode *node); 	
   void Reset_cw(MobileNode *node);
   void Set_Nav(MobileNode *node, unsigned int duration_ns); 
   WGNflag CheckIfChannelIdle(MobileNode *node);
   void CheckBFTimer(MobileNode *node); 
   void SetTxStatus(MobileNode *node,MacStatus status);	
   void SetRxStatus(MobileNode *node,MacStatus status); 	
   void SetNAVsign(MobileNode *node,WGNflag flag);	
   WGNflag GetNAVsign(MobileNode *node);  	
   WGNflag GetErrorSign(WGN_802_11_Mac_Frame *frame); 		
   WGNflag IsOverRTSThreshold(WGN_802_11_Mac_Frame *frame);
   void BFTimeoutHandler(MobileNode *node); 	
   void DFTimeoutHandler(MobileNode *node);
   void NAVTimeoutHandler(MobileNode *node);
   void IFTimeoutHandler(MobileNode *node);  	
   void RXTimeoutHandler(MobileNode *node);	
   void TXTimeoutHandler(MobileNode *node);
   void AskPktFromUpLayer (MobileNode *node); 	
   void tx_resume(MobileNode *node);
   void rx_resume(MobileNode *node); 
   int UpdateRspBuf(MobileNode *node); 
   int UpdateRtsBuf(MobileNode *node);
   int UpdateTxBuf(MobileNode *node);              
   void SendRTS(MobileNode *node); 
   void SendCTS(MobileNode *node,WGN_802_11_Mac_Frame *RTS_frame);
   void UpdateSRCounter(MobileNode *node);
   void UpdateLRCounter(MobileNode *node);
   void RstSRCounter(MobileNode *node);
   void RstLRCounter(MobileNode *node); 
   WGNflag SCounterIsOver(MobileNode *node); 
   WGNflag LCounterIsOver(MobileNode *node);
   void RetransmitRTS(MobileNode *node);
   void RetransmitData(MobileNode *node); 
   void send_timer (MobileNode *node); 
   void recv_timer(MobileNode *node); 
   void recvRTS(MobileNode *node); 
   void recvCTS(MobileNode *node);
   void recvACK(MobileNode *node);   
   void recvDATA(MobileNode *node);   
   void S80211DcfMacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame); 
   void S80211DcfMacUpPortRecv (MobileNode *node, WGN_802_11_Mac_Frame *frame); 		
   void S80211DcfMacDownPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame);
   void S80211DcfMacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame); 
   void Capture(MobileNode *node, WGN_802_11_Mac_Frame *frame);
   void Collision(MobileNode *node, WGN_802_11_Mac_Frame *frame);
   void PktErrHandler(MobileNode *node);
  
#endif
