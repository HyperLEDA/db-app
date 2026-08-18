BEGIN;

ALTER TABLE photometry.ellipse DROP CONSTRAINT IF EXISTS ellipse_check2 ;

ALTER TABLE photometry.ellipse ADD CONSTRAINT ellipse_check2 
CHECK (
     (method IN ('asymptotic', 'model', 'petrosian', 'kron') AND level IS NOT NULL AND isophote IS NULL) 
  OR (method IN ('visual', 'isophotal') AND isophote IS NOT NULL AND level IS NULL)
  OR (method = 'moments' AND level IS NULL AND isophote IS NULL)
);

COMMIT ;