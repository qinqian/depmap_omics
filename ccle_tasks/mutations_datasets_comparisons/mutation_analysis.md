- 17% of the mutations in WES could not be found in WGS. this is explained mainly by read depth issues (eve the somatic mutations pipeline could not have found them. Except for 7 of them that seemed to have been filtered out 2 would not have been called by HC (the rest could be retrieved like CGA does from known mutations), 3 seemed to have only be found on WGS by previous somatic mutation caller and are thus likely artificats/FP.)
- 60% for rnaseq. what about the opposite?

rnaseq filtering did not filter any mutations on MV411.


- CGA adding mutations that were not called adds 5% more mutations.

- only .6% of mutations are kept by the cnn filter. 4 million to 25,000

-  mutect1 and strelka that seem to call most germlines. still 10 times   

- the overlap of each is only 655 mutations (1% of strelka/mutect, 20% of mutect2)

- over the 789 mutations found by the CGA pipeline, its filters removed 640 mutations to get to 154 mutations.

- we only have 36% of mutations in CGA that are found back in HC+CNN. but this is when they don't pass through filters, otherwise it is 72%. it goes to 83% if we are using WGS HC+CNN). We need to know that some of these missing are due to mutations only found by Raindance, WGS or RNAseq that we are still reporting.

- 83% is also the number of mutations found in WES and not in WGS. (why??), can it be cell line mutations? (Sanger vs Broad) 
	- is 83% the maximum?
	- from Uri's paper on cell line changes. we should not think about allele frequency as it is as changing as rnaseq profile (population changes).
	- even true low allele frequency mut could appear and disappear between different groups/time/sequencing. 

- comparing HC with CGA. We have RNAseq and WGS and calls from Sanger to help us.
	- we have 20 mutations found by CGA but not HC (over the 220 that we have)
	- Looking deeply at these 20, 7 seemed wrong (looking at igv and knowing that no other tool called them). Some seemed bad but were actually retrieved in RNAseq (all were low a/f, half of them were hotspot)
	- But, HC found 16 more mutations that CGA did not report (but that were found by old Sanger PiPeling, WGS and RNAseq. All of them by more than 1 of them).

- WGS new vs old. old found 10 more mutations than us (that were found by other methods).
- Did we found some more mutations that the old pipeline did not?

- what about our RNAseq to previous?
- what about CGA new to CGA old?

- overall we see good AF mutations that can even be considered damaging called only by one modality or two, very often. the general overlap, even in damaging high AF mutations in not that great. 

- what it is exactly?