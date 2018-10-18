//=======================================================
//       File Name :  mobility.h
//======================================================= 
 #ifndef __MOBILITY_H_
 #define __MOBILITY_H_

 #include <stdio.h>
 #include <stdio.h>     
 #include <sys/socket.h> 
 #include <arpa/inet.h> 
 #include <stdlib.h>   
 #include <string.h>    
 #include <unistd.h>    
 #include <math.h>
 #include <slack/prog.h>

 #include "gwcenter.h"
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
 #include "cli.h"
 #include "vpl.h"
 #include "event.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"
   
  //used in printing the output file
 #define MOB_FNPREFIX  "mob_node_" 

  void PrintMobility(char *FILENAME, double x, double y, double z);
  double DistComp(NodePosition *Pos_1, NodePosition *Pos_2) ;
  void SetAPPos(MobileNode *node);
  void SetMovStrPtr(MobileNode *node); 
  void SetStartPointLoc(MobileNode *node); 
  void IniNodeCurLoc(MobileNode *node); 
  void SetNodeSpd(MobileNode *node); 
  WGNflag GetEndSign(MobileNode *node); 
  void SetEndSign(MobileNode *node, WGNflag flag);
  void IniNodeMobility(NodeType type);
  void FinalizeNodeMobility(NodeType type);
  void MobilityUpdate(MobileNode *node); 
  void MobilityProcess(); 
  void RWP_SetAPPos(MobileNode *AP); 
  void RWP_SetStartPointLoc(MobileNode *node); 
  void RWP_SetNodeRanDstLoc(MobileNode *node);
  WGNflag RWP_NodeSrcDstIsSame(MobileNode *node);
  void RWP_SetEndPointLoc(MobileNode *node);
  void RWP_IniNodeCurLoc(MobileNode *node);
  void RWP_SetNodeSpd(MobileNode *node);
  void RWP_UpdatePosition(MobileNode *node);
  WGNflag RWP_GetMovChSign(MobileNode *node); 
  void RWP_SetMovChSign(MobileNode *node, WGNflag flag); 
  WGNflag RWP_GetEndSign(MobileNode *node); 
  void RWP_SetEndSign(MobileNode *node, WGNflag flag); 
  void MovResume(MobileNode *node);
  void MovStop(MobileNode *node);

  #endif
