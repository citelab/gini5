/*
 * NAME: fading.c 
 * FUNCTION: Collection of functions implements the fading module. It provides
 *                    functions to emulate the Rayleigh fading of the wireless channel. 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 * NOTE:   Some functions are written by taking SAM simulator as reference. 
 */

//=======================================================
//       File Name :  fading.c
//======================================================= 
  #include "fading.h"

//=======================================================
//       FUNCTION:   IniChannelFading
//       PURPOSE:    Establish the initial fading matrix for the channel
//======================================================= 
    void IniChannelFading() {
		if (prog_verbosity_level()==2){
            printf("[IniChannelFading]:: Initializing fading module ... ");
		}			
		Channel->channelFad = (ChannelFad *)malloc(sizeof(ChannelFad));
		Channel->channelFad->switcher = RayleighSign;
	    Channel->channelFad->N0 = oscnum;     //the total number of oscillators in the Jakes model
	    Channel->channelFad->N = 4*oscnum+2;       //the total number of the simulated multiple paths 
		IniCoefMatrix();
		IniIcrMatrix();
		IniPhaseMatrix();
		IniFadMatrix();
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
	}


//=======================================================
//       FUNCTION:   FinalizeChannelFading()
//       PURPOSE:    Establish the initial fading matrix for the channel
//======================================================= 
    void FinalizeChannelFading() {
	    int i,j;
		int N0;
		N0=Channel->channelFad->N0;
		if (prog_verbosity_level()==2){
            printf("[FinalizeChannelFading]:: Finalizing fading module ... ");
		}
		for(i=0;i<=N0;i++){ 
			free(Channel->channelFad->coef[i]);
		}
		for(i=0;i<TotNodeNo;i++) {
			 for(j=0;j<TotNodeNo;j++) {
				  free(Channel->channelFad->incr[i][j]);
				  free(Channel->channelFad->pha[i][j]);
			 }
		}
		for(i=0;i<TotNodeNo;i++) {
			 free(Channel->channelFad->incr[i]);
			 free(Channel->channelFad->pha[i]);
			 free(Channel->channelFad->fad[i]);
		}
		free(Channel->channelFad->coef);
	    free(Channel->channelFad->incr);
        free(Channel->channelFad->pha);
		free(Channel->channelFad->fad);
		free(Channel->channelFad);
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
	}


//=======================================================
//       FUNCTION:   IniCoefMatrix
//       PURPOSE:    Allocate the memory space to store the Rayleigh fading 
//                               envelop amplitude
//======================================================= 
	void IniCoefMatrix() {
		int i;
		int N0;
		N0=Channel->channelFad->N0;
	    Channel->channelFad->coef=(double **)malloc((N0+1)*sizeof(double *));
		if(Channel->channelFad->coef==NULL){
			puts("[IniCoefMatrix]:: Malloc error");
			exit(1);
		}
		for(i=0;i<=N0;i++){ 
			Channel->channelFad->coef[i]=(double *)malloc(2*sizeof(double));
			if(Channel->channelFad->coef[i]==NULL) {
				puts("[IniCoefMatrix]:: Malloc error");
				exit(1);
		    }
			Channel->channelFad->coef[i][0] = 2*cos(PI*i/(N0))/sqrt(2*N0);
    		Channel->channelFad->coef[i][1] = 2*sin(PI*i/(N0))/sqrt(2*N0+2);
	    }
        Channel->channelFad->coef[0][0]=Channel->channelFad->coef[0][0]/sqrt(2.0);
        Channel->channelFad->coef[0][1]=Channel->channelFad->coef[0][1]/sqrt(2.0);
	}

//=======================================================
//       FUNCTION:   IniIcrMatrix
//       PURPOSE:    Allocate the memory space to store the phrase increment
//======================================================= 	
	void IniIcrMatrix() {	
		int i,j,k;  
		int N0;
		N0=Channel->channelFad->N0;
		Channel->channelFad->incr = (double ***)malloc(TotNodeNo*sizeof(double));
		if(Channel->channelFad->incr == NULL){
			puts("[IniIcrMatrix]:: Malloc error");
			exit(1);  
		}
		for(i=0;i<TotNodeNo;i++) {
			 Channel->channelFad->incr[i]=(double **)malloc(TotNodeNo*sizeof(double));
			 if(Channel->channelFad->incr[i]==NULL){
				puts("[IniIcrMatrix]:: Malloc error");
				exit(1);  
		     }
			 for(j=0;j<TotNodeNo;j++) {
				  Channel->channelFad->incr[i][j]=(double *)malloc((N0+1)*sizeof(double));
	              if(Channel->channelFad->incr[i][j]==NULL){
		          puts("[IniIcrMatrix]:: Malloc error");
		          exit(1);
				  }		
				  for (k=0; k<=N0; k++){
						if (i==j) {
							//no channel between the same node
						    Channel->channelFad->incr[i][j][k] = 0;      
						}
						else 
                            Channel->channelFad->incr[i][j][k]=GetIIcrValue(i+1,j+1,k);     
				  }					  
			 }
		}
	}

//=======================================================
//       FUNCTION:   GetIIcrValue
//       PURPOSE:    Calculate the phase increment 
//======================================================= 
    double GetIIcrValue (int i, int j, int osc_no) {
		int N;
		N=Channel->channelFad->N;
	   	return (2*PI*cos(2*PI*osc_no/N)*GetMaxDopSht(i,j)*(SYS_INFO->time_info->Ch_timeunit));
	}

//=======================================================
//       FUNCTION:   UpdateIcrMatrix
//       PURPOSE:    Update the phase increment per second for the spec- 
//                               -ified path between two nodes 
//======================================================= 	
	void UpdateIcrMatrix(int id) {	
		int i,k;  // "i" is the receiving node id
		int N0;
		N0=Channel->channelFad->N0;
		for(i=0;i<TotNodeNo;i++) {
			if ((i+1)!=id) {
				for(k=0;k<=N0;k++) {
					Channel->channelFad->incr[i][id-1][k]=GetIIcrValue(i+1,id,k);
					Channel->channelFad->incr[id-1][i][k]=GetIIcrValue(id,i+1,k);
				}
			}
		}
	}

//=======================================================
//       FUNCTION:   IniPhaseMatrix
//       PURPOSE:    Initialize the path phase between every two nodes
//======================================================= 
	void IniPhaseMatrix() {
		int i,j,k;
		int N0;
		N0=Channel->channelFad->N0;
		Channel->channelFad->pha=(double ***)malloc(TotNodeNo*sizeof(double));
		if(Channel->channelFad->pha==NULL){
			puts("[IniPhaseMatrix]:: Malloc error");
			exit(1);
		}
		for(i=0;i<TotNodeNo;i++) {
			 Channel->channelFad->pha[i]=(double **)malloc(TotNodeNo*sizeof(double));
	         if(Channel->channelFad->pha[i]==NULL){
			 puts("[IniPhaseMatrix]:: Malloc error");
	   	     exit(1);
		     }
		     for( j=0; j<TotNodeNo; j++){
				  Channel->channelFad->pha[i][j]=(double *)malloc((N0+1)*sizeof(double));
	              if(Channel->channelFad->pha[i][j]==NULL){
		          puts("[IniPhaseMatrix]:: Malloc error");
		          exit(1);
				  }
				  for (k=0; k<=N0; k++){
						if (i==j) {
							//no channel between the same node
						    Channel->channelFad->pha[i][j][k] = 0;      
						}
						//set the starting random value for the phases
						else 
                            Channel->channelFad->pha[i][j][k]=2*PI*((double)rand() / RAND_MAX);     
				  }	
		     } 
	    } 
	}

//=======================================================
//       FUNCTION:   IniFadMatrix
//       PURPOSE:    Initialize the Rayleigh fading matrix 
//======================================================= 
	void IniFadMatrix() {
		int i,j;
		Channel->channelFad->fad=(double **)malloc(TotNodeNo*sizeof(double *));
		if(Channel->channelFad->fad==NULL) {
		puts("[IniFadMatrix]:: Malloc error");
		exit(1);
		}
		for(i=0; i<TotNodeNo; i++){
			 Channel->channelFad->fad[i]=(double *)malloc(TotNodeNo*sizeof(double));
			 if(Channel->channelFad->fad[i]==NULL) {
				puts("[IniFadMatrix]:: Malloc error");
				exit(1);
			 }
			 for (j=0; j<TotNodeNo; j++) {
				   Channel->channelFad->fad[i][j] = 0;
		     }
	    } 
		FadingComp(Channel->channelFad->pha,Channel->channelFad->incr, Channel->channelFad->coef,Channel->channelFad->fad);
	}

//=======================================================
//       FUNCTION:   JakOscillator
//       PURPOSE:    Computes fading quadrature components for each ray 
//                               of each user, and updates phases of the correspon-
//                               ding oscillators.
//======================================================= 
	void JakOscillator(double *pha,double *incr, double **coef,double *x){    
		int i;
		double temp1,temp2,temp_cos;
		int N0;
		N0=Channel->channelFad->N0;  
		temp1=0;
		temp2=0;
		for(i=0;i<=N0;i++){ 
			pha[i]=pha[i]+incr[i];
			if (pha[i]>2*PI)
			    pha[i]-=2*PI;
	        temp_cos=cos(pha[i]);
            temp1+=coef[i][0]*temp_cos;
            temp2+=coef[i][1]*temp_cos;
        }
        x[0]=temp1;
        x[1]=temp2;
    }

//=======================================================
//       FUNCTION:   FadingComp
//       PURPOSE:    Calculate the fading factor
//======================================================= 
   void FadingComp(double ***pha,double ***incr, double **coef,double **fad){  
       int i,j;
      double fad_coef[2];

	  for(i=0;i<TotNodeNo;i++) {
            for(j=0;j<TotNodeNo;j++){
				if (i!=j) {
				    JakOscillator(pha[i][j],incr[i][j],coef,fad_coef);
                    fad[i][j]=WToDB(pow(fad_coef[0],2.0)+pow(fad_coef[1],2.0));
				}
            }
			if (Channel->channelFadPrintSign == TRUE) {
				PrintChannelFading(fad[i],i+1);
			}			
       }
   }

//=======================================================
//       FUNCTION:   GetMaxDopSht
//       PURPOSE:    Compute the Maximium Doppler Shift
//======================================================= 
    double GetMaxDopSht(int i, int j) {
		 double f_max;
	     double spd;
         // Get the comparative speed of the T-R pair
		 spd = GetSpdDif(i,j); 
		 f_max = (WGNnode(j)->nodePhy->nodeWCard->freq*MIG)*spd / WAVESPD; 
		 f_max = Absolute(f_max);
		 return (f_max);
    }	

//=======================================================
//       FUNCTION:   GetSpdDif
//======================================================= 
    double GetSpdDif(int i, int j) {
	     double spd_dif;
		 double x;
		 double y;
		 double z;
		 x = WGNnode(i)->nodePhy->nodeMobility->nodeSpd->spd_x - WGNnode(j)->nodePhy->nodeMobility->nodeSpd->spd_x;
		 y = WGNnode(i)->nodePhy->nodeMobility->nodeSpd->spd_y - WGNnode(j)->nodePhy->nodeMobility->nodeSpd->spd_y;
		 z = WGNnode(i)->nodePhy->nodeMobility->nodeSpd->spd_z - WGNnode(j)->nodePhy->nodeMobility->nodeSpd->spd_z;
		 spd_dif = sqrt( x*x + y*y + z*z);
		 return (spd_dif);
    }	

//=======================================================
//       FUNCTION:   RayleighFad
//       PURPOSE:    Compute the Maximium Doppler Shift
//======================================================= 
    double RayleighFad(MobileNode *tx, MobileNode *rx) {
 	    verbose(5, "[RayleighFad]:: Packet from node %d to node %d is handled by the 'Fading Module'", tx->Id, rx->Id);		
		if(Channel->channelFad->fad==NULL) {
		   return(0.0);
		}
	    else {
		    return(Channel->channelFad->fad[(tx->Id)-1][(rx->Id)-1]);
		}
	}
