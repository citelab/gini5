//=======================================================
//       File Name :  llc.h
//======================================================= 
 #ifndef __LLC_H_
 #define __LLC_H_

 #include <stdio.h>
 #include <sys/socket.h>
 #include <arpa/inet.h> 
 #include <stdlib.h>     
 #include <string.h>   
 #include <unistd.h>    
 #include <math.h>
 #include <pthread.h>
 #include <sys/time.h>
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
 #include "mac.h"
 #include "802_11_frame.h"
 #include "timer.h"
 #include "wirelessphy.h"
 #include "vpl.h"
 #include "event.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"
   
 void IniNodeLlc(NodeType type);
 void FinalizeNodeLlc(NodeType type);
 void LlcProcess();
 void LlcUpPortRecv(void* psConn);
 WGNflag LlcDownPortSend(MobileNode *node);
 void LlcUpPortSend();
 void LlcDownPortRecv(MobileNode *node, WGN_802_11_Mac_Frame *frame);
 WGN_802_3_Mac_Frame* WGN_802_3_FrameDup(unsigned char* input_frame, int byte_no);
 WGN_802_11_Mac_Frame* WGN_802_3_To_11_Frame_Converter(MobileNode *node, WGN_802_3_Mac_Frame *dot_3_frame);
 unsigned char* WGN_802_11_To_3_Frame_Converter(MobileNode *node, WGN_802_11_Mac_Frame *dot_11_frame, int body_len, int frame_len);	
 void conn_open(MobileNode *node,char* pchSocket);
 void conn_close(struct interface* psInt);
 void SocketNameGen(int id, char* sktname);	
 
 #endif
