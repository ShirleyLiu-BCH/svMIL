import numpy as np
import json

from tad import TAD
from sv import SV
from gene import Gene
from eQTL import EQTL
from interaction import Interaction
from snv import SNV

import settings

class NeighborhoodDefiner:
	"""
		Class responsible for defining the neighborhood of causal genes.
		
		Currently, the neighborhood consists of:
		
		- nearest TADs on the left and right of the gene
		- all eQTLs mapped to the gene (and if these are enhancers or not)
		- Hi-C interactions. These are mapped to the TAD that these are present in. We use this to determine which interactions are potentially gained. 
		- SVs (and SNVs) overlapping either the gene directly, or other elements in the neighborhood
	
	"""

	
	def __init__(self, genes, svData, snvData, mode):
		
		#1. Map genes to TADs
		
		if settings.general['tads'] == True or settings.general['gainOfInteractions'] == True: #Gain of interactions is dependent on TADs
			
			#Make these pats a setting!
			tadFile = "../../data/tads/tads.csv" #These files will need to go to the settings!
			print "Getting TADs"
			tadData = self.getTADsFromFile(tadFile)
			print "mapping TADs to genes"
			self.mapTADsToGenes(genes[:,3], tadData) #only pass the gene objects will suffice
			
			
		#2. Map genes to eQTLs
		
		eQTLData = [] #Keep empty by default
		if settings.general['eQTLs'] == True:
			eQTLFile = "../../data/eQTLs/eQTLsFilteredForCausalGenes.txt" #These files will need to go to the settings!
			print "getting eQTLs"
			eQTLData = self.getEQTLsFromFile(eQTLFile, genes[:,3])
		
		
		#Add reading/parsing of 3D genome information
		if settings.general['interactionChains'] == True: 
			interactionsFile = "../../data/HiC/intrachromosomal_geneNonGeneInteractions.csv" #should be setting!!!!
			print "Getting interactions"
			interactionData = self.getInteractionsFromFile(interactionsFile)
			print "mapping interactions to genes"
			self.mapInteractionsToGenes(genes[:,3], interactionData)
			
		#Read/parse Hi-C interactions (intrachromosomal) to later compute gains of interactions
		if settings.general['gainOfInteractions'] == True:
			interactionsFile = settings.files['hiCInteractionsFile']
			print "Reading all Hi-C interactions"
			#First get all Hi-C interactions
			interactions, regions = self.getHiCInteractionsFromFile(interactionsFile)
			#Map the Hi-C interactions to the respective TADs
			tadData = self.mapInteractionsToTads(interactions, regions, tadData)


		
		#3. Map SVs to all neighborhood elements
		if mode == "SV":
			print "Mapping SVs to the neighborhood"
			self.mapSVsToNeighborhood(genes, svData, tadData)
		if mode == "SNV":
			print "Mapping SNVs to the neighborhood"
			self.mapSNVsToNeighborhood(genes, snvData, eQTLData)
		if mode == "SV+SNV": #in this case map both
			print "Mapping SVs to the neighborhood"
			self.mapSVsToNeighborhood(genes, svData)
			
			print "Mapping SNVs to the neighborhood"
			self.mapSNVsToNeighborhood(genes, snvData, eQTLData)
		
		
	def getTADsFromFile(self, tadFile):
		"""
			Read the TADs into NumPy format. I don't read the TADs into objects immediately, because the NumPy matrices work very well for
			quick overlapping. I add an object reference to the matrix so that we can later add the right TAD object to the genes. 
		"""
		
		#Read the gene list data into a list
		tadData = []
		with open(tadFile, "r") as f:
			lineCount = 0
			for line in f:
				if lineCount < 2: #skip header
					lineCount += 1
					continue
				line = line.strip()
				splitLine = line.split("\t")
				
				
				#Convert the numbers to integers for quicker comparison. 0 is chromosome, 1 is start, 2 is end. Celltypes are not used for now. 
				splitLine[1] = int(splitLine[1])
				splitLine[2] = int(splitLine[2])
				
				TADObject = TAD(splitLine[0], splitLine[1], splitLine[2])
				
				#chr, start, end
				tadData.append([splitLine[0], splitLine[1], splitLine[2], TADObject])
		
		#Also convert the other dataset to numpy
		tadData = np.array(tadData, dtype='object')
		
		return tadData
		
		
	def getEQTLsFromFile(self, eQTLFile, genes):
		
		eQTLs = []
		with open(eQTLFile, 'rb') as f:
			
			lineCount = 0
			for line in f:
				if lineCount < 1:
					lineCount += 1
					continue
				
				line = line.strip()
				splitLine = line.split("\t")
				
				eQTLObject = EQTL(splitLine[0], int(splitLine[1]), int(splitLine[2])) #chr, start, end
				
				#The mapping information is in the file, so we can already do it here
				self.mapEQTLsToGenes(eQTLObject, genes, splitLine[3])
						
				eQTLs.append(eQTLObject)				
		
		return eQTLs
	
	def getInteractionsFromFile(self, interactionsFile):
		"""
			!!! DEPRECATED, Hi-C BASED HEAT DIFFUSION IS NOT WORKING
		
			Read the HiC interactions between genes and interaction pairs into numPy array format. Each numpy array will be in the format of:
			0: chromosome of non-coding interaction
			1: start of non-coding interaction
			2: end of non-coding interaction
			3: name of gene that is interacted with. If there are multiple genes, this is split across multiple lines
			4: bin in which the gene resides in the format of chr_binStartPosition
			
			Notes:
			There is an issue with the csv export in Neo4J and now there are double quotation marks which I cannot fix. Thus the string is not real json. 
		"""
		
		#Read the gene list data into a list
		interactionData = []
		with open(interactionsFile, "r") as f:
			lineCount = 0
			for line in f:
				if lineCount < 1: #skip header
					lineCount += 1
					continue
				line = line.strip()
				splitLine = line.split('}","{') #split on every column which is encoded strangely now
				
				encodedNonCodingRegion = splitLine[0].split('"')[7] #this is where the region ID will always be
				nonCodingRegionChr = encodedNonCodingRegion.split("_")[0]
				nonCodingRegionStart = int(encodedNonCodingRegion.split("_")[1])
				nonCodingRegionEnd = nonCodingRegionStart + 5000 #bin of 5kb, should be a setting
				
				encodedGeneData = splitLine[1].split('"')
				encodedGeneRegion = encodedGeneData[14]
				encodedGeneRegionChr = encodedGeneRegion.split("_")[0]
				encodedGeneRegionStart = int(encodedGeneRegion.split("_")[1])
				encodedGeneRegionEnd = encodedGeneRegionStart + 5000
				encodedGeneNames = encodedGeneData[6]
				
				splitGeneNames = encodedGeneNames.split(";")
				for geneName in splitGeneNames: #Add the region separately for each gene in the coding region. 
					
					interactionObj = Interaction(nonCodingRegionChr, nonCodingRegionStart, nonCodingRegionEnd, encodedGeneRegionChr, encodedGeneRegionStart, encodedGeneRegionEnd, geneName)
					#For now I will not make objects because working with the numpy arrays is much much faster
					interactionData.append([nonCodingRegionChr, nonCodingRegionStart, nonCodingRegionEnd, geneName, encodedGeneRegion, interactionObj])
					
	
		#Also convert the dataset to numpy
		interactionData = np.array(interactionData, dtype='object')

		return interactionData
	
	def getHiCInteractionsFromFile(self, interactionsFile):
		"""
			Read all Hi-C interactions from the interactions file
			
			- Column 1 is the starting region of the interaction
			- Column 2 is the ending region of the interaction
			
			
			
		"""
		seenRegions = dict() #use a dictionary to quickly determine if we have added this region before to keep the regions unique
		regions = []
		interactions = dict() #for now I won't make objects for interactions, do we really need them? 
		with open(interactionsFile, 'r') as inF:
			
			lineCount = 0
			for line in inF:
				line = line.strip()
				
				if lineCount < 1: #skip header
					lineCount += 1
					continue
				
				splitLine = line.split(",") #csv format

				interactionStart = splitLine[0]
				interactionEnd = splitLine[1]
				
				#Split the regions into the chromosome and region/bin
				splitInteractionStart = interactionStart.split("_")
				splitInteractionEnd = interactionEnd.split("_")
				
				chr1 = splitInteractionStart[0]
				start1 = int(splitInteractionStart[1])
				end1 = start1 + int(settings.interactions['binSize'])
				
				chr2 = splitInteractionEnd[0]
				start2 = int(splitInteractionEnd[1])
				end2 = start2 + int(settings.interactions['binSize'])
				
				if interactionStart not in seenRegions:
					regions.append([chr1, start1, end1, interactionStart])
					seenRegions[interactionStart] = len(regions) #keep the index at which the region is
				if interactionEnd not in seenRegions:
					regions.append([chr2, start2, end2, interactionEnd])
					seenRegions[interactionEnd] = len(regions)
				
				if interactionStart not in interactions:
					interactions[interactionStart] = []
				if interactionEnd not in interactions:
					interactions[interactionEnd] = [] #Some interactions are only in the end region
				
				interactions[interactionStart].append(interactionEnd)
				interactions[interactionEnd].append(interactionStart)
				
		
		regions = np.array(regions, dtype="object")
		#interactions = np.array(interactions, dtype="object")

		return interactions, regions
	
	def mapTADsToGenes(self, genes, tadData):
		"""
			Adds the left and right TAD to each gene object.
		"""
		print tadData
		#For each gene, check which TADs are on the correct chromosome.
		
		#Then see which ones are directly on the left and directly on the right of the gene.
		previousChr = None
		for gene in genes:
			
			#1. Make a subset of TADs on the right chromosome. There should be only 1 chromosome
			
			if "chr" + str(gene.chromosome) != previousChr:
				
				#Find the two subsets that match on both chromosomes. 
				matchingChrInd = tadData[:,0] == "chr" + str(gene.chromosome)
				
				#It is not even necessary to make 2 lists if both chromosomes are the same, we could use a reference without re-allocating
				chrSubset = tadData[np.where(matchingChrInd)]
				
				#Make sure to update the previous chromosome when it changes
				previousChr = "chr" + str(gene.chromosome)
				
			if np.size(chrSubset) < 1:
				continue #no need to compute the distance, there are no genes on these chromosomes
			
			#Within this subset, check which TADs are on the right and left of the current gene
			
			#TADs on the left have an end coordinate smaller than the gene start coordinate. Similar for the right TADs
			
			leftTADs = chrSubset[np.where(chrSubset[:,2] <= gene.start)]
			rightTADs = chrSubset[np.where(chrSubset[:,1] > gene.end)]
			
			#Compute the distance to each of these TADs and take the TADs with the minimum distance
			if leftTADs.shape[0] > 0:
				leftTADsDistance = np.abs(leftTADs[:,2] - gene.start)
				nearestLeftTAD = leftTADs[np.argmin(leftTADsDistance),3]
				gene.setLeftTAD(nearestLeftTAD)
			else:
				gene.setLeftTAD(None)
			if rightTADs.shape[0] > 0:
				rightTADsDistance = np.abs(rightTADs[:,1] - gene.end)
				nearestRightTAD = rightTADs[np.argmin(rightTADsDistance),3]
				gene.setRightTAD(nearestRightTAD)
			else:
				gene.setRightTAD(None)

			
			
		
	def mapEQTLsToGenes(self, eQTL, genes, geneSymbol):
		"""
			Map the right gene object to the eQTL object. 
		
		"""
		for gene in genes:
			
			if gene.name == geneSymbol:
				
				gene.addEQTL(eQTL)
	
	def mapInteractionsToGenes(self, genes, interactionData):
		"""
			Take Hi-C interactions as input (see getInteractionsFromFile for the format) and link these to the causal genes. 
		
		"""
		
		#1. For each gene, find the non-coding regions that have an interaction with this gene. 
		
		previousChr = None
		for gene in genes:
			
			#Get the interactions bby the name of the gene
			interactionsSubset = interactionData[interactionData[:,3] == gene.name,5] #get the objects
			
			#add interaction objects to the genes
			gene.setInteractions(interactionsSubset)
			
	
	def mapInteractionsToTads(self, interactions, regions, tadData):
		"""
			Determine which interactions take place within which TAD.
			Interactions will be mapped to TAD objects.
			
			- For now, I remove all interactions that take place with regions outside of the TAD. For the purpose of this script, we only look at interactions that are gained as a
			result of disrupted TAD boundaries, so regions that are already outside of TAD boundaries are questionable. Are these errors? Are the TAD boundary definitions not correct?
			
			
			Returns the tadData, where the objects now have interactions mapped to them (but these are objects, so by reference this should not be necessary)
			
		"""
		print "Mapping interactions to TADs"
		previousChromosome = 0
		for tad in tadData:
			
			#Find all interactions taking place within this TAD.
			
			#The interactions are currently intrachromosomal, but may later be interchromosomal
			#Thus for now we can just match on 1 chromosome
			
			#Get all regions that are within the TAD
			#Find all corresponding interactions between the regions within the TAD (make sure that these do not go outside of the boundary, this may indicate data errors)
			
			if tad[0] != previousChromosome:
				previousChromosome = tad[0]
				regionChrSubset = regions[np.where(regions[:,0] == tad[0])] #First get the subset of all regions on the current chromosome, TADs are sorted

			
			#Find which regions are within this TAD
			#All regions must have their start position larger than the TAD start and the end smaller than the TAD end
			startMatches = regionChrSubset[:,1] >= tad[1]
			endMatches = regionChrSubset[:,2] <= tad[2]
			
			allMatches = startMatches * endMatches
			matchingRegions = regionChrSubset[allMatches,:]
			
			#Get the interactions of these matching regions and ensure that these are within the TAD boundaries
			
			#Find all the interactions mapping to this region.
			 
			matchingRegionsInteractions = []
			for region in matchingRegions:
				regionInteractions = interactions[region[3]] #the interacting regions
				for interaction in regionInteractions: #make sure that the interacting regions are actually within the TAD
					
					splitInteraction = interaction.split("_")
					interactionChrom = splitInteraction[0]
					splitInteractionStartRegion = int(splitInteraction[1])
					splitInteractionEndRegion = splitInteractionStartRegion + settings.interactions['binSize']
					
					if splitInteractionStartRegion < tad[2]: #remove the interacting regions where the start of the interaction is outside of the TAD
						#Make the final format for the interactions and then add them to the TAD
						markedUpInteraction = [region[0], region[1], region[2], interactionChrom, splitInteractionStartRegion, splitInteractionEndRegion]
						matchingRegionsInteractions.append(markedUpInteraction)
						
						
			#Add the interactions to this TAD			
			tad[3].setInteractions(matchingRegionsInteractions)
			
		
		
		return tadData 
		
	def determineGainedInteractions(self, svData, tadData):
		"""
			- Function name??
			- Split better into respective parts
		"""
		
		#Loop through all SVs and see which ones have overlap with any TAD.
		#The SVs are sorted per cancer type, so taking chromosome subsets may not gain as much speed

		for sv in svData:
			print "sv: ", sv
			
			##Here we need to take translocations into account as well.
			#If the SV is intrachromosomal, we should find the left TAD by chr1, s1 and the right TAD by e2.
			#if the SV is interchromosomal, we should find the left TAD by chr1, s1 and the right TAD by chr2 and e2. 
			#We may slightly overshoot TADs if there is a difference in the start and end coordinates, but this may do for now.
			
			
			if sv[0] == sv[3]: #intrachromosomal
				leftTadChr = 'chr' + sv[0]
				svStart = sv[1] #s1
				svEnd = sv[5] #e2
				
				#Now search for the matches on the left and right TAD by these coordinates
				#First get the right chromosome subset
				tadChromosomeSubset = tadData[np.where(tadData[:,0] == leftTadChr)] #Limit to intrachromosomal for now for testing purposes

				tadStartMatches = svStart >= tadChromosomeSubset[:,1]
				tadEndMatches = svStart <= tadChromosomeSubset[:,2]
				
				allMatches = tadStartMatches * tadEndMatches
	
				svStartOverlappingTads = tadChromosomeSubset[allMatches]
				if svStartOverlappingTads.shape[0] < 1  or svStartOverlappingTads.shape[0] > 1:
					continue
				
				#Search for the right TAD on the same chromosome
				#Find the TAD that is on the end of the SV
				#The end of the SV should be after the TAD start, and before the TAD end. 
				tadStartMatches = svEnd >= tadChromosomeSubset[:,1]
				tadEndMatches = svEnd <= tadChromosomeSubset[:,2]
				
				allMatches = tadStartMatches * tadEndMatches
	
				svEndOverlappingTads = tadChromosomeSubset[allMatches]
				
				#If the end of the SV does not overlap any TAD, skip it.
				#There should be only one TAD on each end!! So then we skip it as well
				if svEndOverlappingTads.shape[0] < 1 or svEndOverlappingTads.shape[0] > 1:
					continue
				
			if sv[0] != sv[3]: #interchromosomal
				leftTadChr = 'chr' + sv[0]
				rightTadChr = 'chr' + sv[3]
				svStart = sv[1] #s1
				svEnd = sv[5] #e2
				
				#Now search for the matches on the left and right TAD by these coordinates
				#First get the right chromosome subset
				tadChromosomeSubset = tadData[np.where(tadData[:,0] == leftTadChr)] #Limit to intrachromosomal for now for testing purposes

				tadStartMatches = svStart >= tadChromosomeSubset[:,1]
				tadEndMatches = svStart <= tadChromosomeSubset[:,2]
				
				allMatches = tadStartMatches * tadEndMatches
	
				svStartOverlappingTads = tadChromosomeSubset[allMatches]
				if svStartOverlappingTads.shape[0] < 1  or svStartOverlappingTads.shape[0] > 1:
					continue
				
				#Search for the right TAD on another chromosome
				tadChromosomeSubset = tadData[np.where(tadData[:,0] == rightTadChr)] #Limit to intrachromosomal for now for testing purposes
				
				#Find the TAD that is on the end of the SV
				#The end of the SV should be after the TAD start, and before the TAD end. 
				tadStartMatches = svEnd >= tadChromosomeSubset[:,1]
				tadEndMatches = svEnd <= tadChromosomeSubset[:,2]
				
				allMatches = tadStartMatches * tadEndMatches
	
				svEndOverlappingTads = tadChromosomeSubset[allMatches]
				
				#If the end of the SV does not overlap any TAD, skip it.
				#There should be only one TAD on each end!! So then we skip it as well
				if svEndOverlappingTads.shape[0] < 1 or svEndOverlappingTads.shape[0] > 1:
					continue
				
	
			
			#Sometimes the SV is within one TAD. Then we skip it as well as it is not informative for gaining interactions.
			if svStartOverlappingTads[0][1] == svStartOverlappingTads[0][1]: #we can assume that there is one entry due to checks above
				continue
			#There should not be two TADs with the same start coordinate by the way the data was designed, but check for TADs having the same end as well anyway to make sure
			if svStartOverlappingTads[0][2] == svStartOverlappingTads[0][2]: #we can assume that there is one entry due to checks above
				continue

			#Otherwise, if both SV ends overlap a TAD, and the TAD is not the same at both ends, get the interactions of the TADs on the left and right.
			print svStartOverlappingTads
			print svEndOverlappingTads

			exit()	
		
		
		
		
		
		
		
		
		
		return 0
		
		
	def mapSVsToNeighborhood(self, genes, svData, tadData):
		"""
			Take as input gene objects with the neighborhood pre-set, and search through the SVs to find which SVs overlap the genes, TADs and eQTLs in the gene neighborhood
		
			The TADs are also parsed as input, because when we compute gained interactions we search through other TADs that are on the other end of the SV breakpoint. This is the TAD from which we can
			expect interactions in our current TAD. 
		
			!!!!!! This function will need to be properly split into multiple functions for the different data types.
			TODO:
			- Split into multiple functions
			- Move the gained interactions outside of the left/right TAD check. See comments below. 
		
		"""
		
		#First map the SVs to TADs to see if we can infer gained interactions
		self.determineGainedInteractions(svData, tadData)
		exit()
		
		previousChr = None
		for gene in genes[:,3]:
			
			#We first split the data per chromosome for faster overlapping. Thus, if the chromosome of the gene is 1, then we find all SVs for which either chromosome 1 or chromosome 2 (translcoations)
			#are on chromosome 1. The genes are sorted, so this saves time when doing overlap with large sets of SVs or SNVs. 
			
			#To overlap, there are SVs that either have overlap with elements in the gene neighborhood on chr1 or chr2 (if translocation). Thus, we make 3 different sets
			#for SVs that are not translocations (checking if overlapping with chromosome 1, start 1 and end 2 (intraChrSubset)).
			#If the SV is a translocation, we can match either on chromosome 1 or chromosome 2. Thus we have 2 sets of SVs on chr1, where we overlap with s1 and e1, and on chr2, where we overlap with
			#s2 and e2. These are then all combined into one large set, so that we can immediately do the overlap at once for all elements in the neighborhood on the chromosomes of the SVs. 
			
			if gene.chromosome != previousChr:
				
				matchingSvChr1Ind = svData[:,0] == str(gene.chromosome)
				matchingSvChr2Ind = svData[:,3] == str(gene.chromosome)
				
				#Intra and chr1 and chr2 will overlap if we don't exclude the positions where both chr1 and chr2 are the same. 
		
				notChr1Matches = svData[:,3] != str(gene.chromosome)
				chr1OnlyInd = matchingSvChr1Ind * notChr1Matches
				
				notChr2Matches = svData[:,0] != str(gene.chromosome)
				chr2OnlyInd = matchingSvChr2Ind * notChr2Matches
				
				#intraSubset: chr1 and chr2 both match
				matchingChr1AndChr2Ind = matchingSvChr1Ind * matchingSvChr2Ind
				intraSubset = svData[matchingChr1AndChr2Ind]
				
				#interChr1Subset: only chr1 matches
				interChr1Subset = svData[chr1OnlyInd]
				
				#interChr2Subset: only chr2 matches
				interChr2Subset = svData[chr2OnlyInd]
				
		
				#Now concatenate them into one set, but keep the formatting the same as: chr, start, end
				
				svChr1Subset = np.empty([interChr1Subset.shape[0],11],dtype='object')
				svChr1Subset[:,0] = interChr1Subset[:,0] #For chromosome 1, we use just the first chromosome, s1 and e1.
				svChr1Subset[:,1] = interChr1Subset[:,1] #For chromosome 1, we use just the first chromosome, s1 and e1.
				svChr1Subset[:,2] = interChr1Subset[:,2] #For chromosome 1, we use just the first chromosome, s1 and e1.
				svChr1Subset[:,3] = None #Here fill with None because the SVs need to have the cancer type and sample name in the same place in the array as the SNVs, but the SNVs don't have this info. Also just use None because we won't use the other position anymore.
				svChr1Subset[:,4] = None
				svChr1Subset[:,5] = None
				svChr1Subset[:,6] = interChr1Subset[:,7]
				svChr1Subset[:,7] = interChr1Subset[:,6]
				
				#Make the subset for the chr2 matches
				svChr2Subset = np.empty([interChr2Subset.shape[0],11], dtype='object')
				svChr2Subset[:,0] = interChr2Subset[:,0] #For chromosome 2, we use just the second chromosome, s2 and e2.
				svChr2Subset[:,1] = interChr2Subset[:,4] 
				svChr2Subset[:,2] = interChr2Subset[:,5] 
				svChr2Subset[:,3] = None
				svChr2Subset[:,4] = None
				svChr2Subset[:,5] = None
				svChr2Subset[:,6] = interChr2Subset[:,7] 
				svChr2Subset[:,7] = interChr2Subset[:,6] 
				
				
				#For the intra subset, we need to use s1 and e2.
				svIntraSubset = np.empty([intraSubset.shape[0],11], dtype='object')
				svIntraSubset[:,0] = intraSubset[:,0] #For chromosome 2, we use chromosome 1, s1 and e2.
				svIntraSubset[:,1] = intraSubset[:,1] 
				svIntraSubset[:,2] = intraSubset[:,5] 
				svIntraSubset[:,3] = None
				svIntraSubset[:,4] = None
				svIntraSubset[:,5] = None
				svIntraSubset[:,6] = intraSubset[:,7] 
				svIntraSubset[:,7] = intraSubset[:,6] 
				
				#Now concatenate the arrays
				svSubset = np.concatenate((svChr1Subset, svChr2Subset, svIntraSubset))
			
				previousChr = gene.chromosome
			
			if np.size(svSubset) < 1:
				continue #no need to compute the distance, there are no TADs on this chromosome
			
			#Check which of these SVs overlap with the gene itself
			
			geneStartMatches = gene.start <= svSubset[:,2]
			geneEndMatches = gene.end >= svSubset[:,1]
			
			geneMatches = geneStartMatches * geneEndMatches #both should be true, use AND for concatenating
		
			svsOverlappingGenes = svSubset[geneMatches]
			
			
			#Get the SV objects and link them to the gene
			gene.setSVs(svsOverlappingGenes)
			
			#Check which SVs overlap with the right/left TAD
			
			#For the TAD, we also want to know which interactions are potentially gained.
			#If the boundary of a TAD is disrupted, we should get the TAD on the left of the SV and the TAD on the right of the SV breakpoint.
			#These are the interactions that may end up in the other TAD.
			#There are two possibilities:
			#If this is the left TAD, then either:
			#1. The left TAD does not overlap with the gene itself, and the left TAD boundary closest to the gene is the end of the left TAD. In this case:
				#1. The TAD to the right of the left TAD overlaps with the gene. Here we know that the gained interactions can potentially be with this gene.
				#2. The TAD to the right does not overlap with the gene. We discard this, since we don't know if this is an error in the data, or if this gene is outside of the TAD.
			#2. The left TAD does overlap with the gene itself. Here the options are:
				#1. The SV overlaps with the left side of the left TAD. Thus, the possible interactions are between this TAD and the TAD on the left of it
				#2. The SV overlaps with the right side of the left TAD. Thus, the possible interactions are between this TAD and the TAD on the right of it.
			#If the SV removes a large part of the genome, there is a chance that multiple TADs are gone. Thus, we need to check what the TADs are on the breakpoints of the SV. 
			
			####! I don't think checking the overlap with the left and right TAD boundaries of genes is the most logical thing to do, it is probably better to separate the gained
			#interactions from the genes at first, where we go through ALL TAD boundaries with SVs first, obtain the interactions, and THEN link the potentially gained interactions to genes
			#instead of the other way around that we do now by first mapping TADs to genes, and then looking for disruptions in those TADs. In what we do now it may happen that TADs are
			#counted twice in the gene scoring because the left/right TAD boundaries may be from the same TAD if it lies across the gene. 
			
			if gene.leftTAD != None:
				
				leftTADStartMatches = gene.leftTAD.start <= svSubset[:,2]
				leftTADEndMatches = gene.leftTAD.end >= svSubset[:,1]
				
				leftTADMatches = leftTADStartMatches * leftTADEndMatches
				
				svsOverlappingLeftTAD = svSubset[leftTADMatches]
				gene.leftTAD.setSVs(svsOverlappingLeftTAD)
				
				
				#For each of the SVs overlapping with the left TAD boundary, get the TADs on the right and on the left of the SV (should be within a TAD)
				for sv in svsOverlappingLeftTAD:
					print "sv: ", sv
					
					#Find the TAD where the SV start is larger than the TAD start, but smaller than the TAD end.
					
					#First get the right chromosome subset
					tadChromosomeSubset = tadData[np.where(tadData[:,0] == 'chr' + sv[0])] #Limit to intrachromosomal for now for testing purposes
					
					tadStartMatches = sv[1] >= tadChromosomeSubset[:,1]
					tadEndMatches = sv[1] <= tadChromosomeSubset[:,2]
					
					allMatches = tadStartMatches * tadEndMatches

					svStartOverlappingTads = tadChromosomeSubset[allMatches]
					
					#If the SV does not overlap any TAD, we should skip it as we cannot say anything about gained interactions.
					#There should be only one TAD on each end!! So then we skip it as well
					if svStartOverlappingTads.shape[0] < 1  or svStartOverlappingTads.shape[0] > 1:
						continue
					

					#Find the TAD that is on the end of the SV
					#The end of the SV should be after the TAD start, and before the TAD end. 
					tadStartMatches = sv[2] >= tadChromosomeSubset[:,1]
					tadEndMatches = sv[2] <= tadChromosomeSubset[:,2]
					
					allMatches = tadStartMatches * tadEndMatches

					svEndOverlappingTads = tadChromosomeSubset[allMatches]
					
					#If the end of the SV does not overlap any TAD, skip it.
					#There should be only one TAD on each end!! So then we skip it as well
					if svEndOverlappingTads.shape[0] < 1 or svEndOverlappingTads.shape[0] > 1:
						continue
					
					#Sometimes the SV is within one TAD. Then we skip it as well as it is not informative for gaining interactions.
					if svStartOverlappingTads[0][1] == svStartOverlappingTads[0][1]: #we can assume that there is one entry due to checks above
						continue
					#There should not be two TADs with the same start coordinate by the way the data was designed, but check for TADs having the same end as well anyway to make sure
					if svStartOverlappingTads[0][2] == svStartOverlappingTads[0][2]: #we can assume that there is one entry due to checks above
						continue

					#Otherwise, if both SV ends are within a TAD, and the TAD is not the same at both ends, get the interactions of the TADs on the left and right.
					print svStartOverlappingTads
					print svEndOverlappingTads
					
					
					
					
					
					exit()
				
				
				
			
			if gene.rightTAD != None:
				
				rightTADStartMatches = gene.rightTAD.start <= svSubset[:,2]
				rightTADEndMatches = gene.rightTAD.end >= svSubset[:,1]
				
				rightTADMatches = rightTADStartMatches * rightTADEndMatches
			
				svsOverlappingRightTAD = svSubset[rightTADMatches]
				gene.rightTAD.setSVs(svsOverlappingRightTAD)
			
			#Check which SVs overlap with the eQTLs
			
			#Repeat for eQTLs. Is the gene on the same chromosome as the eQTL? Then use the above chromosome subset.
			
			geneEQTLs = gene.eQTLs
			
			for eQTL in geneEQTLs: #only if the gene has eQTLs
				
				
				
				startMatches = eQTL.start <= svSubset[:,2]
				endMatches = eQTL.end >= svSubset[:,1]
				
				allMatches = startMatches * endMatches
				
				
				
				svsOverlappingEQTL = svSubset[allMatches]

				
				eQTL.setSVs(svsOverlappingEQTL)
			
			#Check which SVs overlap with the interactions.
			for interaction in gene.interactions:
				
				startMatches = interaction.start1 <= svSubset[:,2]
				endMatches = interaction.end1 >= svSubset[:,1]
				
				allMatches = startMatches * endMatches
				
				svsOverlappingInteraction = svSubset[allMatches]
				
				interaction.setSVs(svsOverlappingInteraction)
		
		
		
	def mapSNVsToNeighborhood(self, genes, snvData, eQTLData):
		"""
			Same as the function for mapping SVs to the neighborhood, but then for SNVs.
			!!!!!  Will also need to be properly split into multiple functions, many pieces of code can be re-used. 
		
			TODO:
			- update the documentation in this code
			- Split into functions, re-use code for the SVs
		
		"""
		import time
		import math
		
		
		#### Some testing to link SNVs to eQTLs quickly
		#Do a pre-filtering to have a much shorter list of SNVs and make overlapping faster, there wil be many SNVs that never overlap any eQTL so we don't need to look at these. 
		
		#1. Define ranges for the eQTLs
		#2. Determine the boundaries from the range
		ranges = []
		boundaries = []
		for eQTL in eQTLData:
			#eQTLRange = (eQTL.start, eQTL.end)
			#ranges.append(eQTLRange)
			boundaries.append(eQTL.start)
			boundaries.append(eQTL.end)

		#3. Obtain the SNV coordinates as one list
		snvEnds = []
		snvStarts = []
		for snv in snvData:
			snvStarts.append(snv[1])
			snvEnds.append(snv[2])
			
		boundaries = np.array(boundaries)
		snvStarts = np.array(snvStarts)
		snvEnds = np.array(snvEnds)
		
		#Do the overlap to get the eQTLs that have overlap with ANY SNV on ANY chromosome. From here we can further subset.
		startTime = time.time()
		
		
		#I didn't document this and then forgot what it does... 
		startOverlaps = np.where(np.searchsorted(boundaries, snvStarts, side="right") %2)[0]
		endOverlaps = np.where(np.searchsorted(boundaries, snvEnds, side="right") %2)[0]
		
		allEQTLOverlappingSNVs = snvData[np.union1d(startOverlaps, endOverlaps)]
		
		#Remove any overlap between these sets
		
		
		#Then repeat filtering for genes and TADs.
		
		geneBoundaries = []
		leftTADBoundaries = []
		rightTADBoundaries = []
		for gene in genes:
			
			geneBoundaries.append(gene[1])
			geneBoundaries.append(gene[2])
			
			if gene[3].leftTAD is not None:

				leftTADBoundaries.append(gene[3].leftTAD.start)
				leftTADBoundaries.append(gene[3].leftTAD.end)
			
			if gene[3].rightTAD is not None:
				
				rightTADBoundaries.append(gene[3].rightTAD.start)
				rightTADBoundaries.append(gene[3].rightTAD.end)
		
			
		startOverlaps = np.where(np.searchsorted(geneBoundaries, snvStarts, side="right") %2)[0]
		endOverlaps = np.where(np.searchsorted(geneBoundaries, snvEnds, side="right") %2)[0]
		
		allGeneOverlappingSNVs = snvData[np.union1d(startOverlaps, endOverlaps)]
		
		startOverlaps = np.where(np.searchsorted(leftTADBoundaries, snvStarts, side="right") %2)[0]
		endOverlaps = np.where(np.searchsorted(leftTADBoundaries, snvEnds, side="right") %2)[0]
		
		allLeftTADOverlappingSNVs = snvData[np.union1d(startOverlaps, endOverlaps)]
		
		startOverlaps = np.where(np.searchsorted(rightTADBoundaries, snvStarts, side="right") %2)[0]
		endOverlaps = np.where(np.searchsorted(rightTADBoundaries, snvEnds, side="right") %2)[0]
		
		allRightTADOverlappingSNVs = snvData[np.union1d(startOverlaps, endOverlaps)]
		
		
		
		startTime = time.time()
		previousChr = None
		for gene in genes[:,3]:
			
			#Make a subset of SNVs on the right chromosome
			
			if gene.chromosome != previousChr:
				
				endTime = time.time()
				
				print "new chromosome: ", gene.chromosome
				print "time for one chromosome: ", endTime - startTime
				startTime = time.time()
				matchingChrInd = snvData[:,0] == str(gene.chromosome)

				snvSubset = snvData[matchingChrInd]
				
				#Make the chr subsets for each element type
				matchingChrIndEQTL = allEQTLOverlappingSNVs[:,0] == str(gene.chromosome)
				matchingChrIndGenes = allGeneOverlappingSNVs[:,0] == str(gene.chromosome)
				matchingChrIndLeftTADs = allLeftTADOverlappingSNVs[:,0] == str(gene.chromosome)
				matchingChrIndRightTADs = allRightTADOverlappingSNVs[:,0] == str(gene.chromosome)
				
				eQTLSNVSubset = allEQTLOverlappingSNVs[matchingChrIndEQTL]
				geneSNVSubset = allGeneOverlappingSNVs[matchingChrIndGenes]
				leftTADSNVSubset = allLeftTADOverlappingSNVs[matchingChrIndLeftTADs]
				rightTADSNVSubset = allRightTADOverlappingSNVs[matchingChrIndRightTADs]
				
				previousChr = gene.chromosome
			
			if np.size(snvSubset) < 1:
				continue #no need to compute the distance, there are no TADs on this chromosome
			
			#Make a smaller subset for the interval. Is this speeding up the code?
			
			#Search through blocks instead of doing the overlap on the whole set at once.
		
			
		
		
			#Search through this smaller block for the gene, TADs and eQTLs at once
			geneStartMatches = gene.start <= geneSNVSubset[:,2]
			geneEndMatches = gene.end >= geneSNVSubset[:,1]
		
			geneMatches = geneStartMatches * geneEndMatches #both should be true, use AND for concatenating
		
			#Get the SNV objects of the overlapping SNVs
			
			snvsOverlappingGenes = geneSNVSubset[geneMatches]
			#snvsOverlappingGenes = snvSubset[geneMatches]
			
			#Get the SV objects and link them to the gene
			gene.setSNVs(snvsOverlappingGenes)
			
			if gene.leftTAD != None:
				
				leftTADStartMatches = gene.leftTAD.start <= leftTADSNVSubset[:,2]
				leftTADEndMatches = gene.leftTAD.end >= leftTADSNVSubset[:,1]
				
				
				leftTADMatches = leftTADStartMatches * leftTADEndMatches
				
				snvsOverlappingLeftTAD = leftTADSNVSubset[leftTADMatches]
				
				gene.leftTAD.setSNVs(snvsOverlappingLeftTAD)
			
			if gene.rightTAD != None:
				
				
				rightTADStartMatches = gene.rightTAD.start <= rightTADSNVSubset[:,2]
				rightTADEndMatches = gene.rightTAD.end >= rightTADSNVSubset[:,1]
				 
				rightTADMatches = rightTADStartMatches * rightTADEndMatches
			
				snvsOverlappingRightTAD = rightTADSNVSubset[rightTADMatches]
				gene.rightTAD.setSNVs(snvsOverlappingRightTAD)
			
			#Check which SVs overlap with the eQTLs
			
			#Repeat for eQTLs. Is the gene on the same chromosome as the eQTL? Then use the above chromosome subset.
			
			geneEQTLs = gene.eQTLs
			
			for eQTL in geneEQTLs: #only if the gene has eQTLs
				
				startMatches = eQTL.start <= eQTLSNVSubset[:,2]
				endMatches = eQTL.end >= eQTLSNVSubset[:,1]
				
				allMatches = startMatches * endMatches
				
				
				snvsOverlappingEQTL = eQTLSNVSubset[allMatches]
			
				
				eQTL.setSNVs(snvsOverlappingEQTL)
				
				
			#Interactions have not been implemented for SNVs