"""
	Set of scripts intended to do ranking of (causal) genes based on their neighborhood and the influence that SVs have in this neighborhood. 

	The idea is to look at all known causal genes. The neighborhood may consist of eQTLs that have an effect on this gene, or TADs directly neighboring the gene.
	If we annotate causal genes with these effects, then we can check for potential effects if anything in the neighborhood is affected by SVs.
	Using some magical statistics, we can then make a prediction on how much more likely the effects on the neighborhood are to be disruptive to the causal genes than expected by random chance.
	Later, this format can be extended to non-causal genes as well. 


	The setup of these scripts will initally be (it will not be too pretty and perfect at first):
	
	- The main script where the input (genes) are parsed and the relevant scripts are called
	- The getNeighborhood class, where things such as neighboring TADs, related eQTLs and overlapping SVs are obtained
	- The RankGenes class, where the genes are ranked by how likely they are causal for the disease depending on the SVs affecting their neighborhood
	- The output will be a matrix with all causal genes in the columns, and the relevant SVs in the rows.
	
	
	Using a gene-based approach will likely be quicker than an SV-based approach, and we can get the relevant SVs through the genes. If an SV is never affecting any of our features defined as interesting, there is no
	need to look at that SV at all. This idea may change along the way.
	

"""
import sys
import numpy as np
import random

from gene import Gene
from neighborhoodDefiner import NeighborhoodDefiner
from geneRanking import GeneRanking
from sv import SV

#1. Read and parse the causal genes

def readCausalGeneFile(causalGeneFile):
		
	cosmicGenes = [] #later change this into numpy array for quick overlap
	with open(causalGeneFile, 'r') as geneFile:
		
		lineCount = 0
		header = []
		for line in geneFile:
			splitLine = line.split("\t")
			#First extract the header and store it in the dictionary to remove dependency on the order of columns in the file
			if lineCount < 1:
	
				header = splitLine
				lineCount += 1
				continue
				
			#Obtain the gene name and gene position
			
			geneSymbolInd = header.index('Gene Symbol')
			genePositionInd = header.index('Genome Location')
			
			geneSymbol = splitLine[geneSymbolInd]
			genePosition = splitLine[genePositionInd]
			
			#Split the gene position into chr, start and end
			
			colonSplitPosition = genePosition.split(":")
			dashSplitPosition = colonSplitPosition[1].split("-")
			
			chromosome = colonSplitPosition[0]
			start = dashSplitPosition[0].replace('"',"") #apparently there are some problems with the data, sometimes there are random quotes in there
			end = dashSplitPosition[1].replace('"', "")
			
			if start == '' or end == '':
				continue
			
			gene = Gene(geneSymbol, chromosome, int(start), int(end)) #Keep in objects for easy access of properties related to the neighborhood of the gene
			
			cosmicGenes.append(gene)
			
	
	#cosmicGenes = np.array(cosmicGeneList, dtype='object')
	
	return cosmicGenes

causalGeneFile = sys.argv[1]
causalGenes = readCausalGeneFile(causalGeneFile)

#1.2 Also read the SVs here already, so that we can provide a random set of SVs to the same function later on
def getSVsFromFile(svFile):
		
	variantsList = []
	
	with open(svFile, 'rb') as f:
		
		lineCount = 0
		header = []
		for line in f:
			line = line.strip()
			splitLine = line.split("\t")
			
			#First extract the header and store it in the dictionary to remove dependency on the order of columns in the file
			if lineCount < 1:
	
				header = splitLine
				lineCount += 1
				continue
			
			#Now extract the chromosome, start and end (there are multiple)
			chr1Index = header.index("chr1")
			s1Index = header.index("s1")
			e1Index = header.index("e1")
	
			chr2Index = header.index("chr2")
			s2Index = header.index("s2")
			e2Index = header.index("e2")
	
			cancerTypeIndex = header.index("cancer_type")
			sampleNameIndex = header.index("sample_name")
			
			cancerType = splitLine[cancerTypeIndex]
			sampleName = splitLine[sampleNameIndex]
	
			#If the coordinates are missing on the second chromosome, we use the coordinates of the first chromosome unless chr 1 and chr 2 are different.
			if splitLine[chr1Index] == splitLine[chr2Index]:
				if splitLine[s2Index] == 'NaN':
					splitLine[s2Index] = int(splitLine[s1Index])
					
				if splitLine[e2Index] == 'NaN':
					splitLine[e2Index] = int(splitLine[e1Index])
			else:
				if splitLine[chr2Index] == 'NaN':
					continue # This line does not have correct chromosome 2 information (should we be skipping it?)
	
			s1 = int(splitLine[s1Index])
			e1 = int(splitLine[e1Index])
			s2 = int(splitLine[s2Index])
			e2 = int(splitLine[e2Index])
			chr2 = splitLine[chr2Index]
			
			chr1 = splitLine[chr1Index]
			
			svObject = SV(chr1, s1, e1, chr2, s2, e2, sampleName, cancerType)
			#chr 1, start, end, chr2, start2, end2
			variantsList.append([chr1, s1, e1, chr2, s2, e2, cancerType, sampleName, svObject])
	
	regions = np.array(variantsList, dtype='object')
	
	return regions		
			
svFile = "../../data/TPTNTestSet/TP.txt" #should be a setting
svData = getSVsFromFile(svFile)

#2. Get the neighborhood for these genes
#NeighborhoodDefiner(causalGenes, svData) 

#3. Do simple ranking of the genes and report the causal SVs
#GeneRanking(causalGenes)


#4. Randomly shuffle the SVs 1000 times

#4.1 Get the maximum length of each chromosome to ensure that SVs will stay within the bounds

###Make this a setting later
hg19CoordinatesFile = "../../data/chromosomes/hg19Coordinates.txt"


hg19Coordinates = dict()
with open(hg19CoordinatesFile, 'r') as f:
	lineCount = 0
	for line in f:
		line = line.strip()
		
		if lineCount < 1: #skip header
			lineCount += 1
			continue
		
		splitLine = line.split("\t")
		
		chromosome = splitLine[0]
		end = splitLine[3]
		
		hg19Coordinates[chromosome] = int(end)

print hg19Coordinates

#4.2 Shuffle the SVs
#For the current chromosome we get the maximum decrease/increase that this SV can get
#The new coordinate can be derived randomly from this range

shuffledSvs = []

for sv in svData:
	
	
	#1. Get the min max bounds for the chromosomes (2 in case of translocation)
	#The minimum start coordinate is just 1, the maximum start is the length-start
	#The end coordinate is just start + length
	
	chromosome1 = sv[0]
	chromosome2 = sv[3]
	
	chr1Length = hg19Coordinates[chromosome1]
	chr2Length = hg19Coordinates[chromosome2]
	
	start1 = int(sv[1])
	start2 = int(sv[2])
	
	startDifference = start2 - start1
	
	end1 = int(sv[4])
	end2 = int(sv[5])
	
	endDifference = end2 - end1
	
	minimumStart1 = 1	
	maximumStart1 = chr1Length - start1
	
	#If the start position is after the bounds of the chromosome, the maximum start should be the length of the chromosome - the length of the SV.

	if maximumStart1 < 0:
		maximumStart1 = chr1Length - svLength

	newStart1 = random.randint(minimumStart1, maximumStart1)
	newStart2 = newStart1 + startDifference
	
	#If the chromosomes are the same, use the maximum start for chr1. Otherwise use different chromosomes.
	if chromosome1 == chromosome2:
	
		#difference between end1 and start 1
		svLength = end1 - start1
			
		newEnd1 = newStart1 + svLength
		newEnd2 = newEnd1 + endDifference
		
	else: #If the chromosomes are not the same, the start and end coordinates do not necessarily need to be equidistant. Here we can randomly sample the start on both chromosomes 		
		maximumStart2 = chr2Length - start2
		
		#If the chr2 start is outside of the bounds, we only need to subtract the difference between the positions on chromosome 2. 
		if maximumStart2 < 0:
			maximumStart2 = chr2Length - endDifference
		
		#The end coordinate here is actually the start coordinate for chromosome 2.
		newEnd1 = random.randint(minimumStart1, maximumStart2) #chr2 has the same start coordinate as chr 1
		newEnd2 = newEnd1 + endDifference
		
	#Sample name and cancer type can be copied from the other SV. Chromosome information also remains the same. 	
	newSvObj = SV(chromosome1, newStart1, newStart2, chromosome2, newEnd1, newEnd2, sv[6], sv[7])
	newSv = [chromosome1, newStart1, newStart2, chromosome2, newEnd1, newEnd2, sv[6], sv[7], newSvObj]	
	shuffledSvs.append(newSv)	

shuffledSvs = np.array(shuffledSvs, dtype="object")	

#5. Re-obtain the gene neighborhood and the SVs overlapping these (could be optimized, we only need to re-associate the SVs)
print shuffledSvs

#We have to make sure here that the objects will not get overlaps with previous objects
NeighborhoodDefiner(causalGenes, shuffledSvs)

#6. Rank the shuffled genes
geneRanking = GeneRanking(causalGenes)

#7. Compute p-values

#For each cancer type, get the scores of the genes after shuffling.






		
	

