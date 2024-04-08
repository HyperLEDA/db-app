BEGIN ;

---------------------------------------------------------------------------------------
-- Weighted mean and standard error of the weighted mean
-- 
--    SE = wsem(X,W) returns Cochran (1977) approximation to bootstrap
--        estimation of the standard error of the weighted mean.
-- 
--    Unlike a simple random sample with equal weights, there is no widely
--    accepted definition of standard error of the weighted mean. It would be
--    straight-forward to do a bootstrap and obtain the empirical
--    distribution of the mean, and based on that estimate the standard
--    error. The best approximation to the bootstrap result comes from
--    Cochran (1977).
-- 
--    Reference:
--    D.F. Gatz and L. Smith
--    1995, Atmospheric Environment, 29, 1185
--    "The standard error of a weighted mean concentration - I. Bootstrapping
--    vs other methods"
--    http://www.sciencedirect.com/science/article/pii/135223109400210C
--
--    Based on the MATLAB version by D. Makarov 27/01/2013
--
--  function SE = wsem(X,W)
--  n=length(X);
--  wmeanX = wmean(X,W);
--  meanW = mean(W);
--  dW = W-meanW ;
--  dWX = W.*X - meanW.*wmeanX ;
--  SEV = n./((n-1).*sum(W).^2) .* ...
--      ( sum(dWX.^2) -2.*wmeanX.*sum(dW.*dWX) +wmeanX.^2.*sum(dW.^2) ) ;
--  SE = sqrt(SEV);

CREATE OR REPLACE FUNCTION 
  public.wmean_accum( CumSum double precision[], CurrData double precision, CurrWght double precision ) 
RETURNS double precision[]
AS $$
  SELECT 
    CASE WHEN CurrData IS NOT NULL and CurrWght IS NOT NULL 
         THEN ARRAY[ 
                CumSum[1] + (CurrData * CurrWght)    -- sum(W*X)
              , CumSum[2] + CurrWght                 -- sum(W)
              , CumSum[3] + 1                        -- n
              , CumSum[4] + (CurrData * CurrWght)^2  -- sum((W*X)^2)
              , CumSum[5] + (CurrData * CurrWght^2)  -- sum(W^2*X)
              , CumSum[6] + CurrWght^2               -- sum(W^2)
              ]
         ELSE CumSum 
    END ;
$$ LANGUAGE sql COST 100 STABLE CALLED ON NULL INPUT PARALLEL UNSAFE
;


CREATE OR REPLACE FUNCTION 
  public.wmean_final( WSum double precision[] )
RETURNS double precision[]
AS $$
  SELECT 
    CASE WHEN WSum[3]=0 THEN ARRAY[ NULL::double precision, NULL::double precision ]
         WHEN WSum[3]=1 THEN ARRAY[ WSum[1] / WSum[2], NULL::double precision ]
         ELSE ARRAY[ 
                WSum[1] / WSum[2]               -- Weighted average
              , sqrt( 
                  WSum[3]/( (WSum[3]-1) * WSum[2]^2 ) *
                  (  WSum[4] - WSum[1]^2/WSum[3]
                    -2*WSum[1]/WSum[2]*(WSum[5]-WSum[2]*WSum[1]/WSum[3])
                      +(WSum[1]/WSum[2])^2*(WSum[6]-WSum[2]^2/WSum[3])
                  )
                )                               -- Standard error of weighted mean
              ]
    END;
$$ LANGUAGE sql COST 100 STABLE STRICT PARALLEL UNSAFE
;

CREATE OR REPLACE AGGREGATE public.wmean(datum double precision, weight double precision) (
    SFUNC = wmean_accum,
    STYPE = double precision[] ,
    FINALFUNC = wmean_final,
    FINALFUNC_MODIFY = READ_ONLY,
    INITCOND = '{0,0,0,0,0,0}',
    MFINALFUNC_MODIFY = READ_ONLY
);

COMMENT ON AGGREGATE public.wmean (datum double precision, weight double precision) 
IS 'Weighted mean and Cochran (1977) approximation to bootstrap estimation of the standard error of the weighted mean. ARRAY[ Weighted_mean, Standard_error_of_weighted_mean ]. Reference: D.F. Gatz & L. Smith, 1995, Atmospheric Environment, 29, 1185, "The standard error of a weighted mean concentration - I. Bootstrapping vs other methods", http://www.sciencedirect.com/science/article/pii/135223109400210C' ;



------------------------------------------------------------
-- Distance between two points on sphere

CREATE OR REPLACE FUNCTION
  public.sphdist( ra1 double precision, dec1 double precision, ra2 double precision, dec2 double precision )
RETURNS double precision
AS $$
  SELECT acosd( LEAST( sind(dec1)*sind(dec2) + cosd(dec1)*cosd(dec2)*cosd(ra1-ra2) , 1 ) ) ;
$$ LANGUAGE sql COST 100 IMMUTABLE RETURNS NULL ON NULL INPUT PARALLEL SAFE
;

COMMENT ON FUNCTION public.sphdist (double precision, double precision, double precision, double precision) 
IS 'Angular separation in DEGREES between 2 points on sphere. The coordinates (RA1,Dec1) and (RA2,Dec2) are in DEGREES.' ;


--------------------------------------------------------------
---------- Check if string is JSON ---------------------------
--------------------------------------------------------------
-- in Postgresql 16 there is special function for that purpose
--
-- This solution is from
-- https://stackoverflow.com/questions/2583472/regex-to-validate-json
--
-- Unfortunatly, the improved solution by Gino Pane does not work in Postgres
--        (?(DEFINE)
--           (?<number>   -? (?= [1-9]|0(?!\d) ) \d+ (\.\d+)? ([eE] [+-]? \d+)? )
--           (?<boolean>   true | false | null )
--           (?<string>    " ([^"\n\r\t\\\\]* | \\\\ ["\\\\bfnrt\/] | \\\\ u [0-9a-f]{4} )* " )
--           (?<array>     \[  (?:  (?&json)  (?: , (?&json)  )*  )?  \s* \] )
--           (?<pair>      \s* (?&string) \s* : (?&json)  )
--           (?<object>    \{  (?:  (?&pair)  (?: , (?&pair)  )*  )?  \s* \} )
--           (?<json>   \s* (?: (?&number) | (?&boolean) | (?&string) | (?&array) | (?&object) ) \s* )
--        )
--        \A (?&json) \Z
--
-- I have implemented simplified solution by @cjbarth
-- [{\[]{1}([,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t]|".*?")+[}\]]{1}

CREATE OR REPLACE FUNCTION
  public.isjson( str text )
RETURNS boolean
AS $$
  SELECT str ~* '[{\[]{1}([,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t]|".*?")+[}\]]{1}' ;
$$  LANGUAGE sql COST 100 IMMUTABLE RETURNS NULL ON NULL INPUT PARALLEL SAFE
;

COMMIT ;