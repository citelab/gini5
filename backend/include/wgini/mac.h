//=======================================================
//                                     File Name :  mac.h
//=======================================================
 #ifndef __MAC_H_
 #define __MAC_H_
 
 #include <stdio.h>
 #include <stdio.h>    
 #include <sys/socket.h> 
 #include <arpa/inet.h>  
 #include <stdlib.h>   
 #include <string.h>     
 #include <unistd.h>    
 #include <math.h>
 #include <pthread.h>
 #include <slack/err.h>
 #include <slack/prog.h>

 #include "gwcenter.h"
 #include "mobility.h"
 #include "mathlib.h"
 #include "antenna.h"
 #include "energy.h"
 #include "channel.h"
 #include "propagation.h"
 #include "nomac.h"
 #include "802_11.h"
 #include "csma.h"
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
  void IniNodeMac(NodeType type);
  void FinalizeNodeMac(NodeType type);
  void MacSendPkt( MobileNode *node, WGN_802_11_Mac_Frame *p, unsigned int timeout); 
  void SendDATA(MobileNode *node, WGN_802_11_Mac_Frame *dot_11_frame); 
  void SendACK(MobileNode *node, WGN_802_11_Mac_Frame *Data_frame); 
  void SetTxActiveSign(MobileNode *node,WGNflag flag);
  MacStatus GetTxStatus(MobileNode *node);
  MacStatus GetRxStatus(MobileNode *node);	
  WGNflag GetTxActiveSign(MobileNode *node);	
  WGNflag GetColErrorSign(WGN_802_11_Mac_Frame *frame);	
  WGNflag GetFadErrorSign(WGN_802_11_Mac_Frame *frame);	
  WGNflag GetNoiseErrorSign(WGN_802_11_Mac_Frame *frame);
  void SetColErrorSign(WGN_802_11_Mac_Frame *frame);	
  void SetFadErrorSign(WGN_802_11_Mac_Frame *frame);
  void SetNoiseErrorSign(WGN_802_11_Mac_Frame *frame);
  WGNflag PktRxIsEmpty(MobileNode *node);	
  WGNflag PktTxIsEmpty(MobileNode *node);	
  WGNflag PktRtsIsEmpty(MobileNode *node);	
  WGNflag PktRspIsEmpty(MobileNode *node);
  WGNflag PktRxHasFadError(MobileNode *node);	
  WGNflag PktRxHasColError(MobileNode *node);
  WGNflag PktRxHasNoiseError(MobileNode *node);
  int GetPhyFrameSize(WGN_802_11_Mac_Frame *pkt);  
  double GetCPThreshold(MobileNode *node); 
  WGNflag IsOverCPThreshold(MobileNode *node, WGN_802_11_Mac_Frame *frame_1, WGN_802_11_Mac_Frame *frame_2); 
  int GetID(unsigned char *mac_addr);
  WGNflag CheckIfIsBroadCastPkt(WGN_802_11_Mac_Frame *p); 
  WGNflag MacAddrIsSame(char *addr_1, char *addr_2);
  void MacDownPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void MacDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void MacUpPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void MacUpPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame);
  void ChMacMode(MAC_type type);


#endif
