//=======================================================
//                                     File Name :  csma.h
//=======================================================
 #ifndef __CSMA_H_
 #define __CSMA_H_
 
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
 #include "802_11.h"
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
  void IniNodeCSMAMac(NodeType type);
  void FinalizeNodeCSMAMac(NodeType type) ;
  WGNflag AllowToTx(MobileNode *node);
  void CSMAMacSet_Nav(MobileNode *node, unsigned int duration_ns);
  double GetMaxPropDelay();
  int CSMAMacUpdateTxBuf(MobileNode *node);
  int CSMAMacUpdateRspBuf(MobileNode *node);
  void CSMAMacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void CSMAMacUpPortRecv (MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void CSMAMacDownPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame);
  void CSMAMacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame); 
  void CSMAMacCapture(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void CSMAMacCollision(MobileNode *node, WGN_802_11_Mac_Frame *frame);  
  void CSMAMacSetTxStatus(MobileNode *node,MacStatus status);	
  void CSMAMacSetRxStatus(MobileNode *node,MacStatus status); 	
  void CSMAMacRXTimeoutHandler(MobileNode *node);
  void CSMAMacTXTimeoutHandler(MobileNode *node); 	
   void CSMAMacNAVTimeoutHandler(MobileNode *node);
  void CSMAMacIFTimeoutHandler(MobileNode *node);  
  void CSMAMac_send_timer (MobileNode *node); 
  void CSMAMac_recv_timer(MobileNode *node);
  void CSMAMac_tx_resume(MobileNode *node);
  void CSMAMac_rx_resume( MobileNode *node );
  void CSMAMacRecvACK(MobileNode *node);    
  void CSMAMacRecvDATA(MobileNode *node);
  void CSMAMacRetransmitData(MobileNode *node);
  void CSMARstRetryCounter(MobileNode *node);
  void CSMAUpdateRetryCounter(MobileNode *node);

#endif
