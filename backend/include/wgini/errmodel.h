//=======================================================
//       File Name :  errmodel.h
//=======================================================  
 #ifndef __ERRMODEL_H_
 #define __ERRMODEL_H_
 
 #include <stdio.h>
 #include <stdio.h>      
 #include <sys/socket.h> 
 #include <arpa/inet.h>  
 #include <stdlib.h>     
 #include <string.h>    
 #include <unistd.h>     
 #include <math.h>
 #include <pthread.h>

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
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"
   
  double GetNCDDBPSKBitErrProb(double snr);
  double GetCDDBPSKBitErrProb(double snr); 
  double GetDQPSKBitErrProb(double snr); 
  double GetBPSKBitErrProb(double snr); 
  double GetFSKBitErrProb(double snr);

  #endif
