//=======================================================
//                              File Name :  fading.h
//======================================================= 
 #ifndef __FADING_H_
 #define __FADING_H_
 
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
 #include "timer.h"
 #include "wirelessphy.h"
 #include "llc.h"
 #include "vpl.h"
 #include "event.h"
 #include "nomac.h"
 #include "mac.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "cli.h"
 #include "wcard.h"
   
//=======================================================
//                                                  Functions
//=======================================================  
    void IniChannelFading(); 
	void FinalizeChannelFading();
	void IniCoefMatrix();	
	void IniIcrMatrix();
	double GetIIcrValue (int i, int j, int osc_no);
	void UpdateIcrMatrix(int id);
	void IniPhaseMatrix(); 
	void IniFadMatrix(); 
	void JakOscillator(double *pha,double *incr, double **coef,double *x);
    void FadingComp(double ***pha,double ***incr, double **coef,double **fad);
    double GetMaxDopSht(int i, int j); 
	double GetSpdDif(int i, int j);
    double RayleighFad(MobileNode *tx, MobileNode *rx);

#endif
