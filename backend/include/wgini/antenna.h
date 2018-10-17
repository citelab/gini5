//=======================================================
//       File Name :  antenna.h
//======================================================= 
 #ifndef __ANTENNA_H_
 #define __ANTENNA_H_

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
 #include "mobility.h"
 #include "mathlib.h"
 #include "energy.h"
 #include "channel.h"
 #include "propagation.h"
 #include "802_11.h"
 #include "802_11_frame.h"
 #include "timer.h"
 #include "wirelessphy.h"
 #include "llc.h"
 #include "vpl.h"
 #include "event.h"
 #include "nomac.h"
 #include "mac.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"
   
//=======================================================
//       INITIALIZATION FUNCTIONS
//======================================================= 
void IniNodeAntenna(NodeType type);
void FinalizeNodeAntenna(NodeType type);

//=======================================================
//       SET GROUP FUNCTIONS
//======================================================= 
void SetAntType( MobileNode *tx ); 
void SetAntGain( MobileNode *tx );
void SetAntHeight( MobileNode *tx );
void SetAntSysLos( MobileNode *tx );

//=======================================================
//       GET GROUP FUNCTIONS
//======================================================= 
Antenna_type GetAntType( MobileNode *tx );
double GetAntGain( MobileNode *tx );
double GetAntHeight( MobileNode *tx );
double GetAntSysLos( MobileNode *tx );

#endif
