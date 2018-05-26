/*
 * NAME: mathlib.c 
 * FUNCTION: It provides some mathematical functions.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       Function Part
//======================================================= 
  #include "mathlib.h"

//=======================================================
//       FUNCTION:  Normal Distribution Number Generateor     
//       PURPOSE:   To randomly generate a normal distribution number 
//                              comply to x~N(mean,dev).
//======================================================= 
double NormalDist(double mean,double dev) {
                  
   double x1, x2, w, y1;
   static double y2;
   static int use_last = 0;

   if (use_last)             
   {
     y1 = y2;
     use_last = 0;
   }
   else
   {
     do {
      x1 = 2.0 * ((float)rand()/(float)RAND_MAX) - 1.0;
      x2 = 2.0 * ((float)rand()/(float)RAND_MAX) - 1.0;
      w = x1 * x1 + x2 * x2;
     } while ( w >= 1.0 );

     w = sqrt( (-2.0 * log( w ) ) / w );
     y1 = x1 * w;
     y2 = x2 * w;
     use_last = 1;
   }
   return(y1*dev+mean);
}

//=======================================================
//       FUNCTION: UnitUniform
//       PURPOSE:  Generate the random number with the uniform distributed 
//                             value between (0,1).
//======================================================= 
  double UnitUniform() {
	   double x;
       x=(double)rand() / (double)RAND_MAX;
	   if(x==0) 
		return(UnitUniform());
	   else
		return(x);
  }

//=======================================================
//       FUNCTION: Absolute
//       PURPOSE:  Compute the absolute value of the variable.
//======================================================= 
  double Absolute(double x) {
	if (x<0.0) return(-x);
	else return(x);
  }

//=======================================================
//       FUNCTION: MAX
//       PURPOSE:  Get the maxium variable.
//======================================================= 
  double Max(double a, double b) {
	  return ((a>b)?a:b);
  }

//=======================================================
//       FUNCTION: WToDB
//       PURPOSE:  Transfer the W value to DB.
//======================================================= 
  double WToDB(double x) {
       return(10.0*log10(x));
  }

//=======================================================
//       FUNCTION: DBToW
//       PURPOSE:  Transfer the DB value to W.
//======================================================= 
  double DBToW(double x) {
       return (pow(10,(x/10)));
  }
  
//=======================================================
//       FUNCTION: SecToUsec
//       PURPOSE:  Convert second to micro second
//======================================================= 
    unsigned int SecToUsec(double time) {
        int us = ceil (time * 1e6);
        return us;
    }

//=======================================================
//       FUNCTION: SecToNsec
//       PURPOSE:  Convert second to nano second
//======================================================= 
	unsigned int SecToNsec(double time) {
        int ns = ceil (time * NFACTOR);
        return ns;
    }

//=======================================================
//       FUNCTION: UsecToNsec
//       PURPOSE:  Convert second to nano second
//======================================================= 
	unsigned int UsecToNsec(double time) {
        int ns = ceil ((double)(time * NFACTOR) / 1000000);
        return ns;
    }
