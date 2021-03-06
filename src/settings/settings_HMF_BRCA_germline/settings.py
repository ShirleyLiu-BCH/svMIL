files = dict(

	svFile = '../data/svs/gnomad_v2.1_sv.sites_filtered_01072020.bed', #germline SV test
	causalGenesFile = '../data/genes/CCGC.tsv', #file with all causal genes from cosmic.
	nonCausalGenesFile = '../data/genes/hg19_proteinCodingGenes.bed', #file with all protein-coding genes.
	promoterFile = '../data/promoters/epdnew_hg38ToHg19_9vC8m.bed', #File with promoters in human, not cell-specific
	cpgFile = '../data/cpg/cpgIslandExt.txt', #All human CpG sites
	tfFile = '../data/tf/tf_experimentallyValidated.bed', #All validated human TFs
	hicFile = '../data/hic/HMEC_groupedTADInteractions.txt',
	rankedGeneScoreDir = "linkedSVGenePairs", #File that the output scores will be written to. The output will be in a folder with the provided UUID under this main results folder
	hg19CoordinatesFile = "../data/chromosomes/hg19Coordinates.txt",
	snvDir = '../../../somatics',
	cnvDir = '../../../somatics',
	geneNameConversionFile = '../data/genes/allGenesAndIdsHg19.txt', #used with HMF SNVs, converting ENSG identifiers to gene names.

	#specific for HMEC
	tadFile = "../data/tads/hmec/HMEC_Lieberman-raw_TADs.bed", #File with TADs specific for breast tissue
	eQTLFile = '../data/eQTLs/breast/breast_eQTLs.bed', #File with eQTLs specific for breast tissue
	enhancerFile = '../data/enhancers/hmec/hmec_encoderoadmap_elasticnet.117.txt', #File with enhancers specific for normal cell lines
	h3k9me3 = '../data/histones/hmec/ENCFF065FJK_H3K9me3.bed',
	h3k4me3 = '../data/histones/hmec/ENCFF065TIH_H3K4me3.bed',
	h3k27ac = '../data/histones/hmec/ENCFF154XFN_H3K27ac.bed',
	h3k27me3 = '../data/histones/hmec/ENCFF291WFP_H3K27me3.bed',
	h3k4me1 = '../data/histones/hmec/ENCFF336DDM_H3K4me1.bed',
	h3k36me3 = '../data/histones/hmec/ENCFF906MJM_H3K36me3.bed',
	dnaseIFile = '../data/dnase/hmec/ENCFF336OGZ.bed',
	chromHmmFile = '../data/chromhmm/hmec/GSE57498_HMEC_ChromHMM.bed',
	rnaPolFile = '../data/rnapol/hmec/ENCFF433ZKP.bed',
	superEnhancerFile = '../data/superEnhancers/hmec/se_20200212_HMEC.bed',
	ctcfFile = '../data/ctcf/hmec/ENCFF288RFS.bed'

)

general = dict(

	source = 'TCGA',
	cancerType = 'BRCA',
	shuffleTads = False, #Should TAD positions be shuffled
	crd = False
)

