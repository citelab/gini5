/*
 * NAME: propagation.c 
 * FUNCTION: Collection of functions implements the propagation module. 
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 * NOTE:   Some functions are written by taking ns-2 as reference. 
 */

//=======================================================
//       File Name :  propagation.c
//======================================================= 
  #include "propagation.h"

//=======================================================
//       FUNCTION:  FreeSpaceMod
//       PURPOSE:   Compute the receiving power by using Free Space 
//                              propagation model.
//                              Friis free space equation:
//                              ------------------------------------------------------------
//                              *          Pt * Gt * Gr * (lambda^2)    *
//                              *   P = -------------------------------------------    * 
//                              *                (4 * pi * d)^2 * L            *
//                              ------------------------------------------------------------
//======================================================= 
  double Friis(double Pt, double Gt, double Gr, double lambda, 
	                   double d, double L)  {
        double M;
		M = lambda/ (4 * PI * d);
        return (Pt * Gt * Gr * (M * M)) / L;
    }

//=======================================================
//       FUNCTION:  FreeSpaceMod
//       PURPOSE:   Compute the receiving power by using Free Space 
//                              propagation model.
//                              Friis free space equation:
//                              ------------------------------------------------------------
//                              *          Pt * Gt * Gr * (lambda^2)    *
//                              *   P = -------------------------------------------    * 
//                              *                (4 * pi * d)^2 * L            *
//                              ------------------------------------------------------------
//======================================================= 
double FreeSpaceMod( MobileNode *tx, MobileNode *rx )
{  
   double d;
   double Pt,Pr,Gt,Gr;
   double L;
   double lambda;

	 Pt = tx->nodePhy->nodeWCard->Pt;
	 Gt = tx->nodePhy->nodeAntenna->Gain_dBi;
     Gr = rx->nodePhy->nodeAntenna->Gain_dBi;
	 L = rx->nodePhy->nodeAntenna->SysLoss;
	 lambda = WAVESPD/(tx->nodePhy->nodeWCard->freq*MIG);
	 
	 d = DistComp(tx->nodePhy->nodeMobility->curPosition, rx->nodePhy->nodeMobility->curPosition);
       
     Pr = Friis(Pt, Gt, Gr, lambda, d, L); 
     return (WToDB(Pr));
}


//=======================================================
//       FUNCTION:  TwoRayMod
//       PURPOSE:   Compute the receiving power by using Two-Ray 
//                              ground propagation model.
//                              ---------------------------------------------------------------
//                              *           Pt * Gt * Gr * (ht^2 * hr^2)    *
//                              *   Pr = ----------------------------------------------   * 
//                              *                        d^4 * L                       *
//                              ---------------------------------------------------------------
//                              normally we assumes L = 1.
//======================================================= 
double TwoRayMod( MobileNode *tx, MobileNode *rx )  {
     
		 double hr,ht;
		 double d;
		 double Pt,Pr,Gt,Gr;
		 double L;
		 double M;

         ht = tx->nodePhy->nodeAntenna->Height;
		 hr = rx->nodePhy->nodeAntenna->Height;
		 Pt = tx->nodePhy->nodeWCard->Pt;
		 Gt = tx->nodePhy->nodeAntenna->Gain_dBi;
         Gr = rx->nodePhy->nodeAntenna->Gain_dBi;
		 L = rx->nodePhy->nodeAntenna->SysLoss;

		 d = DistComp(tx->nodePhy->nodeMobility->curPosition, rx->nodePhy->nodeMobility->curPosition);

		 M = (hr*ht) / (d*d);
		 Pr = (M*M)*(Pt*Gt*Gr) / L;

         return   (WToDB(Pr));
    }


//=======================================================
//       FUNCTION:  TwoRayGroundMod
//       PURPOSE:   Compute the receiving power by using Two-Ray 
//                              ground propagation model with the condition of 
//                              d>crossover_dist while by using Free Space pro-
//                              pagation model with the oppsite condition.
//                              The equation used to compute the crossover_dist:
//                              -----------------------------------------------------------------
//                              *                                4 * PI * ht * hr     *
//                              *  crossover_dist = ------------------------------  * 
//                              *                                       lambda          *
//                              -----------------------------------------------------------------
//======================================================= 
double TwoRayGroundMod( MobileNode *tx, MobileNode *rx )  {
        
        double crossover_dist;
        double Pr;
        double hr,ht;
		double lambda;
		double d;

        ht = tx->nodePhy->nodeAntenna->Height;
		hr = rx->nodePhy->nodeAntenna->Height;
		lambda = WAVESPD/(tx->nodePhy->nodeWCard->freq*MIG);
        crossover_dist = (4 * PI * ht * hr) / lambda;
        d = DistComp(tx->nodePhy->nodeMobility->curPosition, rx->nodePhy->nodeMobility->curPosition);
        
		if ( d <= crossover_dist ) {
            Pr = FreeSpaceMod( tx, rx );
        }
        else {
            Pr = TwoRayMod( tx, rx );
        }    
		return (Pr)	;
    }

//=======================================================
//       FUNCTION:  ShadowingMod
//       PURPOSE:   Compute the receiving power by using Shadowing 
//                              propagation model.
//                              -----------------------------------------------------------------------------
//                              *   Pr                                              d                   *
//                              * ------- (db) = 10* Belta* log10(-------) + X_db   *
//                              *  Pr0                                            d0                  *
//                              ------------------------------------------------------------------------------
//                              where X_db ~ N( 0.0 , thelta). d0 is the reference 
//                              distance. Belta is the pathloss exponent. 
//======================================================= 
double ShadowingMod( MobileNode *tx, MobileNode *rx )
{
	double dist;
	double Gt;                  //  tx antenna gain
    double Gr;                  //  rx antenna gain
    double Pr0;                //  receiving power at reference distance
    double idealPwr_db;     //  ideal power loss
	double powerLoss_db;    // the power difference between the receiving power at dist0 and that at receiver
	double Pr;                          //receiving power
	double Pt;
    double L;
    double lambda;

	dist = DistComp(tx->nodePhy->nodeMobility->curPosition, rx->nodePhy->nodeMobility->curPosition);
    
	Pt = tx->nodePhy->nodeWCard->Pt;
	L = rx->nodePhy->nodeAntenna->SysLoss;
	lambda = WAVESPD/(tx->nodePhy->nodeWCard->freq*MIG);

	// get antenna gain
	Gt = tx->nodePhy->nodeAntenna->Gain_dBi;
	Gr = rx->nodePhy->nodeAntenna->Gain_dBi;

	// calculate receiving power at reference distance
	Pr0 = WToDB(Friis(Pt, Gt, Gr, lambda, Channel->channelProp->dist0, L));
	

	// calculate ideal power loss predicted by path loss model
	idealPwr_db = -1*(Channel->channelProp->pathlossexp) * WToDB(dist/Channel->channelProp->dist0);
   
	// get power loss by adding a log-normal random variable (shadowing)
	// the power loss is relative to that at reference distance dist0
	powerLoss_db =  idealPwr_db + NormalDist(0.0, Channel->channelProp->dev_db);

	// calculate the receiving power at dist
	Pr = Pr0 + powerLoss_db;

	return (Pr);
}

//=======================================================
//       FUNCTION:  PathLoss	(db)
//       PURPOSE:   Compute the receiving power with corresponding 
//                           propagation model
//======================================================= 
double PathLoss(MobileNode *tx, MobileNode *rx) {
	 
	 double Pr;
     double dist;
	 
	 verbose(5, "[PathLoss]:: Packet from node %d to node %d is handled by the 'Propagation Module'", tx->Id, rx->Id);		
	 dist = DistComp( tx->nodePhy->nodeMobility->curPosition, rx->nodePhy->nodeMobility->curPosition );

	 if (GetPropType() == FreeSpace) {
	   Pr = FreeSpaceMod(tx, rx);
	   return (Pr);
     }
	 else if (GetPropType() == TwoRayGround) {
	   Pr = TwoRayGroundMod(tx, rx);
	   return (Pr);
	 }
	 else if (GetPropType() == Shadowing ) {
		Pr = ShadowingMod(tx, rx);
		return (Pr);
	 }
	 else {
	    printf ("[Pathloss]:: Unrecognized PropagationModel type.\n");
		exit (1);
	 }
}

void IniChannelPropagation() { 
		if (prog_verbosity_level()==2){
            printf("[IniChannelPropagation]:: Initializing propagation module ... ");
		}	
		Channel->channelProp = (ChannelProp *)malloc(sizeof(ChannelProp));
		Channel->channelProp->prop_type = prop_type;        
		Channel->channelProp->pathlossexp = pathlossexp;
		Channel->channelProp->dev_db = dev_db;
		Channel->channelProp->dist0 = dist0;
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
}

void FinalizeChannelPropagation() {
		if (prog_verbosity_level()==2){
            printf("[FinalizeChannelPropagation]:: Finalizing propagation module ... ");
		}
		free(Channel->channelProp);
		if (prog_verbosity_level()==2){
			printf("[ OK ]\n");
		}
}
