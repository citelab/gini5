//=======================================================
//                                     File Name :  awgn.h
//=======================================================
 #ifndef __AWGN_H_
 #define __AWGN_H_
 
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
 #include "802_11.h"
 #include "nomac.h"
 #include "mac.h"
 #include "802_11_frame.h"
 #include "timer.h"
 #include "wirelessphy.h"
 #include "llc.h"
 #include "event.h"
 #include "cli.h"
 #include "errmodel.h"
 #include "fading.h"
 #include "wcard.h"
  
  void IniChannelAwgn();	
  void FinalizeChannelAwgn();
  double GetAWGNErrProb (double bandwidth, int machdrlen, int pktlen, double Es);
  WGNflag AWGNPktErr (double pe);
  void AWGNPktHandler (WGN_802_11_Mac_Frame *frame);

 #endif
