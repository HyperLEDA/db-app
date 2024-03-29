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

CREATE OR REPLACE FUNCTION public.wmean_accum( CumSum double precision[], CurrData double precision, CurrWght double precision ) 
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
$$ LANGUAGE 'sql' COST 100 STABLE STRICT PARALLEL UNSAFE
;


CREATE OR REPLACE FUNCTION public.wmean_final( WSum double precision[] )
RETURNS double precision[]
AS $$
  SELECT ARRAY[ 
           WSum[1] / WSum[2]               -- Weighted average
         , sqrt( 
             WSum[3]/( (WSum[3]-1) * WSum[2]^2 ) *
             (  WSum[4] - WSum[1]^2/WSum[3]
               -2*WSum[1]/WSum[2]*(WSum[5]-WSum[2]*WSum[1]/WSum[3])
                 +(WSum[1]/WSum[2])^2*(WSum[6]-WSum[2]^2/WSum[3])
             )
           )                               -- Standard error of weighted mean
         ] ;
$$ LANGUAGE 'sql' COST 100 STABLE STRICT PARALLEL UNSAFE
;

CREATE OR REPLACE AGGREGATE public.wmean(datum double precision, weight double precision) (
    SFUNC = wmean_accum,
    STYPE = double precision[] ,
    FINALFUNC = wmean_final,
    FINALFUNC_MODIFY = READ_ONLY,
    INITCOND = '{0,0,0,0,0,0}',
    MFINALFUNC_MODIFY = READ_ONLY
);

COMMENT ON AGGREGATE public.wmean (datum double precision, weight double precision) IS 'Returns ARRAY[ Weighted_mean, Standard_error_of_weighted_mean ]' ;

COMMIT ;