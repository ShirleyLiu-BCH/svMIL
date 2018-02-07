#!/usr/bin/env python

######### Documentation #########

__author__ = "Marleen Nieboer"
__credits__ = []
__maintainer__ = "Marleen Nieboer"
__email__ = "m.m.nieboer@umcutrecht.nl"
__status__ = "Development"

### Imports ###

import numpy as np
import time

### Code ###

class HiCFeatureHandler:
	"""
		This is a docstring. It is the standard way in Python to write documentation. Docstrings and good documentation are required to make collaboration possible.
		The first line in a docstring usually contains basic information about what the class/function does.
		
		Attributes:
			attribute1 (type): In here, you describe all attributes that the class has, what their types are, and what they are/do
	"""
	
	def annotate(self, regions, hiCData, enabledFeatures = None):
		"""
			The annotate function is mandatory. This function should be called from a database handler, such as the FlatFileDb class. It should have one return value, which contains annotations.
			
			Parameters:
				regions (numpy matrix): a Numpy matrix of dtype 'object' with on the columns chr 1, s1, e1, chr2, s2, e2, and the regions on the rows.
				tadData (numpy matrix): matrix with columns chr, start, end, with each TAD on the rows. 
				enabledFeatures (list): optional. Not yet implemented. The idea is that a list can be provided that contains the names of features that are enabled in the settings. If necessary, the listed features
				can be excluded from computation to save computational time. It can be easily implemented by having an if statement checking for that in this function.
				
			Returns:
				annotations (dict): a dictionary with annotations. {'featureName' : [values]}, where the values are in the same order as the provided regions. The value must be a list to guarantee that data is
				written to the output file in the same manner, even if it has only 1 value. 
		"""
		print hiCData.shape
		exit()
		annotations = self.computeHiCFeatures(regions, hiCData)
		
		return annotations

	
	def computeHiCFeatures(self, regions, hiCData):
		
		degreeAnnotations = self.computeDegreeFeatures(regions, hiCData) #hiCData is now only the degree, but could be a combination of different data types. 
		
		annotations = dict()
		annotations['hiCDegree'] = degreeAnnotations
		
		return annotations
		
	def computeDegreeFeatures(self, regions, degreeData):
		"""
			Function to annotate the provided regions with  features related to the degree of nodes in the HiC interaction matrix. For each region, we find which interaction nodes it overlaps with.
			For each node that it overlaps with, we return the degree. The idea is that when the degree is high, there is a higher likelihood that the interaction does something important.
			
			Parameters:
				regions (numpy matrix): a Numpy matrix of dtype 'object' with on the columns chr 1, s1, e1, chr2, s2, e2, and the regions on the rows.
				hiCData (numpy matrix): matrix with columns chr, pos and degree, with the HiC interaction nodes on the rows.
				
			Returns:
				degreeAnnotations (numpy matrix): a list with the degrees of the interaction nodes that each region overlaps with. 
		
		"""
		startTime = time.time()
		#1. Make a subset of the chromosomes that we are interested in
		
		degreeAnnotations = [] #here we store all the degrees
		
		#Do the actual filtering. Make sure that all files have been pre-processed to save time here
		previousChr1 = None
		previousChr2 = None

		for lineCount in range(0, len(regions)):
			#Make sure to filter the dataset per chromosome! Good when sorted, we can keep it until we hit the next chromosome
			#The genes are not cross-chromosomal, but translocations can be, so we need to check both chromosome entries!
			
			#Obtain start and end positions and chromosome from the regions (chr 1 and 2)
			lineList = regions[lineCount,:]
			
			#Check if the previous chromosome is the same. If not, make a new subset of chromosomes.
			if "chr" + str(lineList[0]) != previousChr1 and "chr" + str(lineList[3]) != previousChr2:
				#Find the two subsets that match on both chromosomes. 
				matchingChr1Ind = degreeData[:,0] == 'chr' + lineList[0]
				matchingChr2Ind = degreeData[:,0] == 'chr' + lineList[3]
				
				#It is not even necessary to make 2 lists if both chromosomes are the same, we could use a reference without re-allocating
				chr1Subset = degreeData[np.where(matchingChr1Ind)]
				if lineList[0] == lineList[3]:
					chr2Subset = chr1Subset #This is a reference, so it does not take up extra space. 
				else:
					chr2Subset = degreeData[np.where(matchingChr2Ind)]
				
			# 	#Make sure to update the previous chromosome when it changes
			 	previousChr1 = 'chr' + str(lineList[0])
			 	previousChr2 = 'chr' + str(lineList[3])
				
				#Try to improve the speed of the code:
				#- Make a subset of the positions to search through for start and end given the first start position.
				#If the chromosome changes, we have a new subset. The positions with an end smaller than the smallest start can be ignored, and also the positions with a start larger than the largest end. These will never overlap.
				
				if lineList[0] == lineList[3]:
					#The region end must always be larger than the interaction start
					chr1Subset = chr1Subset[np.where(chr1Subset[:,1] <= int(lineList[5]))]
					#The region start must always be smaller than the interaction end
					chr1Subset = chr1Subset[np.where(chr1Subset[:,2] >= int(lineList[1]))]
				else:
					chr1Subset = chr1Subset[np.where(chr1Subset[:,1] >= int(lineList[2]))]
					chr1Subset = chr1Subset[np.where(chr1Subset[:,2] <= int(lineList[1]))]
				
			
			if np.size(chr1Subset) < 1 and np.size(chr2Subset) < 1:
				degreeAnnotations.append('NA') #otherwise we will not have one annotation per SV
				continue #no need to compute more annotations, there are no interactions on these chromosomes
			
			#Now compute how many interactions the SV overlaps with. 
			#The start should be before the end of the tad, and the end after the start of the tad. This detects 4 scenarios of overlap (currently without using the overlap parameter).
			
			#If the chromosomes are the same, the start of the TAD is in s1 for chr1, and the end is in e2 for chr2.
			if lineList[0] == lineList[3]:
				start = int(lineList[1])
				end = int(lineList[5])
			else: #otherwise, we use the positions for chromosome 1 only
				start = int(lineList[1])
				end = int(lineList[2])
			
			blocks = 4
			blockLen = int(round(chr1Subset[:,2].shape[0] / blocks))
			startOffset = 0
			endOffset = blockLen
			startOverlapChr1 = np.zeros(chr1Subset[:,2].shape, dtype="bool")
			endOverlapChr1 = np.zeros(chr1Subset[:,1].shape, dtype="bool")
			
			
			#print "SV size: ", lineList[0], lineList[1], lineList[2], lineList[3], lineList[4], lineList[5]
			
			for blockInd in range(0, blocks):
				
				if startOffset + blockLen > chr1Subset[:,2].shape[0]:
					endOffset = chr1Subset[:,2].shape[0]
				
				currentEndSubset = chr1Subset[startOffset:endOffset,2]
				
				currentStartOverlap = start < currentEndSubset
				startOverlapChr1[startOffset:endOffset] = currentStartOverlap
				
				#Repeat for the end
				currentStartSubset = chr1Subset[startOffset:endOffset,1]
				currentEndOverlap = end > currentStartSubset
				endOverlapChr1[startOffset:endOffset] = currentEndOverlap
				
				startOffset = endOffset
				endOffset += blockLen
				overlappingSvsChr1 = startOverlapChr1 * endOverlapChr1
				
			#Now find where both of these are true (multiply because both conditions need to be true)
			overlappingSvsChr1 = startOverlapChr1 * endOverlapChr1
			
			#Only re-do the overlap if chromosome 1 and 2 are different.
			if lineList[0] == lineList[3]:
				overlappingSvsChr2 = overlappingSvsChr1
			else:
				
				#Overlap chr2 as well. #If the chromosomes are the same, the start of the TAD is in s1 for chr1, and the end is in e2 for chr2.
				if lineList[0] == lineList[3]:
					start = int(lineList[1])
					end = int(lineList[5])
				else: #otherwise, we use the positions for chromosome 2 only
					start = int(lineList[4])
					end = int(lineList[5])
				
				blocks = 4
				blockLen = int(round(chr2Subset[:,2].shape[0] / blocks))
				startOffset = 0
				endOffset = blockLen
				startOverlapChr2 = np.empty(chr2Subset[:,2].shape, dtype="bool")
				endOverlapChr2 = np.empty(chr2Subset[:,1].shape, dtype="bool")
				for blockInd in range(0, blocks):
					
					if startOffset + blockLen > chr2Subset[:,2].shape[0]:
						endOffset = chr2Subset[:,2].shape[0]
					
					currentEndSubset = chr2Subset[startOffset:endOffset,2]
					
					currentStartOverlap = start < currentEndSubset
					startOverlapChr2[startOffset:endOffset] = currentStartOverlap
					
					#Repeat for the end
					currentStartSubset = chr2Subset[startOffset:endOffset,1]
					
					currentEndOverlap = end > currentStartSubset
					endOverlapChr2[startOffset:endOffset] = currentEndOverlap
					
					startOffset = endOffset
					endOffset += blockLen
				
				overlappingSvsChr2 = startOverlapChr2 * endOverlapChr2
			
			#Get the indices where both the start and end match the overlap criteria
			overlappingSvIndsChr1 = np.ravel(np.argwhere(overlappingSvsChr1 == True))
			overlappingSvIndsChr2 = np.ravel(np.argwhere(overlappingSvsChr2 == True))
			
			#For these overlapping interactions, find out what their degrees are. 
			
			degreesChr1 = list(degreeData[overlappingSvIndsChr1, 3])
			degreesChr2 = list(degreeData[overlappingSvIndsChr2, 3])
			
			allDegrees = np.array(degreesChr1 + degreesChr1)
			
			#Sort the degrees and get a top 10
			sortedDegrees = np.sort(allDegrees)
			top10Degrees = sortedDegrees[1:10]
			
			degreeAnnotations.append(top10Degrees)
		
		endTime = time.time()
		print "used ", endTime - startTime, " seconds to compute the degree annotations"
		
		return degreeAnnotations
	