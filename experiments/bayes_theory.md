#### Bayes' theorem
$A$ is an event.
$B$ is an event whose association with $A$ we want to confirm or deny.
$$
P(A|B) = \frac{P(B|A) P(A)}{P(B)}
$$
$P(A|B)$ - given that $B$ happened, what is the probability that it happened because of $A$? - *posterior probability*
$P(B|A)$ - given that $A$ happened, what is the probability that $B$ will happen?
$P(A)$ - what is the probability of event $A$?
$P(B)$ - what is the probability of event $B$?
#### Cross-identification by coordinates
$p(\vec{x}|\vec{m})$ - the probability density that an object with a three-dimensional normal coordinate vector $\vec{m}$ is observed at coordinates $\vec{x}$.

It is normalized:
$$
\int p(\vec{x}|\vec{m}) d^3 x = 1
$$
Assuming that the object is observed at $\vec{x}_1$, and applying Bayes' theorem, we obtain the probability density that the current position of the object is $\vec{m}$:

$$
p(\vec{m}|\vec{x}_1) = \frac{p(\vec{x}_1|\vec{m})p(\vec{m})}{p(\vec{x}_1)}
$$
while the probability density of finding $\vec{m}$ on the celestial sphere
$$
p(\vec{m}) = \frac{1}{4\pi}\delta(|\vec{m}| - 1)
$$
Using the normalization of the probability density
$$
\int \frac{p(\vec{x}_1|\vec{m})p(\vec{m})}{p(\vec{x}_1)} = 1 \Rightarrow p(\vec{x}_1) = \int p(\vec{x}_1|\vec{m})p(\vec{m}) d^3 m
$$
This allows us to find the probability of finding an object with the current position $\vec{m}$ inside the solid angle $\Omega$:
$$
P(\Omega|\vec{m}) = \int_{\Omega} p(\vec{x}|\vec{m}) d^3 x
$$
where the probability density of the current position $\vec{m}$ is:
$$
p(\vec{m}|\Omega) = \frac{p(\vec{m}) P(\Omega|\vec{m})}{\int p(\vec{m}) P(\Omega|\vec{m}) d^3 m}
$$
Suppose we have a list of observations (from different instruments, with different accuracies) $D = \{\vec{x}_1, \dots, \vec{x}_n\}$. Testing the hypothesis
- $H$ - all these observations are actually one source
- versus $K$ - the observations come from different sources

We introduce the Bayes factor to numerically evaluate these hypotheses:
$$
B(H,K|D) = \frac{p(D|H)}{p(D|K)}
$$
For $p(D|H)$ we need the probability that for any source $\vec{m}$ all measurements came from this source - this is the astrometric precision $p_i$ of each observation:
$$
p(D|H) = \int p(\vec{m}) \prod^{n}_{i=1} p_i(\vec{x}_i|\vec{m}) d^3 m
$$
For the alternative hypothesis $K$ we need to estimate the probability that for any set of sources $\{\vec{m}_i\}$ the observation $\vec{x}_i$ came from the source $\vec{m}_i$:
$$
p(D|K) = \prod^n_{i=1} \int p(\vec{m}_i) p_i(\vec{x}_i|\vec{m}_i) d^3 m_i
$$
When the Bayes factor is large, hypothesis $H$ is most likely true. If it is of the order of 1, then the information does not support any of the hypotheses. If it is less than 1, then hypothesis $K$ is preferable.

For astrometric accuracy, the spherical normal distribution is used:
$$
N(\vec{x}|\vec{m}, w) = \frac{w\delta(|\vec{x}| - 1)}{4\pi \sinh w} \exp(w\vec{m}\vec{x})
$$
where $w = 1/\sigma^2$ is the observation weight. The Bayes factor in this case can be numerically calculated as
$$
B(H, K|D) = \frac{\sinh w}{w} \prod^n_{i=1} \frac{w_i}{\sinh w_i}
$$
where
$$
w = \left|\sum_{i=1}^n w_i \vec{x}_i\right|
$$
for two observations $w = \sqrt{w_1^2 + w_2^2 + 2 w_1 w_2 cos\psi}$, due to which
$$
B = \frac{2}{\sigma_1^2 + \sigma_2^2} \exp \left(-\frac{\psi^2}{2(\sigma_1^2 + \sigma_2^2)}\right)
$$
#### From Bayesian factor to applied meanings
The next task is to choose a threshold for the Bayesian factor, after which the selected pair of objects will be considered one object or different. To do this, we will obtain a relationship between the factor and the probability that the selected pair of objects is one object. After that, it will be possible to set a threshold for this probability.

$$
\frac{P(H|D)}{P(K|D)} = \frac{P(H)p(D|H)}{P(K)p(D|K)} = \frac{P(H)}{P(K)}B(H,K|D)
$$
$$
\frac{P(H|D)}{1 - P(H|D)} = \frac{P(H)}{1 - P(H)}B(H,K|D) \Rightarrow P(H|D) = \left(1 + \frac{1 - P(H)}{BP(H)}\right)^{-1}
$$
Thus, knowing the prior probability (*what is the probability that a randomly chosen pair of objects is the same object?*), we can relate the Bayesian factor and the posterior probability that two specific objects are the same object.

In general, the problem of calculating the a priori probability comes down to determining the probability that two arbitrary objects (one from each catalog) are the same object. In this case, the general formula for this is:
$$
P(H) = \frac{N_{\star}}{N_1 N_2}
$$
Here $N_{1,2}$ is the number of objects in each catalog, $N_{\star}$ is the number of objects in the "intersection" catalog. $N_{\star}$ depends on the distribution of objects in the catalogs.

For example, for the simplest case when one catalog is a subset of another, $N_{\star} = N_1$. If, for example, one catalog is a catalog of galaxies with $z < 0.1$, and the other is with $z > 2$, then $N_\star = 0$.
#### Final algorithm
##### For coordinates
1. Calculate the thresholds for the Bayes factor. For the simplest case, when a catalog with $N \ll N_{\text{hyperleda}}$ objects is loaded, and we know that b**o**most of these objects already exist in HyperLEDA, we can estimate the threshold from the formula above, considering the prior probability as $P(H) = 1 / N_{\text{hyperleda}}$:
$$
B = \frac{P(H|D)(1 - P(H))}{P(H)(1 - P(H|D))}
$$
Thus, if the number of objects in the DB is about $N_{\text{hyperleda}} = 10^7$, and the threshold for the probability that an object already exists is $P(H|D) = 0.1$, then $B \sim 1.1 \cdot 10^6$.
The result of cross-identification should be one of three: two objects originate from the same object, two objects originate from different objects, insufficient information. In order to produce such a result, two Bayes factors must be entered - the lower $B_1$ (transition from "objects are definitely different" to "insufficient information") and the upper $B_2$ (transition from "insufficient information" to "objects are definitely the same"). To do this, two acceptable posterior probabilities must be selected, one up to which we are confident that the objects do not match, and the other after which we are confident that the objects do match.
2. For each object in the loaded catalog:
3. Select some threshold radius within which we will perform the search. This radius can be quite large, its purpose is to cut off objects for which we know for sure that their Bayes factor will be small. This radius can be either constant or vary depending on the coordinate error.
4. Request all objects within this radius from level 2. 3. For each object from this radius, calculate the Bayes factor using the formula:
$$
B = \frac{2}{\sigma_1^2 + \sigma_2^2} \exp \left(-\frac{\psi^2}{2(\sigma_1^2 + \sigma_2^2)}\right)
$$
5. We have a set of Bayes factors $\mathcal{B} = {B_1, \dots, B_{n}}$ for all objects from the selected radius. Then the cross-identification result is as follows:
6. If $\forall B \in \mathcal{B}: B < B_1$, then the object is marked as new.
7. If $\exists !B \in \mathcal{B}: B > B_2$, then the object is marked as existing with the given PGC number.
8. In all other cases, the object is sent for manual verification.
##### For names
For names, the algorithm remains the same, it is supposed to be used as an addition to cross-identification by coordinates - first, using the algorithm above, we cross-identify all objects by coordinates, then, for objects that would have been sent for manual verification, we cross-identify by names using a search for a complete match of the normalized name.
##### (in the future) For redshifts
For redshifts, you need to derive the Bayes factor formula in a similar way. Then you can use the recursiveness of this approach and calculate the general factor as
$$
B = B_{astrometry} B_{redshift}
$$