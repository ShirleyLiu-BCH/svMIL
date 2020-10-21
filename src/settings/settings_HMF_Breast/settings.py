files = dict(

	#to run on the PCAWG data, we need both the directory of the SVs, and also the metadata to link file identifiers to cancer types
	svDir = '/hpc/cuppen/shared_resources/HMF_data/DR-104/data/somatics/',
	snvDir = '/hpc/cuppen/shared_resources/HMF_data/DR-104/data/somatics/',
	cnvDir = '/hpc/cuppen/shared_resources/HMF_data/DR-104/data/somatics/',
	metadataHMF = '/hpc/cuppen/shared_resources/HMF_data/DR-104/metadata/metadata.tsv',
	expressionDir = '/hpc/cuppen/shared_resources/HMF_data/DR-104/data/isofix/',
	normalizedExpressionFile = '../data/expression/HMF_TMM.txt',

	causalGenesFile = '../data/genes/CCGC.tsv', #file with all causal genes from cosmic.
	nonCausalGenesFile = '../data/genes/hg19_proteinCodingGenes.bed', #file with all protein-coding genes.
	promoterFile = '../data/promoters/epdnew_hg38ToHg19_9vC8m.bed', #File with promoters in human, not cell-specific
	cpgFile = '../data/cpg/cpgIslandExt.txt', #All human CpG sites
	tfFile = '../data/tf/tf_experimentallyValidated.bed_clustered.bed', #All validated human TFs
	rankedGeneScoreDir = "linkedSVGenePairs", #File that the output scores will be written to. The output will be in a folder with the provided UUID under this main results folder
	hg19CoordinatesFile = "../data/chromosomes/hg19Coordinates.txt",
	geneNameConversionFile = '../data/genes/allGenesAndIdsHg19.txt', #used with HMF SNVs and expression, converting ENSG identifiers to gene names.

	#specific for HMEC
	tadFile = "../data/tads/hmec/HMEC_Lieberman-raw_TADs.bed", #File with TADs specific for breast tissue
	eQTLFile = '../data/eQTLs/clusters_test.txt', #File with eQTLs specific for breast tissue
	enhancerFile = '../data/enhancers/hmec/hmec_encoderoadmap_elasticnet.117.txt', #File with enhancers specific for normal cell lines
	h3k9me3 = '../data/histones/hmec/ENCFF065FJK_H3K9me3.bed',
	h3k4me3 = '../data/histones/hmec/ENCFF065TIH_H3K4me3.bed_clustered.bed',
	h3k27ac = '../data/histones/hmec/ENCFF154XFN_H3K27ac.bed_clustered.bed',
	h3k27me3 = '../data/histones/hmec/ENCFF291WFP_H3K27me3.bed_clustered.bed',
	h3k4me1 = '../data/histones/hmec/ENCFF336DDM_H3K4me1.bed_clustered.bed',
	h3k36me3 = '../data/histones/hmec/ENCFF906MJM_H3K36me3.bed',
	dnaseIFile = '../data/dnase/hmec/ENCFF336OGZ.bed', ##### the clustered file is missing information!
	chromHmmFile = '../data/chromhmm/hmec/GSE57498_HMEC_ChromHMM.bed',
	rnaPolFile = '../data/rnapol/hmec/ENCFF433ZKP.bed', #same here, missing data
	superEnhancerFile = '../data/superEnhancers/hmec/se_20200212_HMEC.bed',
	ctcfFile = '../data/ctcf/hmec/ENCFF288RFS.bed', #same here
	hicFile = '../data/hic/HMEC_groupedTADInteractions.txt'

)

general = dict(

	source = 'HMF',
	cancerType = 'Breast', #is used to get the right cancer type from the data, use the cancer type name used in the metadata.
	shuffleTads = False, #Should TAD positions be shuffled
	crd = False,
	gtexControl = False, #Should we use GTEx expression as a normal control, or use the non-disrupted TADs in other patients as control?
	geneENSG = False, #True if in the expression data the gene names are ENSG IDs. Otherwise, use False if these are regular gene names.
	bagThreshold = 700 #Subsample the bags randomly if there are more than this amount. To save computational load.
)