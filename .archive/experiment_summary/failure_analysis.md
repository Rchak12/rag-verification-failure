# Failure Analysis

## Summary

| Category | Count | % of Claims |
|---|---|---|
| ✅ Correct & Supported | 36 | 30.0% |
| ⚠️  Correct & Unsupported (false negative) | 18 | 15.0% |
| 🔶 Incorrect & Supported (verifier missed it) | 44 | 36.7% |
| ❌ Incorrect & Unsupported | 22 | 18.3% |

## Failure Mode Descriptions

1. **⚠️ False Negative (Correct but Unsupported)** — The verifier deleted a claim whose underlying answer was correct. Caused by paraphrase mismatch: the claim expresses the same idea as a passage sentence but with different wording, so cosine similarity falls below τ. *Fix: lower τ or use NLI entailment.*

2. **🔶 False Positive (Incorrect but Supported)** — The verifier kept a claim even though the final answer label was wrong. Happens when the retrieved passage is topically similar but does not actually support the specific claim. *Fix: sentence-level NLI rather than embedding similarity.*

3. **❌ Correctly Rejected** — Claim was both wrong and unsupported. This is the ideal case: verification catches hallucinated claims.

4. **Retrieval misses** — If the key evidence passage is not in top-k, verification fails even for true claims. Not directly visible in claim categories but visible as low support scores across all claims for an example.

## Example Instances

### ✅ Correct & Supported

**Q:** Do mitochondria play a role in remodelling lace plant leaves during programmed cell death?  
**Gold:** `yes` | **Pred:** `yes`  
**Claim:** Programmed cell death (PCD) is the regulated death of cells within an organism.  
**Support score:** 1.0 | **Best evidence:** Programmed cell death (PCD) is the regulated death of cells within an organism.  

**Q:** Do mitochondria play a role in remodelling lace plant leaves during programmed cell death?  
**Gold:** `yes` | **Pred:** `yes`  
**Claim:** The lace plant (Aponogeton madagascariensis) produces perforations in its leaves through PCD.  
**Support score:** 1.0 | **Best evidence:** The lace plant (Aponogeton madagascariensis) produces perforations in its leaves through PCD.  

**Q:** Syncope during bathing in infants, a pediatric form of water-induced urticaria?  
**Gold:** `yes` | **Pred:** `yes`  
**Claim:** Apparent life-threatening events in infants are a difficult and frequent problem in pediatric practice.  
**Support score:** 1.0 | **Best evidence:** Apparent life-threatening events in infants are a difficult and frequent problem in pediatric practice.  

### ⚠️  Correct & Unsupported (false negative)

**Q:** Do mitochondria play a role in remodelling lace plant leaves during programmed cell death?  
**Gold:** `yes` | **Pred:** `yes`  
**Claim:** Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this do  
**Support score:** 0.313 | **Best evidence:** The two groups were found to be similar with regard to age, gender, the incidence of individual risk factors for ominous  

**Q:** Syncope during bathing in infants, a pediatric form of water-induced urticaria?  
**Gold:** `yes` | **Pred:** `yes`  
**Claim:** Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this do  
**Support score:** 0.222 | **Best evidence:** Satisfaction levels reported by patients and care givers were good.  

**Q:** Can tailored interventions increase mammography use among HMO women?  
**Gold:** `yes` | **Pred:** `yes`  
**Claim:** Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this do  
**Support score:** 0.51 | **Best evidence:** Retrospective cohort study.  

### 🔶 Incorrect & Supported (verifier missed it)

**Q:** Landolt C and snellen e acuity: differences in strabismus amblyopia?  
**Gold:** `no` | **Pred:** `maybe`  
**Claim:** Assessment of visual acuity depends on the optotypes used for measurement.  
**Support score:** 1.0 | **Best evidence:** Assessment of visual acuity depends on the optotypes used for measurement.  

**Q:** Landolt C and snellen e acuity: differences in strabismus amblyopia?  
**Gold:** `no` | **Pred:** `maybe`  
**Claim:** The ability to recognize different optotypes differs even if their critical details appear under the same visual angle.  
**Support score:** 1.0 | **Best evidence:** The ability to recognize different optotypes differs even if their critical details appear under the same visual angle.  

**Q:** Are the long-term results of the transanal pull-through equal to those of the transabdominal pull-th  
**Gold:** `no` | **Pred:** `yes`  
**Claim:** The transanal endorectal pull-through (TERPT) is becoming the most popular procedure in the treatment of Hirschsprung di  
**Support score:** 1.0 | **Best evidence:** The transanal endorectal pull-through (TERPT) is becoming the most popular procedure in the treatment of Hirschsprung di  

### ❌ Incorrect & Unsupported

**Q:** Landolt C and snellen e acuity: differences in strabismus amblyopia?  
**Gold:** `no` | **Pred:** `maybe`  
**Claim:** Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this do  
**Support score:** 0.263 | **Best evidence:** 12 such cases were detected.  

**Q:** Are the long-term results of the transanal pull-through equal to those of the transabdominal pull-th  
**Gold:** `no` | **Pred:** `yes`  
**Claim:** Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this do  
**Support score:** 0.418 | **Best evidence:** A significant difference in age at interview between the 2 groups was noted; we therefore reanalyzed the data controllin  

**Q:** Double balloon enteroscopy: is it efficacious and safe in a community setting?  
**Gold:** `yes` | **Pred:** `maybe`  
**Claim:** Further longitudinal studies with larger sample sizes are needed to establish definitive causal relationships in this do  
**Support score:** 0.51 | **Best evidence:** Retrospective cohort study.  

