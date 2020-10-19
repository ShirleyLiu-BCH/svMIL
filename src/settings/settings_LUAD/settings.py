files = dict(

	#to run on the PCAWG data, we need both the directory of the SVs, and also the metadata to link file identifiers to cancer types
	svDir = '/hpc/cuppen/shared_resources/PCAWG/pcawg_consensus_1.6.161116.somatic_svs/',
	pcawgMetadata = '/hpc/cuppen/shared_resources/PCAWG/Metadata/overview_metadata.txt',
	snvDir = '/hpc/cuppen/shared_resources/PCAWG/final_consensus_12oct/PASS_vcfs/SNV',
	cnvDir = '/hpc/cuppen/shared_resources/PCAWG/somatic_CN/',
	metadataICGC = '../data/expression/rnaseq.extended.metadata.aliquot_id.V4.tsv',

	causalGenesFile = '../data/genes/CCGC.tsv', #file with all causal genes from cosmic.
	nonCausalGenesFile = '../data/genes/hg19_proteinCodingGenes.bed', #file with all protein-coding genes.
	promoterFile = '../data/promoters/epdnew_hg38ToHg19_9vC8m.bed', #File with promoters in human, not cell-specific
	cpgFile = '../data/cpg/cpgIslandExt.txt', #All human CpG sites
	tfFile = '../data/tf/tf_experimentallyValidated.bed_clustered.bed', #All validated human TFs
	rankedGeneScoreDir = "linkedSVGenePairs", #File that the output scores will be written to. The output will be in a folder with the provided UUID under this main results folder
	hg19CoordinatesFile = "../data/chromosomes/hg19Coordinates.txt",
	geneNameConversionFile = '../data/genes/allGenesAndIdsHg19.txt', #used with HMF SNVs and expression, converting ENSG identifiers to gene names.
	
	#specific for cancer type
	expressionFile = '../data/expression/luad/LUAD.rnaseqv2__illuminahiseq_rnaseqv2__unc_edu__Level_3__RSEM_genes_normalized__data.data.txt',
	tcgaCNVFile = '../data/cnvs/luad/luad_cn.txt',

	tadFile = "../data/tads/luad//Lung_Donor-LG1-raw_TADs.txt", #File with TADs specific for breast tissue
	eQTLFile = '../data/eQTLs/luad/lung_eQTLs.bed_clustered.bed', #File with eQTLs specific for breast tissue
	enhancerFile = '../data/enhancers/luad/encoderoadmap_elasticnet.94.csv', #File with enhancers specific for normal cell lines
	#h3k9me3 = '../data/histones/hmec/ENCFF065FJK_H3K9me3.bed',
	h3k4me3 = '../data/histones/luad/ENCFF935MFX_h3k4me3.bed_clustered.bed',
	h3k27ac = '../data/histones/luad/ENCFF305GIA_h3k27ac.bed_clustered.bed',
	h3k27me3 = '../data/histones/luad/ENCFF999WYS_h3k27me3.bed_clustered.bed',
	h3k4me1 = '../data/histones/luad/ENCFF653NIH_h3k4me1.bed_clustered.bed',
	#h3k36me3 = '../data/histones/hmec/ENCFF906MJM_H3K36me3.bed',
	dnaseIFile = '../data/dnase/luad/ENCFF794QIS.bed', ##### the clustered file is missing information!
	chromHmmFile = '../data/chromhmm/hmec/GSE57498_HMEC_ChromHMM.bed',
	rnaPolFile = '../data/rnapol/luad/ENCFF690LWY.bed', #same here, missing data
	superEnhancerFile = '../data/superEnhancers/luad/Lung.bed',
	ctcfFile = '../data/ctcf/luad/ENCFF694SEF.bed' #same here
	#hicFile = '../data/hic/HMEC_groupedTADInteractions.txt'

)

general = dict(

	source = 'PCAWG',
	expressionSource = 'TCGA',
	cancerType = 'LUAD', #is used to get the right cancer type from the PCAWG data, use the abbreviation of the study
	shuffleTads = False, #Should TAD positions be shuffled
	crd = False,
	gtexControl = False, #Should we use GTEx expression as a normal control, or use the non-disrupted TADs in other patients as control?
	geneENSG = False, #True if in the expression data (e.g. from HMF) the gene names are ENSG IDs. Otherwise, use False if these are regular gene names.
	bagThreshold = 700 #Subsample the bags randomly if there are more than this amount. To save computational load.
)
