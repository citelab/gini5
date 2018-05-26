//=======================================================
//                                     File Name :  nomac.h
//=======================================================
 #ifndef __NOMAC_H_
 #define __NOMAC_H_
 
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
  void IniNodeNoMac(NodeType type);
  void FinalizeNodeNoMac(NodeType type);
  int NoMacUpdateTxBuf(MobileNode *node);
  int NoMacUpdateRspBuf(MobileNode *node);
  void NoMacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void NoMacUpPortRecv (MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void NoMacDownPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame);
  void NoMacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame); 
  void NoMacCapture(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void NoMacCollision(MobileNode *node, WGN_802_11_Mac_Frame *frame);  
  void NoMacSetTxStatus(MobileNode *node,MacStatus status);	
  void NoMacSetRxStatus(MobileNode *node,MacStatus status); 	
  void NoMacRXTimeoutHandler(MobileNode *node);
  void NoMacTXTimeoutHandler(MobileNode *node); 	
  void NoMacIFTimeoutHandler(MobileNode *node);  
  void NoMac_send_timer (MobileNode *node); 
  void NoMac_recv_timer(MobileNode *node);
  void NoMac_tx_resume(MobileNode *node);
  void NoMac_rx_resume( MobileNode *node );
  void NoMacRecvACK(MobileNode *node);    
  void NoMacRecvDATA(MobileNode *node);
  void NoMacRetransmitData(MobileNode *node);
  void RstRetryCounter(MobileNode *node);
  void UpdateRetryCounter(MobileNode *node); 

#endif
