 #ifndef __WIRELESSPHY_H_
 #define __WIRELESSPHY_H_

 #include <stdio.h>
 #include <stdio.h>      
 #include <sys/socket.h> 
 #include <arpa/inet.h>  
 #include <stdlib.h>     
 #include <string.h>     
 #include <unistd.h>     
 #include <math.h>
 #include <slack/err.h>
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
 #include "llc.h"
 #include "vpl.h"
 #include "event.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"
   
//=======================================================
//       FUNCTIONS
//======================================================= 
   void IniNodePhy(NodeType type); 
   void FinalizeNodePhy(NodeType type);
   void PhyProcess() ;
   double GetTxPwr(MobileNode *node);
   void SetPktTxPwr(WGN_802_11_Mac_Frame *frame, double tx_pwr) ;
   double  GetRxPwr( MobileNode *tx, MobileNode *rx );
   void SetPktRxPwr(WGN_802_11_Mac_Frame *frame, double rx_pwr);
   double GetPktRxPwr(WGN_802_11_Mac_Frame *frame);
   void PhyUpPortSend(MobileNode *node,WGN_802_11_Mac_Frame *frame);
   void PhyUpPortRecv(MobileNode *node,WGN_802_11_Mac_Frame *frame);				 
   void PhyDownPortSend(MobileNode *node, WGN_802_11_Mac_Frame *frame); 
   void PhyDownPortRecv(MobileNode *node,WGN_802_11_Mac_Frame *frame);
   WGN_802_11_Mac_Frame *FrameDuplicate(WGN_802_11_Mac_Frame *frame) ;
   double GetCSThreshold(MobileNode *node);
   double GetRXThreshold(MobileNode *node);
   WGNflag IsOverRXThresh(double power, MobileNode *rx);
   WGNflag IsOverCSThresh(double power, MobileNode *rx);
   Switch GetCapSign(MobileNode *node);
   void SetCapSign(MobileNode *node, Switch sign);

#endif
