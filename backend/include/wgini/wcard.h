//=======================================================
//       File Name :  wcard.h
//======================================================= 
 #ifndef __WCARD_H_
 #define __WCARD_H_

 #include <stdio.h>
 #include <sys/socket.h> 
 #include <arpa/inet.h>  
 #include <stdlib.h>     
 #include <string.h>   
 #include <unistd.h>    
 #include <math.h>
 #include <pthread.h>
 #include <sys/time.h>
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
 #include "llc.h"

 void IniNodeWirelessCard(NodeType type);
 void FinalizeNodeWirelessCard(NodeType type);
 void SetWCardPrama( MobileNode *node, WCard_type Type);
 void ChWcardBandWidth(double bandwidth);

 #endif
