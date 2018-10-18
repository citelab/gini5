/*
 * NAME: wcard.c 
 * FUNCTION: Collection of functions to emulate the wireless network interface
 *                    card.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  wcard.c
//=======================================================
   #include "wcard.h"

//=======================================================
//       FUNCTION: IniNodeWirelessCard
//       PURPOSE:  Initialize the wireless card parameters of all nodes.. 
//======================================================= 
   void IniNodeWirelessCard(NodeType type) { 
	    int i;
		if (prog_verbosity_level()==2){
            printf("[IniNodeWirelessCard]:: Initializing wireless card module ... ");
		}		
        if (type == NORMAL) {
		     for ( i=0; i<TotNodeNo; i++) {	
		            WGNnode(i+1)->nodePhy->nodeWCard = (NodeWCard *)malloc(sizeof(NodeWCard));
		            if( WGNnode(i+1)->nodePhy->nodeWCard == NULL ){
						printf("IniNodeWCard(): nodeWCard malloc error");
						exit(1);
		            }
                    SetWCardPrama(WGNnode(i+1),WCardTypeArray[i]);
	         }
	    }
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
   }

//=======================================================
//       FUNCTION: FinalizeNodeWirelessCard
//======================================================= 
   void FinalizeNodeWirelessCard(NodeType type) { 
	    int i;
		if (prog_verbosity_level()==2){
            printf("[FinalizeNodeWirelessCard]:: Finalizing wireless card module ... ");
		}	
        if (type == NORMAL) {
		     for ( i=0; i<TotNodeNo; i++) {	
		            free(WGNnode(i+1)->nodePhy->nodeWCard); 
	         }
	    }
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
   }
//=======================================================
//       FUNCTION: SetWCardPrama
//       PURPOSE:  Set the wireless card parameters for the mobile node. 
//======================================================= 
  void SetWCardPrama( MobileNode *node, WCard_type Type) {
       if ( Type == SampleCard) {
		    node->nodePhy->nodeWCard->freq  = 2400;
            node->nodePhy->nodeWCard->bandwidth  = 2000000.0;
            node->nodePhy->nodeWCard->Pt  = 0.2818;                         
            node->nodePhy->nodeWCard->Pt_consume = 0.660;
            node->nodePhy->nodeWCard->Pr_consume = 0.395;
            node->nodePhy->nodeWCard->P_idle = 0.0;
            node->nodePhy->nodeWCard->P_sleep = 0.130;
            node->nodePhy->nodeWCard->P_off = 0.043;
            node->nodePhy->nodeWCard->RXThresh = 0.2818 * (1/100.0) * (1/100.0) * (1/100.0) * (1/100.0);
            node->nodePhy->nodeWCard->CSThresh = 0.2818 * (1/100.0) * (1/100.0) * (1/100.0) * (1/100.0) / 2.0;
            node->nodePhy->nodeWCard->CPThresh = 10;       // (dB) 	
			node->nodePhy->nodeWCard->ModType = DSSS;
			node->nodePhy->nodeWCard->capsign = ON;
		}
	  else if (Type == DemoTS) {
             printf ("[SetWCardPrama]:: DemoTS is not implemented at this moment.\n");
	         exit (1); 
          }
      else if (Type == DemoTU) {
             printf ("[SetWCardPrama]:: DemoTU is not implemented at this moment.\n");
	         exit (1); 
          }
	  else if (Type == DemoTT) {
             printf ("[SetWCardPrama]:: DemoTT is not implemented at this moment.\n");
	         exit (1); 
		  }
      else if (Type == SelfDefine) {
		     node->nodePhy->nodeWCard->ModType = modulation;
             printf ("[SetWCardPrama]:: SelfDefine is not implemented at this moment.\n");
	         exit (1); 
		  }
	  else {
			 printf ("[SetWCardPrama]:: Unrecongnized mobility type.\n");
		     exit (1);
		  }
  }

//=======================================================
//       FUNCTION:   ChWcardBandWidth   		
//=======================================================
  void ChWcardBandWidth(double bandwidth) {
	 int id;
	int verbose;
	verbose = prog_verbosity_level();
	prog_set_verbosity_level(0);
	 for(id=1; id<=TotNodeNo; id++) {	 
	      pthread_mutex_lock(&(WGNnode(id)->nodeLlc->ltom_array_mutex));
		  pthread_mutex_lock(&(WGNnode(id)->nodeLlc->ltou_array_mutex));	
	 }
     FinalizeEvent();
	 FinalizeNodeMac(NORMAL);

	 for (id=1; id<=TotNodeNo; id++) {
			WGNnode(id)->nodePhy->nodeWCard->bandwidth  = bandwidth;   //bps
	 }
	 Channel->channelbandwidth = bandwidth;
	 
	 IniEvent();
	 IniNodeMac(NORMAL); 
	 for(id=1; id<=TotNodeNo; id++) {	 
	      pthread_mutex_unlock(&(WGNnode(id)->nodeLlc->ltom_array_mutex));
		  pthread_mutex_unlock(&(WGNnode(id)->nodeLlc->ltou_array_mutex));	
	 }
	 prog_set_verbosity_level(verbose);
  }
